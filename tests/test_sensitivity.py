"""Raw RLC exploration must not become a recommendation or fitted accuracy claim."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

os.environ.setdefault('IMPULSETWIN_DB', str(Path(tempfile.mkdtemp(prefix='impulsetwin-sensitivity-tests-')) / 'audit.sqlite3'))
from backend.app import main, storage
from backend.app.optimization import engine as optimization
from backend.app.schemas import SensitivityRequest
from backend.app.sensitivity import compare_sensitivity
from backend.app.physics.waveform_metrics import analyze


@pytest.fixture
def run():
    return json.loads((Path(__file__).resolve().parents[1] / 'data/demo/lightning_model_agreement_run.json').read_text())


def test_zero_change_reproduces_both_raw_models_without_mutating_or_using_ml(run, monkeypatch):
    monkeypatch.setattr(optimization, 'infer', lambda *args, **kwargs: pytest.fail('Sensitivity must never apply residual inference'))
    original = deepcopy(run); c = run['candidates'][0]
    result = compare_sensitivity(run, c['id'], SensitivityRequest(change_pct=0))
    assert run == original and result['saved_recommendation_changed'] is False
    assert result['optimizer_ranking_changed'] is False and result['saved_correction_applied'] is False
    assert result['saved_uncertainty_status'] == 'MARGINAL'
    for model in result['models']:
        assert model['available'] and model['baseline'] == model['variant']
        assert all(change['delta_pct'] == 0 for change in model['changes'])
        recorded = c['physics'] if model['id'] == 'reference' else c['circuit_crosscheck']
        for key in ['front_us', 'tail_us', 'crest_kv']:
            assert model['baseline']['metrics'][key] == pytest.approx(recorded[key], rel=1e-10)


@pytest.mark.parametrize('parameter', ['front_r_stage', 'tail_r_stage', 'load_c_pf', 'divider_c_pf', 'stray_c_pf', 'l_uh'])
def test_only_one_requested_value_changes_and_supply_is_held_fixed(run, parameter):
    result = compare_sensitivity(run, run['candidates'][0]['id'], SensitivityRequest(parameter=parameter, change_pct=10))
    differences = [(location, key) for location in ['inputs', 'settings']
                   for key, value in result[f'baseline_{location}'].items()
                   if result[f'variant_{location}'][key] != value]
    assert differences == [(result['parameter']['location'], parameter)]
    assert result['variant_settings']['stages'] == result['baseline_settings']['stages']
    assert result['variant_settings']['charge_kv_stage'] == result['baseline_settings']['charge_kv_stage']
    assert result['resistor_plan_requires_new_search'] == (parameter in ['front_r_stage', 'tail_r_stage'])
    # The workbook holds crest independent of RLC, while the circuit can change
    # transfer. We expose that limitation rather than inventing one shared law.
    reference, circuit = result['models']
    assert reference['baseline']['metrics']['crest_kv'] == reference['variant']['metrics']['crest_kv']
    assert circuit['available']
    if parameter in ['front_r_stage', 'tail_r_stage', 'load_c_pf']:
        assert not math.isclose(circuit['baseline']['metrics']['crest_kv'], circuit['variant']['metrics']['crest_kv'], rel_tol=1e-6)


def test_rc_front_scaling_and_tail_resistance_scaling_preserve_unaffected_reference_metrics(run):
    run['inputs']['l_uh'] = 0
    front = compare_sensitivity(run, run['candidates'][0]['id'], SensitivityRequest(parameter='front_r_stage', change_pct=20))['models'][0]
    assert front['variant']['metrics']['front_us'] == pytest.approx(front['baseline']['metrics']['front_us'] * 1.2)
    assert front['variant']['metrics']['tail_us'] == front['baseline']['metrics']['tail_us']
    tail = compare_sensitivity(run, run['candidates'][0]['id'], SensitivityRequest(parameter='tail_r_stage', change_pct=-20))['models'][0]
    assert tail['variant']['metrics']['tail_us'] == pytest.approx(tail['baseline']['metrics']['tail_us'] * .8)
    assert tail['variant']['metrics']['front_us'] == tail['baseline']['metrics']['front_us']


def test_zero_inductance_and_calibration_do_not_create_synthetic_gain_claims(run):
    run['inputs']['l_uh'] = 0
    c = run['candidates'][0]; c['calibration'] = {'bias': [10, 200, 300], 'source_type': 'measured_lab'}
    result = compare_sensitivity(run, c['id'], SensitivityRequest(parameter='l_uh', change_pct=30))
    assert not result['parameter']['value_changed'] and result['parameter']['variant_value'] == 0
    assert result['source_type'] == 'generated_stress_test' and result['saved_correction_applied'] is False
    assert all(m['baseline'] == m['variant'] for m in result['models'])


def test_unrepresentable_reference_curve_retains_numeric_metrics(run):
    run['candidates'][0]['settings']['front_r_stage'] = 1e7
    result = compare_sensitivity(run, run['candidates'][0]['id'], SensitivityRequest(change_pct=0))
    reference = result['models'][0]
    assert reference['available'] and reference['baseline']['waveform'] is None
    assert reference['baseline']['plot_error'] and reference['baseline']['metrics']['front_us'] > 0
    assert reference['baseline']['waveform_limits']['nominal_pass'] is False


def test_switching_curve_front_metric_is_time_to_peak_from_zero_onset():
    root = Path(__file__).resolve().parents[1]
    switching = json.loads((root / 'data/demo/switching_constructible_ood_run.json').read_text())
    result = compare_sensitivity(switching, switching['candidates'][0]['id'], SensitivityRequest(parameter='load_c_pf', change_pct=10))
    for model in result['models']:
        assert model['available']
        for mode in ['baseline', 'variant']:
            waveform = model[mode]['waveform']
            extracted = analyze(waveform['time_us'], waveform['voltage_kv'], 'Switching')
            assert extracted['front_us'] == pytest.approx(model[mode]['metrics']['front_us'], rel=1e-9)


def test_api_audit_is_immutable_and_rejects_invalid_inputs(run, tmp_path, monkeypatch):
    engine = create_engine('sqlite:///' + str(tmp_path / 'audit.sqlite3'), connect_args={'check_same_thread': False})
    storage.metadata.create_all(engine); monkeypatch.setattr(storage, 'engine', engine)
    run = storage.put('run', 'sensitivity-baseline', run); c = run['candidates'][0]
    client = TestClient(main.app); path = f"/api/runs/{run['id']}/candidates/{c['id']}/sensitivity"
    response = client.post(path, json={'parameter': 'load_c_pf', 'change_pct': 10})
    assert response.status_code == 200, response.text
    result = response.json()
    assert client.get(f"/api/sensitivity/{result['id']}/json").json() == result
    assert storage.get(run['id'], 'run') == run
    for body in [{'parameter': 'stages'}, {'change_pct': 31}, {'change_pct': -31}, {'change_pct': 'nan'}, {'change_pct': 10, 'hidden_setting': 9}]:
        assert client.post(path, json=body).status_code == 422
    assert client.post(f"/api/runs/{run['id']}/candidates/wrong/sensitivity", json={}).status_code == 422
    assert client.post('/api/runs/missing/candidates/wrong/sensitivity', json={}).status_code == 404
    edge_run = deepcopy(run); edge_run['inputs']['load_c_pf'] = 99000
    edge_run = storage.put('run', 'input-boundary', edge_run)
    response = client.post(f"/api/runs/{edge_run['id']}/candidates/{c['id']}/sensitivity", json={'change_pct': 10})
    assert response.status_code == 422 and 'load_c_pf' in response.text
    engine.dispose()
