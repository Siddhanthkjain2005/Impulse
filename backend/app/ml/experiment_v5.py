"""Preregistered bounded-envelope development experiment; no serving changes.

Only the original V2 fit IDs are parsed into numeric outcome arrays. Prior
feature exploration, historically chosen V2 settings, and repeated outer folds
make every score development evidence, including the nested comparisons.
"""
import csv
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from scipy.optimize import linprog
from sklearn.linear_model import QuantileRegressor, Ridge
from sklearn.model_selection import KFold
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from threadpoolctl import threadpool_limits

from . import experiment_v2 as v2
from .reference_knn import ROOT, FEATURES, OBSERVED, PHYSICS, RESIDUAL

OUTPUT = ROOT / 'artifacts/experiments/v5'
VERSION = 'bounded-envelope-v5-development'
BLENDS = [.5, 1.]
OUTER_SEED = 71
INNER_SEED = 73
METHODS = ['Ridge control', 'Minimax envelope', 'Quantile center']


def spec_grid():
    return [dict(name=method, relative=relative, degree=degree)
            for method in METHODS for relative in [False, True] for degree in [1, 2]]


def x_features(frame, target):
    """The previously exposed compact V3 basis; no new feature mining."""
    total = (frame.Load_C_pF + frame.Divider_C_pF + frame.Stray_C_pF).to_numpy(float)
    inductance = frame.L_uH.to_numpy(float)
    return [np.column_stack([total, inductance]), frame[['Load_C_pF']].to_numpy(float),
            np.column_stack([total, inductance, total * inductance])][target]


class EnvelopeRegressor:
    """All transforms and distributional fits learn from supplied training rows."""

    def __init__(self, method, degree):
        self.method = method
        self.degree = degree

    def fit(self, x, y):
        self.input_scaler_ = StandardScaler().fit(x)
        self.poly_ = PolynomialFeatures(self.degree, include_bias=False)
        z = self.poly_.fit_transform(self.input_scaler_.transform(x))
        self.expanded_scaler_ = StandardScaler().fit(z)
        z = self.expanded_scaler_.transform(z)
        self.target_scaler_ = StandardScaler().fit(np.asarray(y).reshape(-1, 1))
        target = self.target_scaler_.transform(np.asarray(y).reshape(-1, 1)).ravel()
        if self.method == 'Minimax envelope':
            # min t subject to -t <= intercept + X beta - y <= t.
            # The midrange estimate exploits a possible bounded-error shape;
            # it does not assume a known bound or establish uniform noise.
            design = np.column_stack([np.ones(len(z)), z])
            constraint = np.vstack([np.column_stack([design, -np.ones(len(z))]),
                                    np.column_stack([-design, -np.ones(len(z))])])
            objective = np.zeros(design.shape[1] + 1)
            objective[-1] = 1.
            result = linprog(objective, A_ub=constraint, b_ub=np.concatenate([target, -target]),
                             bounds=[(None, None)] * design.shape[1] + [(0., None)], method='highs')
            if not result.success:
                raise RuntimeError(f'Minimax fit failed: {result.message}')
            self.coef_ = result.x[:-1]
            self.radius_ = float(result.x[-1])
        elif self.method == 'Quantile center':
            self.quantiles_ = [QuantileRegressor(quantile=q, alpha=0., solver='highs').fit(z, target)
                               for q in [.1, .9]]
        elif self.method == 'Ridge control':
            self.ridge_ = Ridge(alpha=.01).fit(z, target)
        else:
            raise ValueError(self.method)
        return self

    def predict(self, x):
        z = self.expanded_scaler_.transform(self.poly_.transform(self.input_scaler_.transform(x)))
        if self.method == 'Minimax envelope':
            prediction = np.column_stack([np.ones(len(z)), z]) @ self.coef_
        elif self.method == 'Quantile center':
            prediction = np.mean([model.predict(z) for model in self.quantiles_], axis=0)
        else:
            prediction = self.ridge_.predict(z)
        return self.target_scaler_.inverse_transform(np.asarray(prediction).reshape(-1, 1)).ravel()


