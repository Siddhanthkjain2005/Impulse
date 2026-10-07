import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backend.app.ml import experiment_v7 as v7


def frame(n=30, first_id=1):
    rng = np.random.default_rng(17)
    total = rng.uniform(200, 1000, n)
    inductance = rng.uniform(15, 120, n)
    crest = rng.uniform(300, 1200, n)
    residual = crest * (.006 - total * inductance * 1e-7)
    return pd.DataFrame({'ID': np.arange(first_id, first_id + n), 'Load_C_pF': total,
                         'Divider_C_pF': np.zeros(n), 'Stray_C_pF': np.zeros(n),
                         'L_uH': inductance, 'Physics_Crest_kV': crest,
                         'Residual_Crest': residual, 'Observed_Crest_kV': crest + residual,
                         'Test_kV': crest})


@pytest.mark.parametrize('spec', v7.grid())
def test_query_outcomes_are_never_features(spec):
    train, held = frame(), frame(8, 100)
    model = v7.CrestRegressor(spec).fit(train)
    expected = model.predict(held)
    blinded = held.drop(columns=['Observed_Crest_kV', 'Residual_Crest'])
    np.testing.assert_array_equal(expected, model.predict(blinded))
    assert np.isfinite(expected).all()
    assert set(model.fit_ids).isdisjoint(held.ID)


def test_inner_selection_excludes_all_held_ids(monkeypatch):
    train, other = frame(18), frame(18, 100)
    fits = []

    def baselines(fit, other_fit, held, historical):
        assert set(fit.ID).isdisjoint(held.ID)
        assert len(fit) == len(other_fit) == 12
        fits.append((set(fit.ID), set(held.ID)))
        return {name: np.zeros(len(held)) for name in v7.NAMES[1:3]}

    class SpyRegressor:
        def __init__(self, spec): pass
        def fit(self, fit):
            self.ids = set(fit.ID)
            return self
        def predict(self, held):
            assert self.ids.isdisjoint(held.ID)
            fits.append((self.ids, set(held.ID)))
            return np.zeros(len(held))

    monkeypatch.setattr(v7, 'baseline_predictions', baselines)
    monkeypatch.setattr(v7, 'CrestRegressor', SpyRegressor)
    monkeypatch.setattr(v7, 'grid', lambda: [{'name': 'spy'}])
    selection, log = v7.select(train, other, {}, 131)
    assert len(fits) == 6
    assert set.union(*(held for _, held in fits)) == set(train.ID)
    assert selection == {'name': 'Inner-selected baseline', 'baseline': v7.NAMES[1]}
    assert not log['numerical_failures']


def test_baseline_reference_receives_only_the_given_two_fit_frames(monkeypatch):
    train, other, held = frame(5), frame(5, 100), frame(3, 200)
    captured = []

    class SpyReference:
        def __init__(self, fit):
            captured.extend(fit.ID.tolist())
        def predict(self, query):
            assert set(captured).isdisjoint(query.ID)
            return np.zeros((len(query), 3))

    monkeypatch.setattr(v7, 'WorkbookKNN', SpyReference)
    monkeypatch.setattr(v7.v2, 'fit_spec', lambda *args: None)
    monkeypatch.setattr(v7.v2, 'predict_spec', lambda model, query, *args: np.zeros(len(query)))
    v7.baseline_predictions(train, other, held, {})
    assert set(captured) == set(train.ID) | set(other.ID)


def test_minimax_failure_and_false_success_cannot_be_used(monkeypatch):
    model = v7.CrestRegressor(dict(name='Regularized minimax envelope', basis='full', penalty=.001))
    monkeypatch.setattr(v7, 'linprog', lambda *args, **kwargs: SimpleNamespace(
        success=False, x=None, message='test unresolved'))
    with pytest.raises(v7.SolverFailure, match='unresolved'):
        model._fit_envelope(np.ones((3, 1)), np.ones(3))
    monkeypatch.setattr(v7, 'linprog', lambda *args, **kwargs: SimpleNamespace(
        success=True, x=np.zeros(4), message='false success'))
    with pytest.raises(v7.SolverFailure, match='constraint violation'):
        model._fit_envelope(np.ones((3, 1)), np.ones(3))
    monkeypatch.setattr(v7, 'linprog', lambda *args, **kwargs: SimpleNamespace(
        success=True, x=np.full(4, np.nan), message='nonfinite'))
    with pytest.raises(v7.SolverFailure, match='unresolved'):
        model._fit_envelope(np.ones((3, 1)), np.ones(3))


def test_outer_numerical_failure_is_logged_before_baseline_fallback(monkeypatch):
    class FailedRegressor:
        def __init__(self, spec): pass
        def fit(self, fit): raise v7.SolverFailure('injected solver failure')

    monkeypatch.setattr(v7, 'CrestRegressor', FailedRegressor)
    train, held, failures = frame(), frame(5, 100), []
    expected = np.arange(len(held), dtype=float)
    prediction = v7.chosen_prediction(train, held, {'name': 'candidate', 'baseline': v7.NAMES[1]},
                                      {v7.NAMES[1]: expected}, failures, 'outer test')
    np.testing.assert_array_equal(prediction, expected)
    assert failures[0]['error'] == 'injected solver failure'
    assert failures[0]['stage'] == 'outer test'
    assert set(failures[0]['fit_ids']).isdisjoint(failures[0]['held_ids'])


