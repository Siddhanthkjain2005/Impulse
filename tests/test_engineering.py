"""Independent engineering checks, including adversarial false-pass regressions."""
from copy import deepcopy

import numpy as np
import pytest
from pydantic import ValidationError

from backend.app.schemas import OptimizeRequest
from backend.app.physics.waveform_metrics import analyze, crossing, waveform_from_metrics
from backend.app.physics.circuit import simulate
from backend.app.physics.compliance import check
from backend.app.optimization.networks import networks
from backend.app.optimization import engine
from backend.app.ml.registry import infer
from backend.app.ml.reference_knn import data


def test_linear_crossings_negative_polarity_and_baseline_are_nondestructive():
    # An exactly linear triangular impulse makes interpolation independently known.
    time = np.array([0, .2, .4, .6, .8, 1, 3, 5, 6, 7, 9, 11.])
    positive = np.where(time <= 1, time * 100, (11 - time) * 10)
    raw = 7 - positive
    original = raw.copy()
    result = analyze(time, raw, 'Lightning', baseline_kv=7)
    assert result['polarity'] == -1
    assert result['crest_kv'] == 100
    assert result['t30_us'] == pytest.approx(.3)
    assert result['t90_us'] == pytest.approx(.9)
    assert result['virtual_origin_us'] == pytest.approx(0)
    assert result['front_us'] == pytest.approx(1.002)
    assert result['tail_us'] == pytest.approx(6)
    np.testing.assert_array_equal(raw, original)
    assert crossing(time, positive, 50, start=5, rising=False) == 6


@pytest.mark.parametrize('impulse,front,tail', [('Lightning', 1.2, 50), ('Switching', 250, 2500)])
def test_reconstructed_waveform_metrics_and_explicit_si_conversion(impulse, front, tail):
    wave = waveform_from_metrics(front, tail, 1425, impulse)
    # A CSV represented in seconds/volts must return the same physical metrics.
    time_s = np.asarray(wave['time_us']) * 1e-6
    voltage_v = -np.asarray(wave['voltage_kv']) * 1000
    result = analyze(time_s * 1e6, voltage_v / 1000, impulse)
    assert result['front_us'] == pytest.approx(front, rel=.001)
    assert result['tail_us'] == pytest.approx(tail, rel=.001)
    assert result['crest_kv'] == pytest.approx(1425, rel=1e-12)


def test_switching_pretrigger_uses_explicit_impulse_origin():
    wave = waveform_from_metrics(250, 2500, 1000, 'Switching')
    t = np.r_[-100., -50., wave['time_us']]
    v = np.r_[0., 0., wave['voltage_kv']]
    zero = analyze(t, v, 'Switching', time_origin_us=0)
    shifted = analyze(t + 700, v, 'Switching', time_origin_us=700)
    for result in [zero, shifted]:
        assert result['front_us'] == pytest.approx(250, rel=.001)
        assert result['tail_us'] == pytest.approx(2500, rel=.001)


@pytest.mark.parametrize('bad', ['duplicate', 'reversed', 'nan', 'truncated'])
def test_waveform_refuses_invalid_samples_or_missing_limb(bad):
    wave = waveform_from_metrics(1.2, 50, 1000)
    t = np.asarray(wave['time_us']); v = np.asarray(wave['voltage_kv'])
    if bad == 'duplicate': t[5] = t[4]
    if bad == 'reversed': t = t[::-1]
    if bad == 'nan': v[10] = np.nan
    if bad == 'truncated': t, v = t[:10], v[:10]
    with pytest.raises(ValueError): analyze(t, v)


def test_numeric_compliance_boundaries_and_hardware_gate():
    pred = {'front_us': .84, 'tail_us': 60., 'crest_kv': 1030.}
    assert check('Lightning', 1000, pred)['nominal_pass']
    assert not check('Lightning', 1000, pred, hardware_ok=False)['nominal_pass']
    assert not check('Lightning', 1000, {**pred, 'tail_us': 60.00001})['nominal_pass']
    # An inside point estimate alone never establishes robustness.
    assert not check('Lightning', 1000, pred)['robust_pass']


def test_constructed_networks_have_correct_series_parallel_values_and_counts():
    items = networks(((100., 2), (200., 1)), 3)
    values = [n['equivalent_ohm'] for n in items]
    for expected in [100, 200, 300, 400, 50, 100/1.5, 100 + 100/1.5]:
        assert any(v == pytest.approx(expected) for v in values)
    for item in items:
        assert item['count_per_stage'] == sum(c['count_per_stage'] for c in item['components'])
        assert 1 <= item['count_per_stage'] <= 3
        for c in item['components']:
            assert c['count_per_stage'] <= {100: 2, 200: 1}[c['ohm']]
    one = networks(((100., 1),), 3)
    assert len(one) == 1 and one[0]['equivalent_ohm'] == 100


def test_small_positive_resistor_is_not_erased_by_search_quantization():
    # Positive resistance is valid in the typed inventory schema.
    result = networks(((.04, 1),), 1)
    assert len(result) == 1
    assert result[0]['equivalent_ohm'] == pytest.approx(.04)


