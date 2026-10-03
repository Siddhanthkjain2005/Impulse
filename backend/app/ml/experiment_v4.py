"""Partially pooled, Train-only residual experiment; never replaces serving models.

Both impulse regimes' held-out rows are excluded from shared training. Historical
feature exploration makes this development evidence, not a new independent test.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from threadpoolctl import threadpool_limits

from . import experiment_v2 as v2
from .reference_knn import ROOT, OBSERVED, PHYSICS, RESIDUAL

OUTPUT = ROOT / 'artifacts/experiments/v4'
VERSION = 'pooled-physics-v4-development'
BLENDS = [.5, 1.]


class PooledBasis(BaseEstimator, TransformerMixin):
    """Scale only training inputs, then add penalized regime deviations."""

    def __init__(self, degree=1, pooling='shared'):
        self.degree = degree
        self.pooling = pooling

    def fit(self, x, y=None):
        self.scaler_ = StandardScaler().fit(x[:, :-1])
        self.poly_ = PolynomialFeatures(self.degree, include_bias=False)
        z = self.poly_.fit_transform(self.scaler_.transform(x[:, :-1]))
        self.expanded_scaler_ = StandardScaler().fit(z)
        return self

    def transform(self, x):
        z = self.expanded_scaler_.transform(
            self.poly_.transform(self.scaler_.transform(x[:, :-1])))
        group = (2 * x[:, -1] - 1)[:, None]
        if self.pooling == 'shared':
            return z
        if self.pooling == 'offset':
            return np.column_stack([z, group])
        scale = .25 if self.pooling == 'partial' else 1.
        return np.column_stack([z, group, scale * group * z])


def spec_grid():
    return [dict(basis=basis, degree=degree, pooling=pooling, alpha=alpha)
            for basis in ['minimal mechanism', 'extended mechanism']
            for degree in [1, 2]
            for pooling in ['shared', 'offset', 'partial', 'separate slopes']
            for alpha in [.1, 10., 1000.]]


def x_features(frame, target, spec):
    c = (frame.Load_C_pF + frame.Divider_C_pF + frame.Stray_C_pF).to_numpy(float)
    l = frame.L_uH.to_numpy(float)
    load = frame.Load_C_pF.to_numpy(float)
    minimal = [np.column_stack([c, l]), load[:, None], (l * c)[:, None]][target]
    if spec['basis'] == 'extended mechanism':
        minimal = np.column_stack([minimal, np.sqrt(l * c), load / c,
                                    frame.Efficiency.to_numpy(float)])
    return np.column_stack([minimal, (frame.Impulse_Type == 'Switching').to_numpy(float)])


def fit(frame, target, spec):
    model = TransformedTargetRegressor(
        regressor=make_pipeline(PooledBasis(spec['degree'], spec['pooling']),
                                Ridge(alpha=spec['alpha'])),
        transformer=StandardScaler())
    y = frame[RESIDUAL[target]].to_numpy(float) / frame[PHYSICS[target]].to_numpy(float)
    return model.fit(x_features(frame, target, spec), y)


def predict(model, frame, target, spec):
    return model.predict(x_features(frame, target, spec)) * frame[PHYSICS[target]].to_numpy(float)


def paired_folds(frames, n_splits, seed):
    """A shared model must exclude the held-out rows of *both* regimes."""
    partitions = {t: list(KFold(n_splits, shuffle=True, random_state=seed).split(f))
                  for t, f in frames.items()}
    for k in range(n_splits):
        yield ({t: f.iloc[partitions[t][k][0]].reset_index(drop=True) for t, f in frames.items()},
               {t: f.iloc[partitions[t][k][1]].reset_index(drop=True) for t, f in frames.items()})


def select(frames, target, baseline_specs):
    folds = list(paired_folds(frames, 3, 73))
    positions = {t: {int(id_): i for i, id_ in enumerate(f.ID)} for t, f in frames.items()}
    base = {t: np.zeros(len(f)) for t, f in frames.items()}
    for train, held in folds:
        for typ in v2.TYPES:
            indices = [positions[typ][int(id_)] for id_ in held[typ].ID]
            model = v2.fit_spec(train[typ], target, baseline_specs[typ])
            base[typ][indices] = v2.predict_spec(model, held[typ], target, baseline_specs[typ])
    truth = {t: f[RESIDUAL[target]].to_numpy(float) for t, f in frames.items()}
    tol = {t: v2.tolerances(f, t)[:, target] for t, f in frames.items()}
    base_score = {t: float(np.mean(((base[t] - truth[t]) / tol[t]) ** 2)) for t in v2.TYPES}
    chosen = {t: {'blend': 0., 'name': 'Historical V2 refit'} for t in v2.TYPES}
    best = dict(base_score)
    leaders = {t: [] for t in v2.TYPES}
    for spec in spec_grid():
        p = {t: np.zeros(len(f)) for t, f in frames.items()}
        for train, held in folds:
            pooled = pd.concat(list(train.values()), ignore_index=True)
            model = fit(pooled, target, spec)
            for typ in v2.TYPES:
                indices = [positions[typ][int(id_)] for id_ in held[typ].ID]
                p[typ][indices] = predict(model, held[typ], target, spec)
        for typ in v2.TYPES:
            for weight in BLENDS:
                score = float(np.mean(((weight * p[typ] + (1 - weight) * base[typ] - truth[typ]) / tol[typ]) ** 2))
                candidate = {**spec, 'blend': weight}
                leaders[typ].append({**candidate, 'normalized_mse': score})
                if score < best[typ] and score <= base_score[typ] * .98:
                    chosen[typ] = candidate
                    best[typ] = score
    logs = {t: {'baseline_normalized_mse': base_score[t], 'chosen_normalized_mse': best[t],
                'leaders': sorted(leaders[t], key=lambda s: s['normalized_mse'])[:5]} for t in v2.TYPES}
    return chosen, logs


def predict_fold(train, held, target, specs, chosen):
    base = {}
    predictions = {}
    pooled = pd.concat(list(train.values()), ignore_index=True)
    for typ in v2.TYPES:
        model = v2.fit_spec(train[typ], target, specs[typ])
        base[typ] = v2.predict_spec(model, held[typ], target, specs[typ])
        s = chosen[typ]
        predictions[typ] = base[typ] if s['blend'] == 0 else (
            s['blend'] * predict(fit(pooled, target, s), held[typ], target, s)
            + (1 - s['blend']) * base[typ])
    return predictions, base


def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if (OUTPUT / 'summary.json').exists():
        print('Frozen V4 experiment exists; refusing post-result retuning.', flush=True)
        return
    previous = json.loads((ROOT / 'artifacts/experiments/v2/summary.json').read_text())
    split = json.loads((ROOT / 'artifacts/experiments/v2/protocol.json').read_text())
    train = v2.read_split('Train').set_index('ID', drop=False)
    frames = {t: train.loc[split['fit_ids'][t]].reset_index(drop=True) for t in v2.TYPES}
    assert all(len(f) == 560 and f.ID.is_unique and set(f.Split) == {'Train'} for f in frames.values())
    preserved = {str(p.relative_to(ROOT)): v2.sha(p)
                 for directory in ['artifacts/models', 'artifacts/experiments/v2', 'artifacts/experiments/v3']
                 for p in (ROOT / directory).rglob('*') if p.is_file()}
    protocol = {
        'version': VERSION, 'registered_at': datetime.now(timezone.utc).isoformat(),
        'runner_sha256': v2.sha(Path(__file__)), 'helper_sha256': v2.sha(Path(v2.__file__)),
        'dataset_sha256': v2.sha(ROOT / 'data/processed/synthetic_dataset.csv'),
        'fit_ids': split['fit_ids'], 'excluded_calibration_ids': split['calibration_ids'],
        'preserved_sha256': preserved, 'grid': spec_grid(), 'blends': BLENDS,
        'outer': {'folds': 5, 'seed': 71}, 'inner': {'folds': 3, 'seed': 73},
        'selection': 'Per-output/per-regime inner tolerance-normalized MSE. At least 2% lower MSE than same-row historical V2 refit to select a pooled candidate.',
        'pooling': 'Shared relative corrections with optional regime intercepts and penalized regime slopes. Both regimes exclude held-out rows in every inner and outer fit.',
        'promotion': 'At least 5% macro tolerance-normalized RMSE improvement and no output >2% worse. Passing does not change serving; independent evidence still required.',
        'scope': 'Train development experiment using previously explored features and historically selected V2 parameters. Reused outer folds; no independent final test, calibration or laboratory evaluation.',
        'labels_opened': ['original 560 Train fit rows per impulse type'],
    }
    protocol_path = OUTPUT / 'protocol.json'
    if protocol_path.exists():
        prior = json.loads(protocol_path.read_text())
        assert {k: v for k, v in prior.items() if k != 'registered_at'} == {k: v for k, v in protocol.items() if k != 'registered_at'}
    else:
        protocol_path.write_text(json.dumps(protocol, indent=2))
    started = time.perf_counter()
    oof = []
    choices = []
    for k, (a, b) in enumerate(paired_folds(frames, 5, 71)):
        p = {t: np.zeros((len(b[t]), 3)) for t in v2.TYPES}
        base = {t: np.zeros_like(p[t]) for t in v2.TYPES}
        fold_choices = []
        for j in range(3):
            specs = {t: previous['selection'][t][j] for t in v2.TYPES}
            selected, logs = select(a, j, specs)
            pred, bp = predict_fold(a, b, j, specs, selected)
            for typ in v2.TYPES:
                p[typ][:, j] = pred[typ]
                base[typ][:, j] = bp[typ]
            fold_choices.append({'selection': selected, 'inner': logs})
        choices.append(fold_choices)
        all_train_ids = pd.concat(list(a.values()), ignore_index=True).ID.astype(int).tolist()
        for typ in v2.TYPES:
            physics = b[typ][PHYSICS].to_numpy(float)
            for i, (_, row) in enumerate(b[typ].iterrows()):
                oof.append({'id': int(row.ID), 'type': typ, 'fold': k, 'train_ids': all_train_ids,
                            'observed': row[OBSERVED].to_numpy(float).tolist(),
                            'v4_prediction': (physics[i] + p[typ][i]).tolist(),
                            'v2_refit_prediction': (physics[i] + base[typ][i]).tolist()})
        print(f'Paired Lightning + Switching fold {k + 1}/5 complete', flush=True)
    result = {'version': VERSION, 'scope': protocol['scope'], 'protocol_sha256': v2.sha(protocol_path),
              'nested_cv': {}, 'fold_choices': choices}
    for typ in v2.TYPES:
        rows = {r['id']: r for r in oof if r['type'] == typ}
        table = {name: v2.metric_report(frames[typ], np.array([rows[int(id_)][key] for id_ in frames[typ].ID]), typ)
                 for name, key in [('V4 pooling search', 'v4_prediction'), ('Historical V2 refit', 'v2_refit_prediction')]}
        gain = 100 * (1 - np.array(table['V4 pooling search']['rmse']) / table['Historical V2 refit']['rmse'])
        result['nested_cv'][typ] = {'metrics': table, 'improvement_vs_v2_pct': gain.tolist()}
    baseline = np.concatenate([result['nested_cv'][t]['metrics']['Historical V2 refit']['normalized_rmse_tolerance'] for t in v2.TYPES])
    candidate = np.concatenate([result['nested_cv'][t]['metrics']['V4 pooling search']['normalized_rmse_tolerance'] for t in v2.TYPES])
    gains = np.concatenate([result['nested_cv'][t]['improvement_vs_v2_pct'] for t in v2.TYPES])
    macro = float(100 * (1 - candidate.mean() / baseline.mean()))
    eligible = bool(macro >= 5 and gains.min() >= -2)
    result.update(macro_improvement_pct=macro, worst_target_improvement_pct=float(gains.min()),
                  promotion_eligible=eligible, hidden_test_evaluated=False, calibration_evaluated=False,
                  validation_evaluated=False, cloud_spend_usd=0, elapsed_seconds=time.perf_counter() - started,
                  active_model='residual-competition-v1',
                  decision='Candidate merits new independent evaluation; V1/V2 unchanged.' if eligible else 'No promotion: pooled corrections did not meet the preregistered improvement gate. V1/V2 unchanged.')
    assert all(v2.sha(ROOT / p) == digest for p, digest in preserved.items())
    result['preserved_artifacts_verified'] = True
    (OUTPUT / 'oof_predictions.json').write_text(json.dumps(oof, separators=(',', ':')))
    (OUTPUT / 'summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ['macro_improvement_pct', 'worst_target_improvement_pct', 'promotion_eligible', 'decision', 'elapsed_seconds']}), flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        run()
