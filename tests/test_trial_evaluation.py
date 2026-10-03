"""Laboratory-review controls use isolated synthetic fixtures, not lab evidence."""
import os
import tempfile
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

os.environ.setdefault('IMPULSETWIN_DB', str(Path(tempfile.mkdtemp(prefix='impulsetwin-evaluation-tests-')) / 'audit.sqlite3'))
from backend.app import main, storage
from backend.app.physics.waveform_metrics import waveform_from_metrics


@pytest.fixture
def review_store(tmp_path, monkeypatch):
    import json
    engine = create_engine('sqlite:///' + str(tmp_path / 'audit.sqlite3'), connect_args={'check_same_thread': False})
    storage.metadata.create_all(engine)
    monkeypatch.setattr(storage, 'engine', engine)
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    template = json.loads((Path(__file__).resolve().parents[1] / 'data/demo/lightning_reference_run.json').read_text())
    yield TestClient(main.app), template
    engine.dispose()


def setup(template, identifier='review-setup', impulse='Lightning', calibration=None):
    run = deepcopy(template); run['inputs']['impulse_type'] = impulse
    timing = [1.2, 50] if impulse == 'Lightning' else [250, 2500]
    c = run['candidates'][0]; c['hybrid'] = dict(zip(['front_us', 'tail_us', 'crest_kv'], timing + [1002]))
    c['physics'].update(dict(zip(['front_us', 'tail_us', 'crest_kv'], timing + [1004])))
    c['calibration'] = calibration
    if calibration:
        c['hybrid'] = {k: v + calibration['bias'][i] for i, (k, v) in enumerate(c['hybrid'].items())}
    c['prediction'] = list(c['hybrid'].values())
    return storage.put('run', identifier, run)


def capture(client, run, crest, source='measured_lab', prefix=''):
    timing = [1.2, 50] if run['inputs']['impulse_type'] == 'Lightning' else [250, 2500]
    wave = waveform_from_metrics(*timing, crest, run['inputs']['impulse_type'])
    text = prefix + 'time_us,voltage_kv\n' + '\n'.join(f'{t:.15g},{v:.15g}' for t, v in zip(wave['time_us'], wave['voltage_kv']))
    r = client.post('/api/trials/upload', data={'run_id': run['id'], 'source_type': source}, files={'file': ('isolated-fixture.csv', text, 'text/csv')})
    assert r.status_code == 200, r.text
    return r.json()


def score(client, trials):
    return client.post('/api/evaluations', json={'trial_ids': [t['id'] for t in trials]})


def test_laboratory_readiness_excludes_demo_duplicates_and_calibration_sources(review_store):
    client,template=review_store; run=setup(template)
    measured=capture(client,run,1000)
    capture(client,run,1000,prefix='# Duplicate with changed bytes\n')
    demo=capture(client,run,1002,source='generated_stress_test')
    assert client.post(f"/api/trials/{measured['id']}/calibrate").status_code==200
    result=client.get('/api/laboratory-evidence').json()
    assert result['measured_captures']==2 and result['excluded_captures']==2
    assert result['eligible_for_independent_evaluation']==0
    assert result['by_source']['generated_demo']==1
    assert not next(r for r in result['captures'] if r['source_id']==demo['id'])['eligible_for_external_accuracy']


def test_highest_evidence_requires_matching_intact_evaluation(review_store):
    client,template=review_store; run=setup(template)
    trials=[capture(client,run,v) for v in (999,1000,1001)]
    review=score(client,trials); assert review.status_code==200,review.text
    judge=client.get(f"/api/runs/{run['id']}/judge").json()
    assert judge['candidates'][0]['evidence']['level']==5
    assert judge['candidates'][1]['evidence']['level']<5
    (main.ROOT/trials[0]['raw_path']).write_text('changed capture')
    assert client.post(f"/api/trials/{trials[0]['id']}/calibrate").status_code==422
    refreshed=client.get(f"/api/runs/{run['id']}/judge").json()
    assert refreshed['candidates'][0]['evidence']['level']<5


@pytest.mark.parametrize('tag,expected',[('generated_demo','generated_demo'),('synthetic_benchmark','synthetic_benchmark')])
def test_embedded_nonlaboratory_provenance_cannot_be_upgraded(review_store,tag,expected):
    client,template=review_store;run=setup(template)
    trial=capture(client,run,1000,prefix=f'# source_type={tag}\n')
    assert trial['evidence']['source_type']==expected
    assert trial['evidence']['measurement_instrument'] is None
    assert not trial['evidence']['eligible_for_external_accuracy']


