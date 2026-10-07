import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.app.ml import experiment_v6 as v6


def frame(n=30, start=1):
    rng = np.random.default_rng(47)
    total = rng.uniform(900, 1700, n)
    inductance = rng.uniform(10, 25, n)
    voltage = rng.uniform(900, 1300, n)
    residual = voltage * (-.002 - total * inductance * 1e-7)
    return pd.DataFrame({'ID': np.arange(start, start + n), 'Load_C_pF': total,
                         'Divider_C_pF': np.zeros(n), 'Stray_C_pF': np.zeros(n),
                         'L_uH': inductance, 'Physics_Crest_kV': voltage,
                         'Residual_Crest': residual, 'Observed_Crest_kV': voltage + residual,
                         'Test_kV': voltage})


@pytest.mark.parametrize('spec', v6.grid())
def test_crest_prediction_never_uses_query_outcomes(spec):
    train, held = frame(), frame(8, 100)
    model = v6.CrestRegressor(spec).fit(train)
    expected = model.predict(held)
    changed = held.copy()
    changed[['Observed_Crest_kV', 'Residual_Crest']] = np.nan
    np.testing.assert_array_equal(expected, model.predict(changed))
    assert np.isfinite(expected).all()
    assert set(model.fit_ids).isdisjoint(held.ID)


def test_inner_selection_refits_without_any_query_ids(monkeypatch):
    train, other = frame(18), frame(18, 100)
    visited = []

    def baselines(fit, other_fit, held, historical):
        assert set(fit.ID).isdisjoint(held.ID)
        assert set(other_fit.ID).isdisjoint(held.ID)
        assert len(fit) == len(other_fit) == 12
        visited.append(('baseline', set(fit.ID), set(held.ID)))
        return {name: np.zeros(len(held)) for name in ('Historical V2 refit', 'Matched exact kNN')}

    class SpyRegressor:
        def __init__(self, spec): pass
        def fit(self, fit):
            self.ids = set(fit.ID)
            return self
        def predict(self, held):
            assert self.ids.isdisjoint(held.ID)
            visited.append(('candidate', self.ids, set(held.ID)))
            return np.zeros(len(held))

    monkeypatch.setattr(v6, 'baseline_predictions', baselines)
    monkeypatch.setattr(v6, 'CrestRegressor', SpyRegressor)
    monkeypatch.setattr(v6, 'grid', lambda: [{'name': 'spy'}])
    selection, log = v6.select(train, other, {}, 131)
    assert len(visited) == 6
    assert set.union(*(held for _, _, held in visited)) == set(train.ID)
    assert selection['blend'] == 0
    assert log['selected_inner_mse_kv2'] > 0


def test_gate_requires_all_seeds_and_majority_of_folds():
    rows = [dict(improvement_vs_v2_pct=2., improvement_vs_knn_pct=5.) for _ in v6.SEEDS]
    assert v6.promotion_gate(rows, 10)
    assert not v6.promotion_gate(rows, 9)
    rows[-1]['improvement_vs_v2_pct'] = 1.99
    assert not v6.promotion_gate(rows, 15)
    rows[-1] = dict(improvement_vs_v2_pct=3., improvement_vs_knn_pct=-1.)
    assert not v6.promotion_gate(rows, 15)


def test_frozen_result_cannot_trigger_another_fit(tmp_path, monkeypatch):
    (tmp_path / 'summary.json').write_text('{}')
    monkeypatch.setattr(v6, 'OUTPUT', tmp_path)
    monkeypatch.setattr(v6, 'load_fit_frames', lambda _: pytest.fail('Opened labels after frozen result'))
    v6.run()
    assert json.loads((tmp_path / 'summary.json').read_text()) == {}


def test_development_metrics_retain_physical_error_and_failures():
    result = v6.stats([100., 200.], [103., 194.], [100., 200.])
    assert result['rmse_kv'] == pytest.approx(np.sqrt(22.5))
    assert result['mape_pct'] == pytest.approx(3.)
    assert result['normalized_rmse_tolerance'] == pytest.approx(1.)
    assert result['worst_absolute_error_kv'] == 6.


def test_recorded_study_preserves_splits_hashes_and_recomputed_scores():
    root = Path(__file__).resolve().parents[1]
    output = root / 'artifacts/experiments/v6'
    protocol = json.loads((output / 'protocol.json').read_text())
    summary = json.loads((output / 'summary.json').read_text())
    records = json.loads((output / 'oof_predictions.json').read_text())
    assert summary['protocol_sha256'] == v6.v2.sha(output / 'protocol.json')
    assert protocol['runner_sha256'] == v6.v2.sha(Path(v6.__file__))
    assert len(records) == 560 * len(v6.SEEDS)
    assert len({(r['id'], r['seed']) for r in records}) == len(records)
    assert {r['id'] for r in records} == set(protocol['fit_ids']['Switching'])
    assert set(protocol['excluded_calibration_ids']['Switching']).isdisjoint(r['id'] for r in records)
    for fold in summary['folds']:
        assert set(fold['fit_ids']).isdisjoint(fold['held_ids'])
        assert set(fold['fit_ids']) | set(fold['held_ids']) == set(protocol['fit_ids']['Switching'])
        assert set(fold['other_fit_ids']) <= set(protocol['fit_ids']['Lightning'])
    for name, metrics in summary['combined_repeated_development_metrics'].items():
        recomputed = v6.stats([r['observed_crest_kv'] for r in records],
                              [r['predictions'][name] for r in records], [r['test_kv'] for r in records])
        assert metrics == pytest.approx(recomputed)
    assert summary['promotion_eligible'] == v6.promotion_gate(summary['per_seed'], summary['folds_beating_both_baselines'])
    assert not any(summary[key] for key in ('hidden_test_evaluated','validation_evaluated','calibration_evaluated','final_models_created','production_model_changed'))
    assert all(v6.v2.sha(root / name) == digest for name, digest in protocol['preserved_sha256'].items())
