"""Switching-crest champion study on original Train fit IDs only.

This repeated nested development comparison never alters serving, calibrates,
or evaluates Validation/Hidden Test. The previously explored dataset and
historically selected V2 comparator prevent an independent accuracy claim.
"""
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import SplineTransformer, StandardScaler
from threadpoolctl import threadpool_limits

from . import experiment_v2 as v2
from .experiment_v5 import load_fit_frames
from .reference_knn import ROOT, WorkbookKNN

VERSION = 'switching-crest-champion-v6-development'
OUTPUT = ROOT / 'artifacts/experiments/v6'
SEEDS = (191, 293, 397)
BLENDS = (.5, 1.)
TARGET = 2


def grid():
    specs = []
    for weighted in (False, True):
        for alpha in (.01, 1., 100.):
            specs.append(dict(name='Relative Ridge', alpha=alpha, weighted=weighted))
        for alpha in (1., 10.):
            specs.append(dict(name='Relative Spline', alpha=alpha, weighted=weighted))
    for gamma in (.1, 1.):
        specs.append(dict(name='Relative Kernel Ridge', alpha=.1, gamma=gamma, weighted=False))
    for k in (31, 63, 127):
        specs.append(dict(name='Detrended local mean', alpha=1., k=k, weighted=False))
    return specs


def mechanism(frame):
    total = (frame.Load_C_pF + frame.Divider_C_pF + frame.Stray_C_pF).to_numpy(float)
    inductance = frame.L_uH.to_numpy(float)
    return np.column_stack((total, inductance, total * inductance))


class CrestRegressor:
    def __init__(self, spec):
        self.spec = dict(spec)

    def fit(self, frame):
        crest = frame.Physics_Crest_kV.to_numpy(float)
        if not np.isfinite(crest).all() or np.any(crest <= 0):
            raise ValueError('Positive finite physics crest required.')
        y = frame.Residual_Crest.to_numpy(float) / crest
        self.scaler = StandardScaler().fit(mechanism(frame))
        x = self.scaler.transform(mechanism(frame))
        self.spline = None
        self.expanded_scaler = None
        if self.spec['name'] == 'Relative Spline':
            self.spline = SplineTransformer(n_knots=3, degree=3, include_bias=False).fit(x)
            x = self.spline.transform(x)
            self.expanded_scaler = StandardScaler().fit(x)
            x = self.expanded_scaler.transform(x)
        self.reg = (KernelRidge(alpha=self.spec['alpha'], gamma=self.spec['gamma'], kernel='rbf')
                    if self.spec['name'] == 'Relative Kernel Ridge' else Ridge(alpha=self.spec['alpha']))
        weights = (crest / np.median(crest)) ** 2 if self.spec['weighted'] else None
        self.reg.fit(x, y, sample_weight=weights)
        self.local = None
        if self.spec['name'] == 'Detrended local mean':
            self.local = KNeighborsRegressor(n_neighbors=min(self.spec['k'], len(frame)), weights='uniform')
            self.local.fit(x, y - self.reg.predict(x))
        self.fit_ids = frame.ID.astype(int).tolist()
        return self

    def predict(self, frame):
        x = self.scaler.transform(mechanism(frame))
        if self.spline is not None:
            x = self.expanded_scaler.transform(self.spline.transform(x))
        relative = self.reg.predict(x)
        if self.local is not None:
            relative = relative + self.local.predict(x)
        return relative * frame.Physics_Crest_kV.to_numpy(float)


def baseline_predictions(train, other_train, held, historical):
    model = v2.fit_spec(train, TARGET, historical)
    return {
        'Historical V2 refit': v2.predict_spec(model, held, TARGET, historical),
        'Matched exact kNN': WorkbookKNN(pd.concat([train, other_train], ignore_index=True)).predict(held)[:, TARGET],
    }


def select(train, other_train, historical, seed):
    truth = train.Residual_Crest.to_numpy(float)
    folds = list(KFold(3, shuffle=True, random_state=seed).split(train))
    other_folds = list(KFold(3, shuffle=True, random_state=seed).split(other_train))
    base = {name: np.zeros(len(train)) for name in ('Historical V2 refit', 'Matched exact kNN')}
    for fold, (a, b) in enumerate(folds):
        predictions = baseline_predictions(train.iloc[a], other_train.iloc[other_folds[fold][0]], train.iloc[b], historical)
        for name in base:
            base[name][b] = predictions[name]
    scores = {name: float(np.mean((prediction - truth) ** 2)) for name, prediction in base.items()}
    champion = min(scores, key=scores.get)
    selection = {'name': 'Inner-selected baseline', 'baseline': champion, 'blend': 0.}
    best_score = scores[champion]
    leaderboard = []
    for spec in grid():
        prediction = np.zeros(len(train))
        for a, b in folds:
            prediction[b] = CrestRegressor(spec).fit(train.iloc[a]).predict(train.iloc[b])
        for weight in BLENDS:
            score = float(np.mean((weight * prediction + (1 - weight) * base[champion] - truth) ** 2))
            choice = {**spec, 'baseline': champion, 'blend': weight}
            leaderboard.append({**choice, 'inner_mse_kv2': score})
            # A new fit must improve inner MSE at least 2% over BOTH baselines.
            if score < best_score and score <= scores[champion] * .98:
                selection, best_score = choice, score
    return selection, {'baseline_inner_mse_kv2': scores, 'selected_inner_mse_kv2': best_score,
                       'leaders': sorted(leaderboard, key=lambda s: s['inner_mse_kv2'])[:5]}