def test_saved_predictions_score_new_shots_without_refit_or_changed_records(review_store):
    client, template = review_store; run = setup(template)
    trials = [capture(client, run, crest) for crest in [999, 1000, 1001]]
    response = score(client, trials); assert response.status_code == 200, response.text
    review = response.json(); metrics = review['groups'][0]['metrics']
    assert review['trial_count'] == 3 and review['models_refit'] is False
    assert review['production_model_changed'] is False
    assert metrics['physics']['rmse'][2] == pytest.approx(np.sqrt(50 / 3))
    assert metrics['recorded_prediction']['rmse'][2] == pytest.approx(np.sqrt(14 / 3))
    assert metrics['recorded_prediction']['rmse_reduction_vs_physics_pct'][2] == pytest.approx(100 * (1 - np.sqrt(14 / 50)))
    assert storage.get(run['id'], 'run') == run
    assert storage.list_records('calibration') == []
    assert client.get('/api/evaluations').json()[0]['id'] == review['id']
    assert client.get(f"/api/evaluations/{review['id']}/json").json() == review


@pytest.mark.parametrize('problem', ['synthetic', 'duplicate_id', 'same_waveform', 'changed_raw', 'capture_quality'])
def test_invalid_or_reused_evidence_cannot_create_accuracy_record(review_store, problem):
    client, template = review_store; run = setup(template)
    trials = [capture(client, run, crest) for crest in [999, 1000, 1001]]
    if problem == 'synthetic':
        trials[2] = capture(client, run, 1003, source='generated_stress_test')
    elif problem == 'duplicate_id':
        trials[2] = trials[0]
    elif problem == 'same_waveform':
        trials[2] = capture(client, run, 999, prefix='# Same capture, different CSV bytes\n')
        assert trials[2]['raw_sha256'] != trials[0]['raw_sha256']
    elif problem == 'changed_raw':
        (main.ROOT / trials[0]['raw_path']).write_text('changed capture')
    else:
        bad = deepcopy(trials[0]); ix = np.linspace(0, len(bad['waveform']['time_us']) - 1, 11, dtype=int)
        bad['waveform'] = {k: [bad['waveform'][k][i] for i in ix] for k in ['time_us', 'voltage_kv']}
        trials[0] = storage.put('trial', 'legacy-sparse', bad)
    response = score(client, trials)
    assert response.status_code == 422, response.text
    assert storage.list_records('evaluation') == []


def test_every_calibration_ancestor_is_excluded_from_scoring(review_store):
    client, template = review_store; run = setup(template)
    first = capture(client, run, 1000)
    cal1 = client.post(f"/api/trials/{first['id']}/calibrate").json()
    second_run = setup(template, 'second-setup', calibration=cal1)
    second = capture(client, second_run, 1001)
    cal2 = client.post(f"/api/trials/{second['id']}/calibrate").json()
    third_run = setup(template, 'third-setup', calibration=cal2)
    fresh = [capture(client, third_run, v) for v in [999, 1003, 1004]]
    response = score(client, [first, *fresh[:2]])
    assert response.status_code == 422 and 'contributed to calibration' in response.text
    assert not storage.list_records('evaluation')
    response = score(client, fresh); assert response.status_code == 200, response.text
    assert response.json()['trial_predictions'][0]['calibration_ancestry_ids'] == [cal2['id'], cal1['id']]
    assert response.json()['groups'][0]['metrics']['original_model'] != response.json()['groups'][0]['metrics']['recorded_prediction']


def test_missing_calibration_ancestry_blocks_score(review_store):
    client, template = review_store
    run = setup(template, calibration={'id': 'missing-calibration', 'bias': [0, 0, 1], 'source_type': 'measured_lab'})
    trials = [capture(client, run, crest) for crest in [999, 1000, 1001]]
    response = score(client, trials)
    assert response.status_code == 422 and 'Missing calibration' in response.text


def test_impulse_regimes_and_model_versions_are_scored_separately(review_store):
    client, template = review_store; li = setup(template)
    si = setup(template, 'switching-setup', impulse='Switching')
    changed = deepcopy(template); changed['model_version'] = 'another-frozen-version'
    other = setup(changed, 'other-version')
    trials = [capture(client, li, 999), capture(client, si, 1000), capture(client, other, 1001)]
    response = score(client, trials); assert response.status_code == 200, response.text
    groups = response.json()['groups']; assert len(groups) == 3
    assert all(g['sample_count'] == 1 and g['units'] == ['µs', 'µs', 'kV'] for g in groups)
    assert {g['context']['impulse_type'] for g in groups} == {'Lightning', 'Switching'}


def test_too_few_captures_cannot_create_review(review_store):
    client, template = review_store; run = setup(template)
    assert score(client, [capture(client, run, v) for v in [999, 1000]]).status_code == 422


