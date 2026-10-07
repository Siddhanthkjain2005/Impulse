"""Registered spline-envelope crest development study; no serving changes.

Only the original Train fit IDs enter numerical fits. Repeated use of those
rows and historical feature/model choices prevents an independent accuracy
claim, even if the fixed development gate passes.
"""
import json
import platform
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.optimize import linprog
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import BayesianRidge, QuantileRegressor, Ridge
from sklearn.model_selection import KFold
from sklearn.preprocessing import SplineTransformer, StandardScaler
from threadpoolctl import threadpool_limits

from . import experiment_v2 as v2
from . import experiment_v6 as v6
from .experiment_v5 import load_fit_frames
from .reference_knn import ROOT, WorkbookKNN

OUTPUT = ROOT / 'artifacts/experiments/v7'
VERSION = 'spline-envelope-v7-development'
SEEDS = (503, 607, 709)
TARGET = 2
NAMES = ('V7 envelope search', 'Historical V2 refit', 'Matched exact kNN',
         'Compact V6 spline control')


def grid():
    return [dict(basis=basis, **spec) for basis in ('full', 'additive') for spec in (
        dict(name='Ridge control', alpha=1.),
        dict(name='Bayesian Ridge'),
        dict(name='Regularized minimax envelope', penalty=.001),
        dict(name='Regularized minimax envelope', penalty=.01),
        dict(name='Quantile center', alpha=.0001),
        dict(name='Quantile center', alpha=.001),
    )]


def mechanism(frame, basis):
    total = (frame.Load_C_pF + frame.Divider_C_pF + frame.Stray_C_pF).to_numpy(float)
    inductance = frame.L_uH.to_numpy(float)
    if basis not in ('full', 'additive'):
        raise ValueError('Unknown spline basis.')
    return np.column_stack((total, inductance, total * inductance) if basis == 'full'
                           else (total, inductance))


class SolverFailure(RuntimeError):
    """A candidate cannot be scored because its numerical fit is unresolved."""


class CrestRegressor:
    def __init__(self, spec):
        self.spec = dict(spec)

    def fit(self, frame):
        crest = frame.Physics_Crest_kV.to_numpy(float)
        if not np.isfinite(crest).all() or np.any(crest <= 0):
            raise ValueError('Positive finite physics crest required.')
        relative = frame.Residual_Crest.to_numpy(float) / crest
        if not np.isfinite(relative).all():
            raise ValueError('Finite training residuals required.')
        self.input_scaler = StandardScaler().fit(mechanism(frame, self.spec['basis']))
        x = self.input_scaler.transform(mechanism(frame, self.spec['basis']))
        self.spline = SplineTransformer(n_knots=3, degree=3, include_bias=False).fit(x)
        self.expanded_scaler = StandardScaler().fit(self.spline.transform(x))
        z = self.expanded_scaler.transform(self.spline.transform(x))
        self.target_scaler = StandardScaler().fit(relative.reshape(-1, 1))
        y = self.target_scaler.transform(relative.reshape(-1, 1)).ravel()
        name = self.spec['name']
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always', ConvergenceWarning)
            warnings.simplefilter('always', RuntimeWarning)
            if name == 'Regularized minimax envelope':
                self._fit_envelope(z, y)
            elif name == 'Quantile center':
                self.regressors = [QuantileRegressor(quantile=q, alpha=self.spec['alpha'],
                                                    solver='highs').fit(z, y) for q in (.1, .9)]
            elif name == 'Ridge control':
                self.regressors = [Ridge(alpha=self.spec['alpha']).fit(z, y)]
            elif name == 'Bayesian Ridge':
                self.regressors = [BayesianRidge(max_iter=1000, tol=1e-6).fit(z, y)]
            else:
                raise ValueError('Unknown estimator.')
            failures = [str(w.message) for w in recorded
                        if issubclass(w.category, (ConvergenceWarning, RuntimeWarning))]
            if failures:
                raise SolverFailure('; '.join(failures))
        self.fit_ids = frame.ID.astype(int).tolist()
        # Numerical failure on fitted rows is logged exactly like solver failure.
        self.predict(frame)
        return self

    def _fit_envelope(self, z, y):
        # Variables: signed spline coefficients, unpenalized intercept, radius,
        # and nonnegative absolute-coefficient bounds. Inputs and target are
        # standardized within the training fold. No noise bound is supplied.
        n, p = z.shape
        design = np.column_stack((z, np.ones(n)))
        width = 2 * p + 2
        constraints = np.zeros((2 * n + 2 * p, width))
        constraints[:n, :p + 1] = design
        constraints[n:2 * n, :p + 1] = -design
        constraints[:2 * n, p + 1] = -1
        constraints[2 * n:2 * n + p, :p] = np.eye(p)
        constraints[2 * n + p:, :p] = -np.eye(p)
        constraints[2 * n:2 * n + p, p + 2:] = -np.eye(p)
        constraints[2 * n + p:, p + 2:] = -np.eye(p)
        limits = np.concatenate((y, -y, np.zeros(2 * p)))
        objective = np.zeros(width)
        objective[p + 1] = 1
        objective[p + 2:] = self.spec['penalty']
        result = linprog(objective, A_ub=constraints, b_ub=limits,
                         bounds=[(None, None)] * (p + 1) + [(0, None)] * (p + 1),
                         method='highs', options={'primal_feasibility_tolerance': 1e-9,
                                                   'dual_feasibility_tolerance': 1e-9,
                                                   'ipm_optimality_tolerance': 1e-10})
        if not result.success or result.x is None or not np.isfinite(result.x).all():
            raise SolverFailure(f'Envelope solver unresolved: {result.message}')
        violation = float(np.max(constraints @ result.x - limits))
        if violation > 1e-7:
            raise SolverFailure(f'Envelope primal constraint violation {violation:.9g}')
        self.coefficients = result.x[:p + 1]
        self.radius = float(result.x[p + 1])

    def predict(self, frame):
        x = self.input_scaler.transform(mechanism(frame, self.spec['basis']))
        z = self.expanded_scaler.transform(self.spline.transform(x))
        if self.spec['name'] == 'Regularized minimax envelope':
            prediction = np.column_stack((z, np.ones(len(z)))) @ self.coefficients
        else:
            prediction = np.mean([model.predict(z) for model in self.regressors], axis=0)
        relative = self.target_scaler.inverse_transform(np.asarray(prediction).reshape(-1, 1)).ravel()
        residual = relative * frame.Physics_Crest_kV.to_numpy(float)
        if not np.isfinite(residual).all():
            raise SolverFailure('Candidate produced nonfinite predictions.')
        return residual


