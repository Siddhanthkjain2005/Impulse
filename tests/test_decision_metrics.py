"""Decision thresholds, missing denominators and interval/nominal separation."""
from copy import deepcopy

import pytest

from backend.app.decision_metrics import captured_limits, nominal_decision, saved_envelope_decision, confusion
from backend.app.physics.compliance import RULES


def limits():
    return captured_limits({'rules': deepcopy(RULES), 'inputs': {'impulse_type': 'Lightning', 'test_kv': 1000.}})


def test_nominal_boundaries_and_rule_snapshot_are_preserved():
    selected = limits()
    assert nominal_decision([.84, 40, 970], selected)['nominal_pass']
    assert nominal_decision([1.56, 60, 1030], selected)['nominal_pass']
    outside = nominal_decision([1.560001, 50, 1000], selected)
    assert outside['nominal_pass'] is False and outside['minimum_limit_margin'] < 0
    selected['snapshot']['Lightning']['front_max_us'] = 999
    assert RULES['Lightning']['front_max_us'] == 1.56


def test_no_predicted_passes_has_no_measured_fail_rate_among_predicted_passes():
    d = confusion([True, False], [False, False])
    assert d['false_fail'] == 1 and d['true_fail'] == 1
    assert d['measured_fail_among_predicted_passes']['pct'] is None
    assert d['false_pass_among_measured_failures']['pct'] == 0


@pytest.mark.parametrize('envelope,state', [
    ({'lower': [1, 45, 990], 'upper': [1.4, 55, 1010]}, 'contained'),
    ({'lower': [.7, 45, 990], 'upper': [1.4, 55, 1010]}, 'overlaps'),
    ({'lower': [1.6, 45, 990], 'upper': [1.8, 55, 1010]}, 'outside'),
    ({'lower': [1.4, 45, 990], 'upper': [1, 55, 1010]}, 'unavailable'),
    ({'lower': [1, 45], 'upper': [1.4, 55]}, 'unavailable'),
])
def test_saved_interval_geometry_does_not_invent_coverage(envelope, state):
    center = [1.7, 50, 1000] if state == 'outside' else [1.2, 50, 1000]
    result = saved_envelope_decision(envelope, center, limits())
    assert result['state'] == state
    assert result.get('recorded_coverage_claim') is None


def test_inconsistent_saved_interval_is_unavailable_instead_of_robust_pass():
    result = saved_envelope_decision({'lower': [1, 45, 990], 'upper': [1.4, 55, 1010]}, [2, 50, 1000], limits())
    assert result['state'] == 'unavailable'
