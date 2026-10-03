"""Protect the shared model's regime separation and evidence boundaries."""
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.ml import experiment_v2 as v2, experiment_v4 as v4
from backend.app.ml.reference_knn import ROOT, OBSERVED, PHYSICS, RESIDUAL


def small_frames():
    frame = v2.read_split('Train')
    return {t: frame[frame.Impulse_Type == t].iloc[:18].reset_index(drop=True) for t in v2.TYPES}


def test_shared_inner_and_outer_folds_exclude_both_regimes():
    frames = small_frames()
    seen = set()
    for train, held in v4.paired_folds(frames, 3, 73):
        training_ids = set(pd.concat(list(train.values())).ID)
        held_ids = set(pd.concat(list(held.values())).ID)
        assert not training_ids & held_ids
        assert not seen & held_ids
        seen |= held_ids
        for inner_train, inner_held in v4.paired_folds(train, 3, 73):
            inner_fit_ids = set(pd.concat(list(inner_train.values())).ID)
            inner_test_ids = set(pd.concat(list(inner_held.values())).ID)
            assert not inner_fit_ids & inner_test_ids
            assert not inner_fit_ids & held_ids
    assert seen == set(pd.concat(list(frames.values())).ID)


def test_pooled_features_do_not_use_outcomes_ids_or_splits():
    frame = pd.concat(list(small_frames().values()), ignore_index=True)
    poisoned = frame.copy()
    poisoned[OBSERVED + RESIDUAL + PHYSICS] = -1e12
    poisoned['ID'] = -1
    poisoned['Split'] = 'Hidden Test'
    for spec in v4.spec_grid():
        for j in range(3):
            np.testing.assert_array_equal(v4.x_features(frame, j, spec), v4.x_features(poisoned, j, spec))


@pytest.mark.parametrize('pooling', ['shared', 'offset', 'partial', 'separate slopes'])
def test_relative_predictions_preserve_units_and_constant_signal(pooling):
    train = pd.concat(list(small_frames().values()), ignore_index=True)
    train[RESIDUAL] = train[PHYSICS].to_numpy() * .0125
    spec = dict(basis='minimal mechanism', degree=2, pooling=pooling, alpha=10.)
    for j in range(3):
        model = v4.fit(train, j, spec)
        query = train.copy()
        query[PHYSICS[j]] *= 2
        query[RESIDUAL + OBSERVED] = 1e9
        np.testing.assert_allclose(v4.predict(model, query, j, spec), .0125 * query[PHYSICS[j]], rtol=1e-10)
        # Predicting an extreme query must not refit either feature scaler.
        basis = model.regressor_.steps[0][1]
        before = basis.scaler_.mean_.copy()
        query['Load_C_pF'] *= 100
        v4.predict(model, query, j, spec)
        np.testing.assert_array_equal(basis.scaler_.mean_, before)


def test_v4_recorded_scores_have_no_calibration_or_final_test_leakage():
    path = ROOT / 'artifacts/experiments/v4'
    protocol = json.loads((path / 'protocol.json').read_text())
    summary = json.loads((path / 'summary.json').read_text())
    records = json.loads((path / 'oof_predictions.json').read_text())
    fit_ids = set(sum(protocol['fit_ids'].values(), []))
    excluded = set(sum(protocol['excluded_calibration_ids'].values(), []))
    assert len(records) == len({r['id'] for r in records}) == 1120
    assert {r['id'] for r in records} == fit_ids
    assert not fit_ids & excluded
    for row in records:
        assert len(row['train_ids']) == len(set(row['train_ids'])) == 896
        assert set(row['train_ids']) <= fit_ids
        assert not set(row['train_ids']) & excluded
        same_fold_held = {r['id'] for r in records if r['fold'] == row['fold']}
        assert not set(row['train_ids']) & same_fold_held
        assert np.isfinite(row['v4_prediction']).all()
    assert not any(summary[k] for k in ['hidden_test_evaluated', 'validation_evaluated', 'calibration_evaluated'])
    assert summary['active_model'] == 'residual-competition-v1'
    assert v2.sha(path / 'protocol.json') == summary['protocol_sha256']
    assert v2.sha(ROOT / 'backend/app/ml/experiment_v4.py') == protocol['runner_sha256']
    for file, digest in protocol['preserved_sha256'].items():
        assert v2.sha(ROOT / file) == digest
    baselines = []
    candidates = []
    gains = []
    for typ in v2.TYPES:
        m = summary['nested_cv'][typ]
        baselines.extend(m['metrics']['Historical V2 refit']['normalized_rmse_tolerance'])
        candidates.extend(m['metrics']['V4 pooling search']['normalized_rmse_tolerance'])
        gains.extend(m['improvement_vs_v2_pct'])
    macro = 100 * (1 - np.mean(candidates) / np.mean(baselines))
    assert summary['macro_improvement_pct'] == pytest.approx(macro)
    assert summary['promotion_eligible'] == bool(macro >= 5 and min(gains) >= -2)


def test_v4_refuses_to_retune_frozen_results(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Frozen experiment must not read new labels or train again.')
    monkeypatch.setattr(v2, 'read_split', forbidden)
    monkeypatch.setattr(v4, 'select', forbidden)
    v4.run()


def test_v4_evidence_is_available_but_cannot_be_selected_for_serving():
    client = TestClient(app)
    models = client.get('/api/models').json()
    study = models['experiment_v4']
    assert models['version'] == 'residual-competition-v1'
    assert study['candidate_count'] == 48
    assert study['selected_pooled_fold_targets'] == 0
    assert study['promotion_eligible'] is False
    assert study['macro_improvement_pct'] == 0
    assert client.get('/api/models/' + study['version'] + '/metrics').json()['protocol_sha256']
    assert client.get('/api/documents/accuracy_v4_results').status_code == 200
    assert client.get('/api/models/unknown/metrics').status_code == 404
    response = client.post('/api/optimize', json={'model_mode': study['version']})
    assert response.status_code == 422