def baseline_predictions(train, other_train, held, historical):
    model = v2.fit_spec(train, TARGET, historical)
    return {'Historical V2 refit': v2.predict_spec(model, held, TARGET, historical),
            'Matched exact kNN': WorkbookKNN(pd.concat([train, other_train], ignore_index=True)).predict(held)[:, TARGET]}


def safe_prediction(spec, train, held, failures, stage):
    try:
        return CrestRegressor(spec).fit(train).predict(held)
    except SolverFailure as failure:
        failures.append({'stage': stage, 'spec': dict(spec), 'error': str(failure),
                         'fit_ids': train.ID.astype(int).tolist(),
                         'held_ids': held.ID.astype(int).tolist()})
        return None


def select(train, other_train, historical, seed):
    truth = train.Residual_Crest.to_numpy(float)
    folds = list(KFold(3, shuffle=True, random_state=seed).split(train))
    other_folds = list(KFold(3, shuffle=True, random_state=seed).split(other_train))
    baseline = {name: np.zeros(len(train)) for name in NAMES[1:3]}
    for fold, (a, b) in enumerate(folds):
        prediction = baseline_predictions(train.iloc[a], other_train.iloc[other_folds[fold][0]],
                                          train.iloc[b], historical)
        for name in baseline:
            baseline[name][b] = prediction[name]
    scores = {name: float(np.mean((prediction - truth) ** 2)) for name, prediction in baseline.items()}
    champion = min(scores, key=scores.get)
    selection = {'name': 'Inner-selected baseline', 'baseline': champion}
    best = scores[champion]
    failures, leaderboard = [], []
    for spec in grid():
        prediction = np.zeros(len(train))
        failed = False
        for fold, (a, b) in enumerate(folds):
            held_prediction = safe_prediction(spec, train.iloc[a], train.iloc[b], failures,
                                              f'inner seed {seed} fold {fold}')
            if held_prediction is None:
                failed = True
                break
            prediction[b] = held_prediction
        if failed:
            leaderboard.append({**spec, 'inner_mse_kv2': None, 'numerical_failure': True})
            continue
        score = float(np.mean((prediction - truth) ** 2))
        leaderboard.append({**spec, 'inner_mse_kv2': score, 'numerical_failure': False})
        if score < best and score <= scores[champion] * .98:
            selection, best = {**spec, 'baseline': champion}, score
    return selection, {'baseline_inner_mse_kv2': scores, 'selected_inner_mse_kv2': best,
                       'leaderboard': leaderboard, 'numerical_failures': failures}


def chosen_prediction(train, held, selection, baselines, failures, stage):
    if selection['name'] == 'Inner-selected baseline':
        return baselines[selection['baseline']]
    prediction = safe_prediction(selection, train, held, failures, stage)
    return baselines[selection['baseline']] if prediction is None else prediction