def fit(frame, target, spec):
    y = frame[RESIDUAL[target]].to_numpy(float)
    if spec['relative']:
        y = y / frame[PHYSICS[target]].to_numpy(float)
    return EnvelopeRegressor(spec['name'], spec['degree']).fit(x_features(frame, target), y)


def predict(model, frame, target, spec):
    prediction = model.predict(x_features(frame, target))
    return prediction * frame[PHYSICS[target]].to_numpy(float) if spec['relative'] else prediction


def load_fit_frames(split, path=None):
    """Reject calibration and non-Train rows before converting any outcomes."""
    path = path or ROOT / 'data/processed/synthetic_dataset.csv'
    allowed = {int(id_) for ids in split['fit_ids'].values() for id_ in ids}
    excluded = {int(id_) for ids in split['calibration_ids'].values() for id_ in ids}
    assert allowed.isdisjoint(excluded)
    with Path(path).open(newline='') as stream:
        rows = [row for row in csv.DictReader(stream)
                if row['Split'] == 'Train' and int(row['ID']) in allowed]
    frame = pd.DataFrame(rows)
    for column in set(FEATURES + PHYSICS + OBSERVED + RESIDUAL + ['ID', 'Stages', 'Charge_kV_Stage']):
        frame[column] = pd.to_numeric(frame[column], errors='raise')
    assert frame.ID.is_unique and set(frame.ID) == allowed
    indexed = frame.set_index('ID', drop=False)
    frames = {typ: indexed.loc[split['fit_ids'][typ]].reset_index(drop=True) for typ in v2.TYPES}
    for typ, selected in frames.items():
        assert set(selected.Impulse_Type) == {typ} and set(selected.Split) == {'Train'}
        assert np.isfinite(selected[FEATURES + PHYSICS + OBSERVED + RESIDUAL].to_numpy(float)).all()
    return frames


def choose(scores, baseline_score, allowed_methods):
    choice = {'name': 'Historical V2 refit', 'blend': 0.}
    best = baseline_score
    for record in scores:
        if (record['spec']['name'] in allowed_methods and record['normalized_mse'] < best
                and record['normalized_mse'] <= baseline_score * .98):
            choice = record['spec']
            best = record['normalized_mse']
    return choice, float(best)


def select(frame, target, baseline_spec, typ):
    folds = list(KFold(3, shuffle=True, random_state=INNER_SEED).split(frame))
    base = np.zeros(len(frame))
    truth = frame[RESIDUAL[target]].to_numpy(float)
    tol = v2.tolerances(frame, typ)[:, target]
    for a, b in folds:
        base[b] = v2.predict_spec(v2.fit_spec(frame.iloc[a], target, baseline_spec),
                                  frame.iloc[b], target, baseline_spec)
    baseline_score = float(np.mean(((base - truth) / tol) ** 2))
    scores = []
    for spec in spec_grid():
        predictions = np.zeros(len(frame))
        for a, b in folds:
            predictions[b] = predict(fit(frame.iloc[a], target, spec), frame.iloc[b], target, spec)
        for weight in BLENDS:
            score = float(np.mean(((weight * predictions + (1 - weight) * base - truth) / tol) ** 2))
            scores.append({'spec': {**spec, 'blend': weight}, 'normalized_mse': score})
    selected, selected_score = choose(scores, baseline_score, METHODS)
    control, control_score = choose(scores, baseline_score, ['Ridge control'])
    return selected, control, {'baseline_normalized_mse': baseline_score,
                              'chosen_normalized_mse': selected_score,
                              'control_normalized_mse': control_score,
                              'all_candidate_scores': scores,
                              'inner_folds': [{'train_ids': frame.iloc[a].ID.astype(int).tolist(),
                                               'held_ids': frame.iloc[b].ID.astype(int).tolist()}
                                              for a, b in folds]}


def fold_prediction(train, held, target, spec, baseline):
    if spec['blend'] == 0:
        return baseline.copy()
    return (spec['blend'] * predict(fit(train, target, spec), held, target, spec)
            + (1 - spec['blend']) * baseline)


def preserved_artifacts():
    paths = list((ROOT / 'artifacts/models').rglob('*'))
    paths += [p for p in (ROOT / 'artifacts/experiments').rglob('*')
              if ROOT / 'artifacts/experiments/v5' not in p.parents]
    return {str(p.relative_to(ROOT)): v2.sha(p) for p in sorted(paths) if p.is_file()}