def test_prediction_recorded_after_capture_is_rejected(review_store, monkeypatch):
    client, template = review_store; run = setup(template)
    trials = [capture(client, run, v) for v in [999, 1000, 1001]]
    original_get = storage.get
    def future_record(identifier, kind):
        record = original_get(identifier, kind)
        if kind == 'run':record['created_at'] = '2099-01-01T00:00:00+00:00'
        return record
    monkeypatch.setattr(storage, 'get', future_record)
    response = score(client, trials)
    assert response.status_code == 422 and 'saved before' in response.text


def test_zero_physics_error_has_no_infinite_percentage_improvement(review_store):
    client, template = review_store; trials = []
    for i, crest in enumerate([999, 1000, 1001]):
        changed = deepcopy(template); changed['candidates'][0]['physics']['crest_kv'] = crest
        run = setup(changed, f'zero-baseline-{i}')
        # Set the predeclared fixture physics prediction to this known crest.
        run['candidates'][0]['physics']['crest_kv'] = crest
        run = storage.put('run', f'zero-physics-{i}', run)
        trials.append(capture(client, run, crest))
    response = score(client, trials); assert response.status_code == 200, response.text
    metrics = response.json()['groups'][0]['metrics']
    assert metrics['physics']['rmse'][2] == 0
    assert metrics['recorded_prediction']['rmse_reduction_vs_physics_pct'][2] is None


@pytest.mark.parametrize('impulse', ['Lightning', 'Switching'])
def test_mixed_outcomes_report_false_passes_denominators_and_worst_shot(review_store, impulse):
    client, template = review_store
    template['inputs']['test_kv'] = 1000
    trials = []
    for i, (observed, predicted) in enumerate([(1000, 1000), (1100, 1000), (1001, 1100), (1101, 1100)]):
        run = setup(template, f'decision-{impulse}-{i}', impulse=impulse)
        c = run['candidates'][0]; c['hybrid']['crest_kv'] = predicted
        c['prediction'] = list(c['hybrid'].values())
        values = np.array(c['prediction'])
        c['uncertainty'] = {'lower': (values * .999).tolist(), 'upper': (values * 1.001).tolist(),
                            'coverage_claim': None, 'method': 'Isolated fixture envelope'}
        run = storage.put('run', f'predicted-{impulse}-{i}', run)
        trials.append(capture(client, run, observed))
    response = score(client, trials); assert response.status_code == 200, response.text
    review = response.json(); group = review['groups'][0]
    decisions = group['decisions']['models']['recorded_prediction']
    assert [decisions[k] for k in ['true_pass', 'false_pass', 'false_fail', 'true_fail']] == [1, 1, 1, 1]
    assert decisions['both_measured_outcomes_present'] is True
    assert decisions['correct_decisions'] == {'numerator': 2, 'denominator': 4, 'pct': 50.}
    assert decisions['false_pass_among_measured_failures'] == {'numerator': 1, 'denominator': 2, 'pct': 50.}
    assert decisions['false_fail_among_measured_passes'] == {'numerator': 1, 'denominator': 2, 'pct': 50.}
    assert decisions['false_pass_trial_ids'] == [trials[1]['id']]
    assert decisions['false_fail_trial_ids'] == [trials[2]['id']]
    envelope = group['decisions']['saved_envelope']
    assert envelope['state_counts'] == dict(contained=2, overlaps=0, outside=2, unavailable=0)
    assert envelope['measured_fail_among_contained_envelopes']['pct'] == 50
    worst = group['metrics']['recorded_prediction']['worst_case']
    assert worst['trial_id'] == trials[1]['id'] and worst['metric'] == 'crest_kv'
    assert worst['absolute_error'] == pytest.approx(100)
    assert worst['normalized_error_tolerance'] == pytest.approx(100 / 30)
    assert review['trial_predictions'][0]['ml_support'] == 'in_distribution'
    assert all(r['challenge_limits']['normalization_halfwidth'][2] == 30 for r in review['trial_predictions'])
    assert not storage.list_records('calibration')


def test_all_pass_sample_does_not_claim_zero_false_pass_risk(review_store):
    client, template = review_store; template['inputs']['test_kv'] = 1000
    run = setup(template)
    trials = [capture(client, run, crest) for crest in [999, 1000, 1001]]
    response = score(client, trials); assert response.status_code == 200, response.text
    d = response.json()['groups'][0]['decisions']['models']['recorded_prediction']
    assert d['correct_decisions']['pct'] == 100
    assert d['both_measured_outcomes_present'] is False
    assert d['false_pass_among_measured_failures'] == {'numerator': 0, 'denominator': 0, 'pct': None}