def promotion_gate(per_seed, fold_wins):
    return bool(len(per_seed) == len(SEEDS) and all(
        np.isfinite(row['improvement_vs_v2_pct']) and np.isfinite(row['improvement_vs_knn_pct'])
        and row['improvement_vs_v2_pct'] >= 2 and row['improvement_vs_knn_pct'] >= 2
        for row in per_seed) and fold_wins >= 10)


def write_once(path, content):
    with path.open('x') as stream:
        json.dump(content, stream, indent=2)


def run():
    if any((OUTPUT / name).exists() for name in
           ('protocol.json', 'summary.json', 'oof_predictions.json', 'failure.json')):
        print('Registered V7 study exists; no overwrite or post-result retuning.', flush=True)
        return
    split = json.loads((ROOT / 'artifacts/experiments/v2/protocol.json').read_text())
    historical = json.loads((ROOT / 'artifacts/experiments/v2/summary.json').read_text())['selection']['Switching'][TARGET]
    integrity = json.loads((ROOT / 'config/release_integrity.json').read_text())['files']
    assert all(v2.sha(ROOT / name) == expected for name, expected in integrity.items())
    preserved = dict(integrity)
    for version in range(2, 7):
        for path in sorted((ROOT / f'artifacts/experiments/v{version}').rglob('*')):
            if path.is_file():
                preserved[str(path.relative_to(ROOT))] = v2.sha(path)
        path = ROOT / f'backend/app/ml/experiment_v{version}.py'
        preserved[str(path.relative_to(ROOT))] = v2.sha(path)
    protocol = {
        'version': VERSION, 'registered_at': datetime.now(timezone.utc).isoformat(),
        'runner_sha256': v2.sha(Path(__file__)), 'v2_helper_sha256': v2.sha(Path(v2.__file__)),
        'v6_helper_sha256': v2.sha(Path(v6.__file__)),
        'fit_loader_sha256': v2.sha(ROOT / 'backend/app/ml/experiment_v5.py'),
        'reference_helper_sha256': v2.sha(ROOT / 'backend/app/ml/reference_knn.py'),
        'dataset_sha256': v2.sha(ROOT / 'data/processed/synthetic_dataset.csv'),
        'fit_ids': split['fit_ids'], 'excluded_calibration_ids': split['calibration_ids'],
        'preserved_sha256': preserved, 'historical_v2_spec': historical, 'grid': grid(),
        'transforms': 'Unweighted relative crest residual. Fold-fitted input scaling, cubic spline with 3 knots and include_bias=False, expanded scaling, and target standardization. Minimax minimizes radius plus penalty times standardized-coefficient L1 norm; intercept unpenalized. Quantile center averages .1/.9 fitted quantiles. BayesianRidge max_iter=1000 tol=1e-6, other sklearn defaults.',
        'outer': {'folds': 5, 'seeds': list(SEEDS)},
        'inner': {'folds': 3, 'seed': 'outer seed + 1000 + fold'},
        'control': {'name': 'Relative Spline', 'alpha': 1., 'weighted': False,
                    'basis': 'full C,L,C*L; exact frozen V6 implementation'},
        'hypothesis': 'Multi-input smooth envelope centers or Bayesian regularization may reduce relative trend-fit variance. No known noise-bound or uniform-noise assumption is made.',
        'selection': 'Minimum inner physical-kV MSE; a candidate replaces the better historical V2/exact kNN baseline only at >=2% lower MSE. No blend search. Exact kNN is restricted to both-regime inner/outer fit rows.',
        'promotion': 'At least 2% RMSE improvement over BOTH historical V2 and matched exact kNN in EVERY seed, and at least 10/15 folds beating both. Passing merits only independent evaluation; no automatic serving change.',
        'numerical_policy': 'Explicit numerical solver failure disqualifies that inner candidate; outer failure uses the recorded inner-selected baseline. Every numerical failure includes fit and held IDs. Unexpected errors abort into a retained failure record. LP primal/dual feasibility tolerance=1e-9, IPM optimality tolerance=1e-10; primal constraint violation >1e-7 is rejected. Convergence/Runtime warnings and nonfinite predictions are numerical failures.',
        'scope': 'Repeated nested Train development CV on previously explored rows and features. Fresh seeds are not fresh data. Historical V2 selection is reused. Results cannot establish Hidden Test or laboratory accuracy.',
        'stopping_rule': 'Exactly 12 fixed specs and 3 outer seeds, no grid expansion, retraining, weights, calibration, Validation or Hidden Test evaluation. Existing protocol/results are never overwritten.',
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'scipy': scipy.__version__, 'sklearn': sklearn.__version__},
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    protocol_path = OUTPUT / 'protocol.json'
    write_once(protocol_path, protocol)
    started = time.perf_counter()
    try:
        frames = load_fit_frames(split)
        frame, other = frames['Switching'], frames['Lightning']
        assert len(frame) == len(other) == 560
        records, fold_records, seed_results = [], [], []
        fold_wins = 0
        for seed in SEEDS:
            outer = list(KFold(5, shuffle=True, random_state=seed).split(frame))
            other_outer = list(KFold(5, shuffle=True, random_state=seed).split(other))
            predictions = {name: np.zeros(len(frame)) for name in NAMES}
            assignments = np.empty(len(frame), dtype=int)
            for fold, (a, b) in enumerate(outer):
                train, held, other_train = frame.iloc[a], frame.iloc[b], other.iloc[other_outer[fold][0]]
                selection, log = select(train, other_train, historical, seed + 1000 + fold)
                baselines = baseline_predictions(train, other_train, held, historical)
                residual = chosen_prediction(train, held, selection, baselines,
                                             log['numerical_failures'], f'outer seed {seed} fold {fold}')
                physics = held.Physics_Crest_kV.to_numpy(float)
                predictions[NAMES[0]][b] = physics + residual
                for name, values in baselines.items():
                    predictions[name][b] = physics + values
                control = v6.CrestRegressor(dict(name='Relative Spline', alpha=1., weighted=False)).fit(train)
                predictions[NAMES[3]][b] = physics + control.predict(held)
                assignments[b] = fold
                truth = held.Observed_Crest_kV.to_numpy(float)
                metrics = {name: v6.stats(truth, prediction[b], held.Test_kV) for name, prediction in predictions.items()}
                winner = metrics[NAMES[0]]['rmse_kv'] < min(metrics[n]['rmse_kv'] for n in NAMES[1:3])
                fold_wins += int(winner)
                fold_records.append({'seed': seed, 'fold': fold, 'selection': selection, **log,
                                     'fit_ids': train.ID.astype(int).tolist(),
                                     'other_fit_ids': other_train.ID.astype(int).tolist(),
                                     'held_ids': held.ID.astype(int).tolist(), 'metrics': metrics,
                                     'beats_both_baselines': bool(winner)})
                print(f'Switching crest V7 seed {seed} fold {fold + 1}/5 complete', flush=True)
            metrics = {name: v6.stats(frame.Observed_Crest_kV, prediction, frame.Test_kV)
                       for name, prediction in predictions.items()}
            gain = lambda name: 100 * (1 - metrics[NAMES[0]]['rmse_kv'] / metrics[name]['rmse_kv'])
            seed_results.append({'seed': seed, 'metrics': metrics,
                                 'improvement_vs_v2_pct': gain(NAMES[1]),
                                 'improvement_vs_knn_pct': gain(NAMES[2]),
                                 'improvement_vs_compact_control_pct': gain(NAMES[3])})
            for i, row in frame.iterrows():
                records.append({'id': int(row.ID), 'seed': seed, 'fold': int(assignments[i]),
                                'observed_crest_kv': float(row.Observed_Crest_kV),
                                'physics_crest_kv': float(row.Physics_Crest_kV), 'test_kv': float(row.Test_kV),
                                'predictions': {name: float(prediction[i]) for name, prediction in predictions.items()}})
        combined = {name: v6.stats([r['observed_crest_kv'] for r in records],
                                   [r['predictions'][name] for r in records], [r['test_kv'] for r in records])
                    for name in NAMES}
        eligible = promotion_gate(seed_results, fold_wins)
        assert all(v2.sha(ROOT / name) == digest for name, digest in preserved.items())
        summary = {'version': VERSION, 'scope': protocol['scope'], 'protocol_sha256': v2.sha(protocol_path),
                   'per_seed': seed_results, 'combined_repeated_development_metrics': combined,
                   'folds_beating_both_baselines': fold_wins, 'folds': fold_records,
                   'numerical_failure_count': sum(len(f['numerical_failures']) for f in fold_records),
                   'promotion_eligible': eligible, 'hidden_test_evaluated': False,
                   'validation_evaluated': False, 'calibration_evaluated': False,
                   'final_models_created': False, 'production_model_changed': False,
                   'preserved_artifacts_verified': True, 'cloud_spend_usd': 0,
                   'elapsed_seconds': time.perf_counter() - started,
                   'decision': ('Fixed crest development gate passed; independent outcomes required before a serving change.'
                                if eligible else 'Fixed crest development gate failed; prior serving and evidence remain unchanged.')}
        write_once(OUTPUT / 'oof_predictions.json', records)
        write_once(OUTPUT / 'summary.json', summary)
        print(json.dumps({'promotion_eligible': eligible, 'folds_beating_both_baselines': fold_wins,
                          'combined': combined, 'elapsed_seconds': summary['elapsed_seconds']}), flush=True)
    except Exception as error:
        write_once(OUTPUT / 'failure.json', {'error_type': type(error).__name__, 'error': str(error),
                                            'elapsed_seconds': time.perf_counter() - started,
                                            'protocol_sha256': v2.sha(protocol_path)})
        raise


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        run()