def gate(baseline, candidate, physical_improvements):
    macro = float(100 * (1 - np.mean(candidate) / np.mean(baseline)))
    worst = float(np.min(physical_improvements))
    return macro, worst, bool(macro >= 5 and worst >= -2)


def run():
    if (OUTPUT / 'summary.json').exists() or (OUTPUT / 'oof_predictions.json').exists():
        print('Frozen V5 result exists; refusing post-result retuning.', flush=True)
        return
    split = json.loads((ROOT / 'artifacts/experiments/v2/protocol.json').read_text())
    # Read only the historical configuration field; no stored evaluation values
    # are consulted for choices. Calibration remains excluded from new data.
    previous = json.loads((ROOT / 'artifacts/experiments/v2/summary.json').read_text())['selection']
    preserved = preserved_artifacts()
    protocol = {
        'version': VERSION, 'registered_at': datetime.now(timezone.utc).isoformat(),
        'runner_sha256': v2.sha(Path(__file__)), 'helper_sha256': v2.sha(Path(v2.__file__)),
        'reference_helper_sha256': v2.sha(ROOT / 'backend/app/ml/reference_knn.py'),
        'dataset_sha256': v2.sha(ROOT / 'data/processed/synthetic_dataset.csv'),
        'fit_ids': split['fit_ids'], 'excluded_calibration_ids': split['calibration_ids'],
        'preserved_sha256': preserved, 'historical_v2_specs': previous,
        'grid': spec_grid(), 'blends': BLENDS, 'quantiles': [.1, .9], 'ridge_control_alpha': .01,
        'outer': {'folds': 5, 'seed': OUTER_SEED}, 'inner': {'folds': 3, 'seed': INNER_SEED},
        'hypothesis': 'Previously observed flat bounded residuals may make extremal or quantile-envelope trend estimates competitive with mean-loss estimates. Bounded/uniform noise is not assumed to be established.',
        'features': 'Previously explored V3 compact mechanisms: total C + L for front; load C for tail; total C + L + L*C for crest. Degrees 1 and 2, trained foldwise.',
        'selection': 'Per-output/per-regime minimum inner tolerance-normalized MSE, with >=2% lower MSE required to replace the same-row historical V2 refit. All 12 specs and both blend weights compete.',
        'control': 'Separate inner selection limited to the four matched Ridge configurations and V2 fallback, evaluated on every outer held row. Same features, transforms, blend grid, inner gate, and fit budget.',
        'pooling': 'None. Every fit uses only the target regime. No labels from either regime held-out rows enter any fit.',
        'promotion': 'At least 5% improvement in mean of six outer tolerance-normalized RMSE values and no physical-unit target RMSE regression >2%. Passing only merits independent evaluation; no serving change.',
        'scope': 'Nested Train CV development only. Previously exposed features, reused outer folds, and historically selected V2 configurations; not an unbiased or independent test.',
        'labels_used': 'Original 560 Train fit IDs per impulse type only. Calibration, Validation and Hidden Test outcomes excluded from fitting, scoring and tuning.',
        'stopping_rule': 'One registered grid. No expansion or retuning after outer outcomes. Do not create final production weights or calibration intervals.',
        'packages': {'python': platform.python_version(), 'numpy': np.__version__,
                     'scipy': scipy.__version__, 'sklearn': sklearn.__version__, 'pandas': pd.__version__},
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    protocol_path = OUTPUT / 'protocol.json'
    if protocol_path.exists():
        prior = json.loads(protocol_path.read_text())
        assert {k: v for k, v in prior.items() if k != 'registered_at'} == {
            k: v for k, v in protocol.items() if k != 'registered_at'}, 'Registered protocol mismatch'
    else:
        protocol_path.write_text(json.dumps(protocol, indent=2))
    # Registration precedes even parsing the permitted numeric outcomes.
    started = time.perf_counter()
    frames = load_fit_frames(split)
    assert all(len(frame) == 560 for frame in frames.values())
    records = []
    choices = {}
    for typ, frame in frames.items():
        choices[typ] = []
        for fold, (a, b) in enumerate(KFold(5, shuffle=True, random_state=OUTER_SEED).split(frame)):
            train, held = frame.iloc[a], frame.iloc[b]
            baseline = np.zeros((len(held), 3))
            candidate = np.zeros_like(baseline)
            control = np.zeros_like(baseline)
            fold_choices = []
            for target in range(3):
                spec = previous[typ][target]
                selected, control_spec, log = select(train, target, spec, typ)
                model = v2.fit_spec(train, target, spec)
                baseline[:, target] = v2.predict_spec(model, held, target, spec)
                candidate[:, target] = fold_prediction(train, held, target, selected, baseline[:, target])
                control[:, target] = fold_prediction(train, held, target, control_spec, baseline[:, target])
                fold_choices.append({'selection': selected, 'control_selection': control_spec, **log})
            choices[typ].append(fold_choices)
            physics = held[PHYSICS].to_numpy(float)
            for i, (_, row) in enumerate(held.iterrows()):
                records.append({'id': int(row.ID), 'type': typ, 'fold': fold,
                                'train_ids': train.ID.astype(int).tolist(),
                                'observed': row[OBSERVED].to_numpy(float).tolist(),
                                'v5_prediction': (physics[i] + candidate[i]).tolist(),
                                'ridge_control_prediction': (physics[i] + control[i]).tolist(),
                                'v2_refit_prediction': (physics[i] + baseline[i]).tolist()})
            print(f'{typ} envelope fold {fold + 1}/5 complete', flush=True)
    result = {'version': VERSION, 'scope': protocol['scope'], 'protocol_sha256': v2.sha(protocol_path),
              'nested_cv': {}, 'fold_choices': choices}
    for typ, frame in frames.items():
        by_id = {row['id']: row for row in records if row['type'] == typ}
        table = {name: v2.metric_report(frame, np.array([by_id[int(id_)][key] for id_ in frame.ID]), typ)
                 for name, key in [('V5 envelope search', 'v5_prediction'),
                                   ('Matched Ridge control search', 'ridge_control_prediction'),
                                   ('Historical V2 refit', 'v2_refit_prediction')]}
        gain = 100 * (1 - np.array(table['V5 envelope search']['rmse']) / table['Historical V2 refit']['rmse'])
        result['nested_cv'][typ] = {'metrics': table, 'improvement_vs_v2_pct': gain.tolist()}
    def normalized(name):
        return np.concatenate([result['nested_cv'][typ]['metrics'][name]['normalized_rmse_tolerance']
                               for typ in v2.TYPES])
    gains = np.concatenate([result['nested_cv'][typ]['improvement_vs_v2_pct'] for typ in v2.TYPES])
    baseline, candidate, control = [normalized(name) for name in [
        'Historical V2 refit', 'V5 envelope search', 'Matched Ridge control search']]
    macro, worst, eligible = gate(baseline, candidate, gains)
    result.update(macro_improvement_pct=macro, worst_target_improvement_pct=worst,
                  control_macro_improvement_pct=float(100 * (1 - control.mean() / baseline.mean())),
                  improvement_vs_matched_control_pct=float(100 * (1 - candidate.mean() / control.mean())),
                  promotion_eligible=eligible, hidden_test_evaluated=False,
                  validation_evaluated=False, calibration_evaluated=False, cloud_spend_usd=0,
                  elapsed_seconds=time.perf_counter() - started, final_models_created=False,
                  decision='Gate passed on development rows only; independent evaluation required. V1/V2 unchanged.'
                  if eligible else 'No promotion: the bounded-envelope search failed the fixed gate. V1/V2 unchanged.')
    assert preserved_artifacts() == preserved, 'Older experiment or model artifact changed'
    result['preserved_artifacts_verified'] = True
    (OUTPUT / 'oof_predictions.json').write_text(json.dumps(records, separators=(',', ':')))
    (OUTPUT / 'summary.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({key: result[key] for key in ['macro_improvement_pct',
          'control_macro_improvement_pct', 'improvement_vs_matched_control_pct',
          'worst_target_improvement_pct', 'promotion_eligible', 'elapsed_seconds']}), flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        run()