@pytest.mark.parametrize('fields', [
    {'l_uh': -1}, {'efficiency': 0}, {'efficiency': 1.01}, {'load_c_pf': 0},
    {'stray_c_pf': float('inf')}, {'test_kv': float('nan')},
    {'stage_min': 10, 'stage_max': 9}, {'connection_mode': 'unverified_parallel'},
])
def test_nonphysical_or_unsupported_requests_are_rejected(fields):
    with pytest.raises(ValidationError): OptimizeRequest(**fields)


@pytest.mark.parametrize('fields,reason', [
    ({'test_kv': 3001}, 'outside'),
    ({'profile_id': 'briefing_3mv_profile'}, 'incomplete'),
    ({'profile_id': 'cpri_problem_brief_profile'}, 'stock quantities'),
    ({'stage_min': 16}, 'capacity'),
    ({'inventory_override': {'front': [], 'tail': [], 'provenance': 'test fixture'}}, 'empty'),
])
def test_hard_constraints_abort_optimization(fields, reason):
    with pytest.raises(ValueError, match=reason): engine.optimize(OptimizeRequest(**fields))


@pytest.mark.parametrize('inductance', [0, 18.5, 1000])
def test_passive_circuit_is_stable_finite_and_voltage_linear(inductance):
    args = dict(stages=9, front_r_stage=50, tail_r_stage=25, stage_c_uf=3,
                total_c_pf=1500, l_uh=inductance, efficiency=.82)
    low = simulate(charge_kv_stage=90, **args)
    high = simulate(charge_kv_stage=180, **args)
    assert all(e['real'] < 0 for e in high['diagnostics']['eigenvalues_per_second'])
    assert np.isfinite(high['waveform']['voltage_kv']).all()
    # An underdamped passive charge transfer can raise load voltage above the
    # initial generator voltage. Energy, rather than source voltage, bounds it.
    cg=3e-6/9; cl=1500e-12
    energy_bound=9*180*.82*np.sqrt(cg/cl)
    assert high['crest_kv'] <= energy_bound*(1+1e-9)
    assert high['diagnostics']['maximum_energy_ratio']<=1+1e-8
    assert high['diagnostics']['maximum_energy_increase_ratio']<1e-8
    np.testing.assert_allclose(high['waveform']['voltage_kv'],
                               np.asarray(low['waveform']['voltage_kv']) * 2, atol=1e-8)
    assert high['front_us'] == pytest.approx(low['front_us'], rel=1e-8)
    assert high['tail_us'] == pytest.approx(low['tail_us'], rel=1e-8)


def test_ml_correction_is_disabled_for_other_profiles_and_circuit_mode():
    row = data().query("Split == 'Train' and Impulse_Type == 'Lightning'").iloc[0].to_dict()
    base = [row[k] for k in ['Physics_FrontPeak_us', 'Physics_Tail_us', 'Physics_Crest_kV']]
    for profile, mode in [('cpri_problem_brief_profile', 'hybrid'), ('workbook_reference_profile', 'physics')]:
        result = infer([row], profile, mode)[0]
        assert result['ood']['trust_weight'] == 0
        np.testing.assert_array_equal(result['correction'], [0, 0, 0])
        np.testing.assert_array_equal(result['prediction'], base)
        assert result['uncertainty']['coverage_claim'] is None


def candidate_for_robustness():
    req = OptimizeRequest(monte_carlo_samples=8, uncertainty_pct=5)
    profile = engine.profile_for(req.profile_id)
    settings = {'stages': 9, 'charge_kv_stage': 1425 / (.82 * 9), 'front_r_stage': 50., 'tail_r_stage': 25.}
    phys = engine.physics(req, profile, 9, settings['charge_kv_stage'], 50, 25)
    ml = infer([engine.ml_row(req, settings, phys)], req.profile_id)[0]
    c = {'settings': settings, 'physics': phys, **ml}
    c['hybrid'] = dict(zip(['front_us', 'tail_us', 'crest_kv'], c['prediction']))
    c['calibration'] = None
    return req, profile, c


def test_latin_hypercube_robustness_is_finite_and_reproducible():
    req, profile, first = candidate_for_robustness()
    second = deepcopy(first)
    engine.robustness(req, profile, first, 'hybrid')
    engine.robustness(req, profile, second, 'hybrid')
    assert first['robustness'] == second['robustness']
    assert first['uncertainty'] == second['uncertainty']
    assert np.isfinite(first['uncertainty']['lower']).all()
    assert np.isfinite(first['uncertainty']['upper']).all()
    assert 0 <= first['robustness']['nominal_scenario_pass_pct'] <= 100


def test_robustness_includes_widened_ood_interval_for_each_scenario(monkeypatch):
    req, profile, candidate = candidate_for_robustness()
    original = infer
    def uncertain_samples(rows, profile_id, mode):
        samples = original(rows, profile_id, mode)
        for sample in samples:
            sample['prediction'] = [1.2, 50, 1425]
            sample['uncertainty'].update(lower=[.2, 1, 400], upper=[2.2, 99, 2400],
                                         halfwidth=[1, 49, 1000], coverage_claim=None)
            sample['ood']['trust_weight'] = 0
        return samples
    monkeypatch.setattr(engine, 'infer', uncertain_samples)
    engine.robustness(req, profile, candidate, 'hybrid')
    assert candidate['uncertainty']['lower'][0] <= .2
    assert candidate['uncertainty']['upper'][0] >= 2.2
    assert not candidate['compliance']['robust_pass']
    assert candidate['uncertainty']['coverage_claim'] is None
