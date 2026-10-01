"""Historical evidence must not become a passing simulation or lab claim."""
from copy import deepcopy
from backend.app.run_evidence import summarize_evidence


def test_legacy_missing_evidence_stays_unknown_and_record_unchanged():
    run = {'candidates': [{'compliance': {'status': 'MARGINAL'}}]}
    original = deepcopy(run)
    result = summarize_evidence(run)
    assert result['primary_nominal_pass'] is None
    assert result['agreement'] is None and result['verification'] is None
    assert not result['lab_calibrated']
    assert run == original


def test_disagreement_is_not_hidden_by_primary_nominal_pass():
    run = {'inputs': {'solver': 'reference'}, 'candidates': [{
        'compliance': {'nominal_pass': True, 'status': 'MARGINAL'},
        'circuit_crosscheck': {'compliance': {'nominal_pass': False}},
        'calibration': {'source_type': 'generated_stress_test'},
    }]}
    result = summarize_evidence(run)
    assert result['primary_nominal_pass'] is True
    assert result['agreement'] == {'both_nominal_pass': False, 'required': False}
    assert result['calibration_source'] == 'generated_stress_test'
    assert not result['lab_calibrated']


def test_circuit_only_and_fresh_samples_remain_separate_evidence():
    run = {'inputs': {'solver': 'circuit'}, 'candidates': [{
        'compliance': {'nominal_pass': True, 'status': 'MARGINAL'},
        'circuit_crosscheck': None,
        'verification': {'passed': 144, 'total': 144, 'all_checks_pass': True,
            'models_checked': ['Circuit prediction'], 'unique_scenarios': 144,
            'worst_case': {'minimum_margin_fraction': .21}},
    }]}
    result = summarize_evidence(run)
    assert result['agreement'] is None
    assert result['verification']['all_checks_pass'] is True
    assert result['verification']['models_checked'] == ['Circuit prediction']
    assert run['candidates'][0]['compliance']['status'] == 'MARGINAL'
