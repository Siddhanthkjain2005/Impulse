"""Post-ranking parasitic challenge of fixed settings, separate from search samples."""
from itertools import product
import numpy as np
from scipy.stats import qmc

from ..ml.registry import infer
from ..physics.circuit import simulate
from ..physics.compliance import check

KEYS = ['load_c_pf', 'divider_c_pf', 'stray_c_pf', 'l_uh']
SEED = 617
SAMPLES = 128


def verify_settings(req, profile, candidate, mode, calibration=None):
    # Import at call time to keep the engine/verification dependency one-way.
    from .engine import physics, ml_row, calibration_matches

    s = candidate['settings']
    lhs = qmc.LatinHypercube(d=4, seed=SEED).random(SAMPLES)
    factors = np.vstack([2 * lhs - 1, np.array(list(product([-1., 1.], repeat=4)))])
    variations = [req.model_copy(update={k: getattr(req, k) * (1 + req.uncertainty_pct / 100 * u)
                   for k, u in zip(KEYS, point)}) for point in factors]
    physical = [physics(r, profile, s['stages'], s['charge_kv_stage'], s['front_r_stage'], s['tail_r_stage'])
                for r in variations]
    inferred = infer([ml_row(r, s, ph) for r, ph in zip(variations, physical)], profile['id'], mode)
    checks = []
    calibration_count = 0
    for index, (r, ph, prediction) in enumerate(zip(variations, physical, inferred)):
        bias = np.zeros(3)
        if candidate.get('calibration') and calibration and calibration_matches(calibration, r, candidate):
            bias = np.array(calibration['bias'])
            calibration_count += 1
        final = dict(zip(['front_us', 'tail_us', 'crest_kv'], np.array(prediction['prediction']) + bias))
        primary = check(req.impulse_type, req.test_kv, final)
        cross = None
        if req.solver == 'reference':
            total = r.load_c_pf + r.divider_c_pf + r.stray_c_pf
            total += (profile['base_c_pf'] or 0) if r.include_base_c else 0
            cp = simulate(s['stages'], s['charge_kv_stage'], s['front_r_stage'], s['tail_r_stage'],
                          profile['stage_c_uf'], total, r.l_uh, r.efficiency, r.impulse_type, False)
            cross = check(req.impulse_type, req.test_kv, cp)
        rows = [(r, 'Primary prediction') for r in primary['rows']]
        if cross: rows += [(r, 'Independent circuit') for r in cross['rows']]
        margins = [(1 - abs(row['predicted'] - row['target']) / ((row['upper'] - row['lower']) / 2), row, model)
                   for row, model in rows]
        margin, limiting, model = min(margins, key=lambda item: item[0])
        checks.append({'index': index + 1, 'group': 'fresh_samples' if index < SAMPLES else 'boundary_corners',
            'inputs': {k: getattr(r, k) for k in KEYS},
            'primary_pass': primary['nominal_pass'],
            'circuit_pass': cross['nominal_pass'] if cross else None,
            'all_models_pass': primary['nominal_pass'] and (cross['nominal_pass'] if cross else True),
            'minimum_margin_fraction': float(margin), 'limiting_model': model,
            'limiting_metric': limiting['name'], 'predicted': limiting['predicted'],
            'allowed_lower': limiting['lower'], 'allowed_upper': limiting['upper'], 'unit': limiting['unit']})

    def summarize(rows):
        return {'total': len(rows), 'passed': sum(r['all_models_pass'] for r in rows),
                'primary_passed': sum(r['primary_pass'] for r in rows),
                'circuit_passed': sum(bool(r['circuit_pass']) for r in rows) if req.solver == 'reference' else None}

    worst = min(checks, key=lambda row: row['minimum_margin_fraction'])
    nominal_pass = candidate['compliance']['nominal_pass'] and (
        candidate['circuit_crosscheck']['compliance']['nominal_pass'] if req.solver == 'reference' else True)
    return {'version': 'fixed-settings-verification-v1', 'seed': SEED, 'used_for_ranking': False,
        'models_checked': ['Primary prediction', 'Independent circuit'] if req.solver == 'reference' else ['Circuit prediction'],
        'parameters': KEYS, 'uncertainty_pct': req.uncertainty_pct,
        'fresh_samples': summarize(checks[:SAMPLES]), 'boundary_corners': summarize(checks[SAMPLES:]),
        'total': len(checks), 'passed': sum(r['all_models_pass'] for r in checks),
        'unique_scenarios': len({tuple(row['inputs'].values()) for row in checks}),
        'nominal_all_models_pass': nominal_pass,
        'all_checks_pass': nominal_pass and all(r['all_models_pass'] for r in checks),
        'worst_case': worst, 'calibrated_scenarios': calibration_count,
        'scope': 'Fixed hardware checked after ranking using 128 separate-seed Latin-hypercube scenarios and 16 boundary corners. '
                 'These checks do not select or reorder candidates. Finite simulation evidence only: '
                 'not continuous-bound certification, independent model-accuracy testing or a laboratory success probability. '
                 'Efficiency and hardware tolerances are held fixed; no statistical coverage claim.'}