def test_inner_numerical_failure_disqualifies_the_candidate(monkeypatch):
    class FailedRegressor:
        def __init__(self, spec): pass
        def fit(self, fit): raise v7.SolverFailure('injected unresolved LP')

    monkeypatch.setattr(v7, 'CrestRegressor', FailedRegressor)
    monkeypatch.setattr(v7, 'grid', lambda: [{'name': 'test envelope'}])
    monkeypatch.setattr(v7, 'baseline_predictions', lambda train, other, held, historical:
                        {name: np.zeros(len(held)) for name in v7.NAMES[1:3]})
    choice, log = v7.select(frame(18), frame(18, 100), {}, 4)
    assert choice['name'] == 'Inner-selected baseline'
    assert log['leaderboard'][0]['inner_mse_kv2'] is None
    assert log['leaderboard'][0]['numerical_failure']
    assert len(log['numerical_failures']) == 1


def test_unexpected_implementation_errors_are_not_hidden_as_solver_fallback(monkeypatch):
    class BrokenRegressor:
        def __init__(self, spec): pass
        def fit(self, fit): raise ValueError('programming or input error')

    monkeypatch.setattr(v7, 'CrestRegressor', BrokenRegressor)
    with pytest.raises(ValueError, match='programming or input error'):
        v7.safe_prediction({}, frame(), frame(5, 100), [], 'test')


def test_fixed_gate_needs_every_seed_and_ten_fold_wins():
    rows = [dict(improvement_vs_v2_pct=2., improvement_vs_knn_pct=5.) for _ in v7.SEEDS]
    assert v7.promotion_gate(rows, 10)
    assert not v7.promotion_gate(rows, 9)
    assert not v7.promotion_gate(rows[:1], 15)
    rows[-1]['improvement_vs_v2_pct'] = 1.99
    assert not v7.promotion_gate(rows, 15)
    rows[-1]['improvement_vs_v2_pct'] = np.nan
    assert not v7.promotion_gate(rows, 15)


def test_completed_or_incomplete_registered_study_is_never_overwritten(tmp_path, monkeypatch):
    path = tmp_path / 'protocol.json'
    path.write_text('{"retained":"failed or complete"}')
    monkeypatch.setattr(v7, 'OUTPUT', tmp_path)
    monkeypatch.setattr(v7, 'load_fit_frames', lambda _: pytest.fail('Opened labels after registration'))
    v7.run()
    assert json.loads(path.read_text()) == {'retained': 'failed or complete'}


def test_saved_metrics_scope_and_hashes_are_independently_recomputed():
    root = Path(__file__).resolve().parents[1]
    output = root / 'artifacts/experiments/v7'
    if not (output / 'summary.json').exists():
        pytest.skip('Registered study not executed yet')
    protocol = json.loads((output / 'protocol.json').read_text())
    summary = json.loads((output / 'summary.json').read_text())
    records = json.loads((output / 'oof_predictions.json').read_text())
    assert summary['protocol_sha256'] == v7.v2.sha(output / 'protocol.json')
    assert protocol['runner_sha256'] == v7.v2.sha(Path(v7.__file__))
    assert protocol['v6_helper_sha256'] == v7.v2.sha(Path(v7.v6.__file__))
    assert len(records) == 560 * len(v7.SEEDS)
    assert len({(r['id'], r['seed']) for r in records}) == len(records)
    allowed = set(protocol['fit_ids']['Switching'])
    assert {r['id'] for r in records} == allowed
    assert set(protocol['excluded_calibration_ids']['Switching']).isdisjoint(allowed)
    for fold in summary['folds']:
        assert set(fold['fit_ids']).isdisjoint(fold['held_ids'])
        assert set(fold['fit_ids']) | set(fold['held_ids']) == allowed
        assert len(fold['other_fit_ids']) == 448
        assert set(fold['other_fit_ids']) <= set(protocol['fit_ids']['Lightning'])
    observed = np.array([r['observed_crest_kv'] for r in records])
    voltage = np.array([r['test_kv'] for r in records])
    for name, metrics in summary['combined_repeated_development_metrics'].items():
        error = np.array([r['predictions'][name] for r in records]) - observed
        independent = {'rmse_kv': np.sqrt(np.mean(error ** 2)), 'mae_kv': np.mean(abs(error)),
                       'mape_pct': 100 * np.mean(abs(error) / observed),
                       'normalized_rmse_tolerance': np.sqrt(np.mean((error / (.03 * voltage)) ** 2)),
                       'p95_absolute_error_kv': np.quantile(abs(error), .95),
                       'worst_absolute_error_kv': np.max(abs(error))}
        assert metrics == pytest.approx(independent)
    assert summary['promotion_eligible'] == v7.promotion_gate(
        summary['per_seed'], summary['folds_beating_both_baselines'])
    assert not any(summary[key] for key in ('hidden_test_evaluated', 'validation_evaluated',
                                          'calibration_evaluated', 'final_models_created',
                                          'production_model_changed'))
    assert all(v7.v2.sha(root / name) == digest for name, digest in protocol['preserved_sha256'].items())
