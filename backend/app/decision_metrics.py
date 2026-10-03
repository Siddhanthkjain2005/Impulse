"""Descriptive waveform-decision errors against captured challenge limits.

These counts describe selected measured captures. They do not certify hardware,
estimate instrument uncertainty, or imply a population success probability.
"""
from copy import deepcopy
import hashlib
import json

import numpy as np


KEYS = ('front_us', 'tail_us', 'crest_kv')
BOUNDARY_EPSILON = 1e-10  # Match the existing nominal compliance roundoff tolerance.


def captured_limits(run):
    """Use the run's saved rules, never today's mutable global configuration."""
    try:
        rules = run['rules']
        typ = run['inputs']['impulse_type']
        rule = rules[typ]
        crest = float(run['inputs']['test_kv'])
        fraction = float(rules['crest_tolerance_fraction'])
        targets = np.array([rule['front_target_us'], rule['tail_target_us'], crest], float)
        bounds = np.array([[rule['front_min_us'], rule['front_max_us']],
                           [rule['tail_min_us'], rule['tail_max_us']],
                           [crest * (1 - fraction), crest * (1 + fraction)]], float)
        if (typ not in ('Lightning', 'Switching') or not 0 < fraction < 1
                or not np.isfinite(targets).all() or not np.isfinite(bounds).all()
                or (bounds <= 0).any() or (bounds[:, 1] <= bounds[:, 0]).any()
                or (targets < bounds[:, 0]).any() or (targets > bounds[:, 1]).any()
                or not rules['id'] or not rules['version']):
            raise ValueError('Invalid saved challenge bounds.')
        digest = hashlib.sha256(json.dumps(rules, sort_keys=True, separators=(',', ':'),
                                          allow_nan=False).encode()).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('The saved run must include valid versioned challenge rules for accuracy review.') from error
    return {'id': rules['id'], 'version': rules['version'], 'sha256': digest,
            'source': rules.get('source'), 'definition': rule.get('definition'),
            'bounds': bounds.tolist(), 'targets': targets.tolist(),
            'normalization_halfwidth': ((bounds[:, 1] - bounds[:, 0]) / 2).tolist(),
            'snapshot': deepcopy(rules), 'boundary_epsilon': BOUNDARY_EPSILON}


def nominal_decision(values, limits):
    values = np.asarray(values, dtype=float)
    bounds = np.asarray(limits['bounds'], dtype=float)
    if values.shape != (3,) or not np.isfinite(values).all():
        raise ValueError('A waveform decision needs three finite metric values.')
    passed = (values >= bounds[:, 0] - BOUNDARY_EPSILON) & (values <= bounds[:, 1] + BOUNDARY_EPSILON)
    margins = np.minimum(values - bounds[:, 0], bounds[:, 1] - values) / np.asarray(limits['normalization_halfwidth'])
    return {'nominal_pass': bool(passed.all()), 'per_metric_pass': dict(zip(KEYS, passed.tolist())),
            'minimum_limit_margin': float(margins.min()), 'scope': 'Nominal waveform values only'}


def extracted_compliance(values, limits, quality):
    """Preserve nominal arithmetic while making unresolved captures provisional."""
    decision = nominal_decision(values, limits)
    rows = []
    for i, key in enumerate(KEYS):
        passed = decision['per_metric_pass'][key]
        target = limits['targets'][i]
        rows.append({'name': ['Front / peak time', 'Time to half-value', 'Crest voltage'][i],
                     'target': target, 'predicted': float(values[i]),
                     'lower': limits['bounds'][i][0], 'upper': limits['bounds'][i][1],
                     'pass': passed, 'robust': False, 'unit': 'kV' if i == 2 else 'µs',
                     'deviation': float(values[i] - target),
                     'deviation_pct': float(100 * (values[i] / target - 1)),
                     'reason': 'Inside challenge limits' if passed else 'Outside challenge limits'})
    reviewed = quality['evaluation_allowed']
    return {'profile_id': limits['id'], 'version': limits['version'], 'source': limits['source'],
            'rules_sha256': limits['sha256'], 'definition': limits['definition'], 'rows': rows,
            'nominal_pass': decision['nominal_pass'], 'robust_pass': False, 'hardware_pass': None,
            'status': 'REVIEW REQUIRED' if not reviewed else 'NOMINAL PASS' if decision['nominal_pass'] else 'FAIL',
            'measurement_evidence_eligible': reviewed, 'provisional': not reviewed,
            'scope': 'Extracted nominal waveform values against the saved run rules. Capture review is required before use as measurement evidence; no instrument uncertainty or hardware approval.'}


