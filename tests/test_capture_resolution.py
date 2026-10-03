"""Synthetic capture counterexamples verify acquisition gates, not lab accuracy."""
from copy import deepcopy

import numpy as np
import pytest

from backend.app.physics.compliance import RULES, check
from backend.app.physics.waveform_metrics import analyze, waveform_from_metrics
from backend.app.trial_quality import assess_waveform


CASES = [
    ('switching_peak', 'Switching', 350., 2500.,
     np.r_[np.linspace(0., 240., 50), 250., 1000., 2000., 2500., 3000., 6000., 10000.],
     'unresolved_peak', [250., 2579.0877191966397, 975.3800964296034]),
    ('lightning_tail', 'Lightning', 1.2, 35.,
     np.r_[np.linspace(0., 5., 100), 10., 90., 150., 250.],
     'unresolved_half_value', [1.1993195233777536, 50.40246991473856, 999.9948232526388]),
    ('switching_tail', 'Switching', 250., 1800.,
     np.r_[np.linspace(0., 800., 300), 1000., 3500., 7500., 12000.],
     'unresolved_half_value', [248.8294314381271, 2132.889457394079, 999.9954510373582]),
]


@pytest.mark.parametrize('name,impulse,front,tail,times,issue,expected', CASES,
                         ids=[case[0] for case in CASES])
def test_sparse_false_pass_is_retained_but_ineligible(name, impulse, front, tail, times, issue, expected):
    dense = waveform_from_metrics(front, tail, 1000., impulse, points=100000)
    voltage = np.interp(times, dense['time_us'], dense['voltage_kv'])
    measured = analyze(times, voltage, impulse)
    original = (times.copy(), voltage.copy(), deepcopy(measured), deepcopy(RULES))
    truth = analyze(dense['time_us'], dense['voltage_kv'], impulse)
    assert not check(impulse, 1000., truth)['nominal_pass']
    assert check(impulse, 1000., measured)['nominal_pass']
    np.testing.assert_allclose([measured[k] for k in ['front_us', 'tail_us', 'crest_kv']], expected, rtol=1e-8)

    quality = assess_waveform(times, voltage, measured, impulse_type=impulse, rules=RULES)
    assert quality['status'] == 'review_required'
    assert not quality['calibration_allowed'] and not quality['evaluation_allowed']
    assert issue in {item['code'] for item in quality['issues']}
    # These examples passed the old rising-resolution and flat-crest checks.
    assert quality['metrics']['rising_intervals_30_90'] >= 4
    assert quality['metrics']['flat_crest_max_consecutive_samples'] < 3
    np.testing.assert_array_equal(times, original[0])
    np.testing.assert_array_equal(voltage, original[1])
    assert measured == original[2] and RULES == original[3]
    assert check(impulse, 1000., measured)['nominal_pass']


@pytest.mark.parametrize('impulse,front,tail', [('Lightning', 1.2, 50.), ('Switching', 250., 2500.)])
@pytest.mark.parametrize('shift,polarity,baseline', [(0., 1, 0.), (700., -1, 7.)])
def test_dense_controls_and_negative_delayed_captures_remain_usable(impulse, front, tail, shift, polarity, baseline):
    wave = waveform_from_metrics(front, tail, 1000., impulse)
    times = np.array(wave['time_us']) + shift
    voltage = baseline + polarity * np.array(wave['voltage_kv'])
    measured = analyze(times, voltage, impulse, baseline_kv=baseline, time_origin_us=shift)
    quality = assess_waveform(times, voltage, measured, impulse_type=impulse, rules=RULES)
    assert quality['calibration_allowed'] and quality['evaluation_allowed'], quality
    assert quality['metrics']['rules_id'] == RULES['id']
    assert quality['metrics']['rules_version'] == RULES['version']
    assert quality['metrics']['rules_source'] == 'supplied_rules'
    expected_limits = [.09, 2.5] if impulse == 'Lightning' else [12.5, 125.]
    np.testing.assert_allclose([quality['metrics']['maximum_peak_neighbor_span_us'],
                               quality['metrics']['maximum_half_value_bracket_span_us']], expected_limits)
    legacy = assess_waveform(times, voltage, measured)
    assert legacy['calibration_allowed'] and legacy['metrics']['impulse_type'] == impulse
    assert legacy['metrics']['rules_source'] == 'current_default'


@pytest.mark.parametrize('definition,explicit', [(None, None), ('unknown convention', None),
                                                ('virtual front/origin', 'unknown'),
                                                ('virtual front/origin', 'Switching')])
def test_unknown_or_conflicting_type_never_assumes_a_challenge_scale(definition, explicit):
    wave = waveform_from_metrics(1.2, 50., 1000.)
    measured = analyze(wave['time_us'], wave['voltage_kv'])
    measured['definition'] = definition
    quality = assess_waveform(wave['time_us'], wave['voltage_kv'], measured, impulse_type=explicit)
    assert not quality['calibration_allowed']
    assert 'missing_review_context' in {item['code'] for item in quality['issues']}


def test_explicit_context_supports_legacy_metadata_and_uses_supplied_limits():
    wave = waveform_from_metrics(1.2, 50., 1000.)
    measured = analyze(wave['time_us'], wave['voltage_kv'])
    measured.pop('definition')
    rules = deepcopy(RULES)
    rules.update(id='recorded-review-fixture', version='fixture-2')
    rules['Lightning'].update(front_min_us=1.199, front_max_us=1.201,
                              tail_min_us=49.99, tail_max_us=50.01)
    quality = assess_waveform(wave['time_us'], wave['voltage_kv'], measured,
                              impulse_type='Lightning', rules=rules)
    assert not quality['calibration_allowed']
    assert quality['metrics']['rules_id'] == 'recorded-review-fixture'
    assert quality['metrics']['rules_version'] == 'fixture-2'
    assert {'unresolved_peak', 'unresolved_half_value'} <= {item['code'] for item in quality['issues']}
    np.testing.assert_allclose([quality['metrics']['maximum_peak_neighbor_span_us'],
                               quality['metrics']['maximum_half_value_bracket_span_us']], [.00025, .0025])


@pytest.mark.parametrize('broken', [{}, None, {'front_min_us': 1.2, 'front_max_us': 1.2},
                                   {'tail_min_us': float('nan'), 'tail_max_us': 60.}])
def test_invalid_explicit_rules_block_resolution_review(broken):
    wave = waveform_from_metrics(1.2, 50., 1000.)
    measured = analyze(wave['time_us'], wave['voltage_kv'])
    rules = deepcopy(RULES)
    if broken is None:
        rules.pop('version')
    elif broken:
        rules['Lightning'].update(broken)
    else:
        rules = broken
    quality = assess_waveform(wave['time_us'], wave['voltage_kv'], measured,
                              impulse_type='Lightning', rules=rules)
    assert not quality['evaluation_allowed']
    assert 'missing_review_context' in {item['code'] for item in quality['issues']}