def test_rules_with_same_version_but_changed_bounds_form_separate_groups(review_store):
    client, template = review_store; template['inputs']['test_kv'] = 1000
    trials = [capture(client, setup(template, 'default-rules'), 1000)]
    changed = deepcopy(template)
    changed['rules']['crest_tolerance_fraction'] = .001
    for i, crest in enumerate([1003, 1004]):
        trials.append(capture(client, setup(changed, f'narrow-rules-{i}'), crest))
    response = score(client, trials); assert response.status_code == 200, response.text
    result = response.json(); groups = result['groups']
    assert len(groups) == 2 and {g['sample_count'] for g in groups} == {1, 2}
    assert len({g['context']['rules_sha256'] for g in groups}) == 2
    assert len({g['context']['rules_version'] for g in groups}) == 1
    narrowed = [r for r in result['trial_predictions'] if r['trial_id'] != trials[0]['id']]
    assert all(not r['measured_decision']['nominal_pass'] for r in narrowed)
    assert all(r['challenge_limits']['normalization_halfwidth'][2] == pytest.approx(1) for r in narrowed)


@pytest.mark.parametrize('problem', ['absent', 'invalid'])
def test_missing_or_invalid_saved_rules_block_evaluation(review_store, problem, monkeypatch):
    client, template = review_store; run = setup(template)
    trials = [capture(client, run, crest) for crest in [999, 1000, 1001]]
    if problem == 'absent':
        run.pop('rules')
    else:
        run['rules']['crest_tolerance_fraction'] = -1
    original_get = storage.get
    def broken_record(identifier, kind):
        return deepcopy(run) if kind == 'run' and identifier == run['id'] else original_get(identifier, kind)
    monkeypatch.setattr(storage, 'get', broken_record)
    response = score(client, trials)
    assert response.status_code == 422, response.text
    assert not storage.list_records('evaluation')


@pytest.mark.parametrize('impulse,front,tail,times', [
    ('Switching', 350., 2500., np.r_[np.linspace(0., 240., 50), 250., 1000., 2000., 2500., 3000., 6000., 10000.]),
    ('Lightning', 1.2, 35., np.r_[np.linspace(0., 5., 100), 10., 90., 150., 250.]),
    ('Switching', 250., 1800., np.r_[np.linspace(0., 800., 300), 1000., 3500., 7500., 12000.]),
])
def test_sparse_nominal_pass_is_provisional_and_cannot_calibrate_or_score(review_store, impulse, front, tail, times):
    client, template = review_store; template['inputs']['test_kv'] = 1000
    run = setup(template, impulse=impulse)
    dense = waveform_from_metrics(front, tail, 1000, impulse, points=100000)
    voltage = np.interp(times, dense['time_us'], dense['voltage_kv'])
    content = 'time_us,voltage_kv\n' + '\n'.join(f'{t},{v}' for t, v in zip(times, voltage))
    response = client.post('/api/trials/upload', data={'run_id': run['id'], 'source_type': 'measured_lab'},
                           files={'file': ('isolated-sparse-fixture.csv', content, 'text/csv')})
    assert response.status_code == 200, response.text
    trial = response.json()
    assert trial['compliance']['nominal_pass'] is True
    assert trial['compliance']['status'] == 'REVIEW REQUIRED'
    assert trial['compliance']['provisional'] is True
    assert trial['compliance']['measurement_evidence_eligible'] is False
    assert (main.ROOT / trial['raw_path']).read_bytes() == content.encode()
    # Older stored eligibility cannot bypass today's resolution checks.
    legacy = deepcopy(trial); legacy['quality'] = {'calibration_allowed': True}
    legacy = storage.put('trial', 'legacy-unresolved', legacy)
    assert client.post('/api/trials/legacy-unresolved/calibrate').status_code == 422
    trials = [legacy, capture(client, run, 1001), capture(client, run, 1002)]
    response = score(client, trials)
    assert response.status_code == 422 and 'capture review' in response.text.lower()
    assert storage.get(run['id'], 'run') == run
    assert not storage.list_records('calibration') and not storage.list_records('evaluation')


def test_capture_review_uses_saved_timing_rules_in_upload_and_recheck(review_store):
    client, template = review_store
    template['rules']['Lightning'].update(front_min_us=1.199, front_max_us=1.201)
    run = setup(template)
    trial = capture(client, run, 1000)
    assert trial['quality']['metrics']['maximum_peak_neighbor_span_us'] == pytest.approx(.00025)
    assert trial['quality']['metrics']['rules_source'] == 'supplied_rules'
    assert trial['quality']['evaluation_allowed'] is False
    assert client.post(f"/api/trials/{trial['id']}/calibrate").status_code == 422