def saved_envelope_decision(uncertainty, prediction, limits):
    if not uncertainty:
        return {'state': 'unavailable', 'reason': 'No interval was saved with this prediction.'}
    try:
        lower = np.asarray(uncertainty['lower'], dtype=float)
        upper = np.asarray(uncertainty['upper'], dtype=float)
        center = np.asarray(prediction, dtype=float)
        if (lower.shape != (3,) or upper.shape != (3,)
                or not np.isfinite(lower).all() or not np.isfinite(upper).all()
                or (lower > upper).any() or (center < lower - BOUNDARY_EPSILON).any()
                or (center > upper + BOUNDARY_EPSILON).any()):
            raise ValueError('Invalid interval or prediction outside its saved interval.')
    except (KeyError, TypeError, ValueError):
        return {'state': 'unavailable', 'reason': 'Saved interval is incomplete or inconsistent with its prediction.'}
    bounds = np.asarray(limits['bounds'], dtype=float)
    contained = bool(((lower >= bounds[:, 0]) & (upper <= bounds[:, 1])).all())
    outside = bool(((upper < bounds[:, 0]) | (lower > bounds[:, 1])).any())
    return {'state': 'contained' if contained else 'outside' if outside else 'overlaps',
            'lower': lower.tolist(), 'upper': upper.tolist(),
            'recorded_coverage_claim': uncertainty.get('coverage_claim'),
            'recorded_method': uncertainty.get('method'),
            'scope': 'Saved envelope geometry only; no new calibrated coverage or hardware approval.'}


def rate(numerator, denominator):
    return {'numerator': int(numerator), 'denominator': int(denominator),
            'pct': float(100 * numerator / denominator) if denominator else None}


def confusion(measured_pass, predicted_pass):
    measured = np.asarray(measured_pass, dtype=bool)
    predicted = np.asarray(predicted_pass, dtype=bool)
    if measured.ndim != 1 or measured.shape != predicted.shape or not len(measured):
        raise ValueError('Decision counts require paired nonempty observations.')
    tp = int(np.sum(measured & predicted)); fp = int(np.sum(~measured & predicted))
    fn = int(np.sum(measured & ~predicted)); tn = int(np.sum(~measured & ~predicted))
    return {'true_pass': tp, 'false_pass': fp, 'false_fail': fn, 'true_fail': tn,
            'measured_pass_count': tp + fn, 'measured_fail_count': fp + tn,
            'predicted_pass_count': tp + fp, 'predicted_fail_count': fn + tn,
            'both_measured_outcomes_present': bool(measured.any() and (~measured).any()),
            'correct_decisions': rate(tp + tn, len(measured)),
            'false_pass_among_measured_failures': rate(fp, fp + tn),
            'measured_fail_among_predicted_passes': rate(fp, tp + fp),
            'false_fail_among_measured_passes': rate(fn, tp + fn),
            'scope': 'Selected-capture nominal decisions; rates are descriptive, not generalization estimates.'}


def summarize_decisions(rows):
    measured_pass = [r['measured_decision']['nominal_pass'] for r in rows]
    models = {}
    for name in rows[0]['prediction_decisions']:
        models[name] = confusion(measured_pass, [r['prediction_decisions'][name]['nominal_pass'] for r in rows])
        models[name]['false_pass_trial_ids'] = [r['trial_id'] for r in rows
            if not r['measured_decision']['nominal_pass'] and r['prediction_decisions'][name]['nominal_pass']]
        models[name]['false_fail_trial_ids'] = [r['trial_id'] for r in rows
            if r['measured_decision']['nominal_pass'] and not r['prediction_decisions'][name]['nominal_pass']]
    contained = [r for r in rows if r['saved_envelope_decision']['state'] == 'contained']
    return {'models': models,
            'saved_envelope': {'state_counts': {state: sum(r['saved_envelope_decision']['state'] == state for r in rows)
                                               for state in ['contained', 'overlaps', 'outside', 'unavailable']},
                'measured_fail_among_contained_envelopes': rate(sum(not r['measured_decision']['nominal_pass'] for r in contained), len(contained)),
                'scope': 'Containment of saved prediction envelopes is separate from nominal decision accuracy.'}}