def chosen_prediction(train, held, selection, baselines):
    base = baselines[selection['baseline']]
    if selection['blend'] == 0:
        return base
    fitted = CrestRegressor(selection).fit(train)
    return selection['blend'] * fitted.predict(held) + (1 - selection['blend']) * base


def stats(observed, prediction, voltage):
    error = np.asarray(prediction) - np.asarray(observed)
    return {'rmse_kv': float(np.sqrt(np.mean(error ** 2))),
            'mae_kv': float(np.mean(abs(error))),
            'mape_pct': float(100 * np.mean(abs(error) / np.asarray(observed))),
            'normalized_rmse_tolerance': float(np.sqrt(np.mean((error / (.03 * np.asarray(voltage))) ** 2))),
            'p95_absolute_error_kv': float(np.quantile(abs(error), .95)),
            'worst_absolute_error_kv': float(np.max(abs(error)))}


def promotion_gate(per_seed, fold_wins):
    return bool(all(row['improvement_vs_v2_pct'] >= 2 and row['improvement_vs_knn_pct'] >= 2
                    for row in per_seed) and fold_wins >= 10)


def run():
    if (OUTPUT / 'summary.json').exists() or (OUTPUT / 'oof_predictions.json').exists():
        print('Frozen V6 results exist; no post-result retuning.', flush=True)
        return
    split = json.loads((ROOT / 'artifacts/experiments/v2/protocol.json').read_text())
    historical = json.loads((ROOT / 'artifacts/experiments/v2/summary.json').read_text())['selection']['Switching'][TARGET]
    integrity = json.loads((ROOT / 'config/release_integrity.json').read_text())['files']
    assert all(v2.sha(ROOT / name) == expected for name, expected in integrity.items())
    protocol = {
        'version': VERSION, 'registered_at': datetime.now(timezone.utc).isoformat(),
        'runner_sha256': v2.sha(Path(__file__)), 'v2_helper_sha256': v2.sha(Path(v2.__file__)),
        'fit_loader_sha256': v2.sha(ROOT / 'backend/app/ml/experiment_v5.py'),
        'reference_helper_sha256': v2.sha(ROOT / 'backend/app/ml/reference_knn.py'),
        'dataset_sha256': v2.sha(ROOT / 'data/processed/synthetic_dataset.csv'),
        'fit_ids': split['fit_ids'], 'excluded_calibration_ids': split['calibration_ids'],
        'preserved_sha256': integrity, 'historical_v2_spec': historical,
        'grid': grid(), 'blends': list(BLENDS), 'outer': {'folds': 5, 'seeds': list(SEEDS)},
        'inner': {'folds': 3, 'seed': 'outer seed + 1000 + fold'},
        'hypothesis': 'A compact smooth relative trend or trend-plus-local averaging may reduce Switching crest variance beyond the historical tree model while retaining exact kNN as a competing fallback.',
        'selection': 'Minimum inner physical-unit MSE; replace the better inner V2/kNN baseline only with at least 2% lower MSE. All feature/scaler/regression/local fits occur inside folds. Other-regime outer/inner held rows are also excluded from exact kNN.',
        'promotion': 'Crest RMSE improves at least 2% versus both V2 and exact kNN in EVERY seed, with at least 10 of 15 folds beating both. This only merits new independent evaluation; no automatic serving change.',
        'scope': 'Repeated nested Train CV development. Features and these rows have been explored; historical V2 selection and exploratory crest study preceded this protocol. Fresh fold seeds do not create fresh data. Repeated predictions are not independent shots.',
        'labels_used': 'Original 560 Train fit IDs per type only. Switching crest is the sole searched target; Lightning fit outcomes only enter fold-restricted exact kNN.',
        'stopping_rule': 'One fixed grid and three seeds; no expansion after outer results. No weights for serving or new calibration intervals.',
        'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__},
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    protocol_path = OUTPUT / 'protocol.json'
    if protocol_path.exists():
        saved = json.loads(protocol_path.read_text())
        assert {k: v for k, v in saved.items() if k != 'registered_at'} == {k: v for k, v in protocol.items() if k != 'registered_at'}
    else:
        protocol_path.write_text(json.dumps(protocol, indent=2))
    started = time.perf_counter()
    frames = load_fit_frames(split)
    frame, other = frames['Switching'], frames['Lightning']
    assert len(frame) == len(other) == 560
    records, fold_records, seed_results = [], [], []
    names = ('V6 champion search', 'Historical V2 refit', 'Matched exact kNN', 'Compact Ridge control')
    fold_wins = 0
    for seed in SEEDS:
        outer = list(KFold(5, shuffle=True, random_state=seed).split(frame))
        other_outer = list(KFold(5, shuffle=True, random_state=seed).split(other))
        predictions = {name: np.zeros(len(frame)) for name in names}
        for fold, (a, b) in enumerate(outer):
            train, held, other_train = frame.iloc[a], frame.iloc[b], other.iloc[other_outer[fold][0]]
            selection, log = select(train, other_train, historical, seed + 1000 + fold)
            baselines = baseline_predictions(train, other_train, held, historical)
            residual = chosen_prediction(train, held, selection, baselines)
            physics = held.Physics_Crest_kV.to_numpy(float)
            predictions[names[0]][b] = physics + residual
            for name, residuals in baselines.items():
                predictions[name][b] = physics + residuals
            control = CrestRegressor(dict(name='Relative Ridge', alpha=.01, weighted=False)).fit(train)
            predictions[names[3]][b] = physics + control.predict(held)
            truth = held.Observed_Crest_kV.to_numpy(float)
            fold_metrics = {name: stats(truth, predictions[name][b], held.Test_kV) for name in names}
            winner = fold_metrics[names[0]]['rmse_kv'] < min(fold_metrics[n]['rmse_kv'] for n in names[1:3])
            fold_wins += int(winner)
            fold_records.append({'seed': seed, 'fold': fold, 'selection': selection, **log,
                                 'fit_ids': train.ID.astype(int).tolist(), 'other_fit_ids': other_train.ID.astype(int).tolist(),
                                 'held_ids': held.ID.astype(int).tolist(), 'metrics': fold_metrics, 'beats_both_baselines': bool(winner)})
            print(f'Switching crest seed {seed} fold {fold + 1}/5 complete', flush=True)
        metrics = {name: stats(frame.Observed_Crest_kV, prediction, frame.Test_kV) for name, prediction in predictions.items()}
        gains = {'improvement_vs_v2_pct': 100 * (1 - metrics[names[0]]['rmse_kv'] / metrics[names[1]]['rmse_kv']),
                 'improvement_vs_knn_pct': 100 * (1 - metrics[names[0]]['rmse_kv'] / metrics[names[2]]['rmse_kv'])}
        seed_results.append({'seed': seed, 'metrics': metrics, **gains})
        for i, row in frame.iterrows():
            records.append({'id': int(row.ID), 'seed': seed, 'fold': next(k for k, (_, b) in enumerate(outer) if i in b),
                            'observed_crest_kv': float(row.Observed_Crest_kV), 'physics_crest_kv': float(row.Physics_Crest_kV),
                            'test_kv': float(row.Test_kV),
                            'predictions': {name: float(prediction[i]) for name, prediction in predictions.items()}})
    combined = {name: stats([r['observed_crest_kv'] for r in records], [r['predictions'][name] for r in records],
                           [r['test_kv'] for r in records]) for name in names}
    eligible = promotion_gate(seed_results, fold_wins)
    assert all(v2.sha(ROOT / name) == expected for name, expected in integrity.items())
    result = {'version': VERSION, 'scope': protocol['scope'], 'protocol_sha256': v2.sha(protocol_path),
              'per_seed': seed_results, 'combined_repeated_development_metrics': combined,
              'folds_beating_both_baselines': fold_wins, 'folds': fold_records,
              'promotion_eligible': eligible, 'hidden_test_evaluated': False, 'validation_evaluated': False,
              'calibration_evaluated': False, 'final_models_created': False, 'production_model_changed': False,
              'preserved_artifacts_verified': True, 'cloud_spend_usd': 0, 'elapsed_seconds': time.perf_counter() - started,
              'decision': 'Crest development gate passed; independent outcomes required before a serving change.' if eligible else 'Crest development gate failed; frozen serving and prior evidence remain unchanged.'}
    (OUTPUT / 'oof_predictions.json').write_text(json.dumps(records, separators=(',', ':')))
    (OUTPUT / 'summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'promotion_eligible': eligible, 'folds_beating_both_baselines': fold_wins,
                      'combined': combined, 'elapsed_seconds': result['elapsed_seconds']}), flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        run()
