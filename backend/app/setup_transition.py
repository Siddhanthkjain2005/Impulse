"""Compare saved active-stage plans without running or changing the optimizer."""
from copy import deepcopy
import hashlib
import json
import math


def candidate(run, identifier):
    selected = next((c for c in run['candidates'] if c['id'] == identifier), None)
    if selected is None:
        raise ValueError('The baseline candidate does not belong to its saved run.')
    return selected


def counts(network):
    if not network.get('topology') or not math.isfinite(network['equivalent_ohm']) or network['equivalent_ohm'] <= 0:
        raise ValueError('A saved connection plan is required.')
    result = {}
    for part in network['components']:
        ohm, quantity = float(part['ohm']), part['count_per_stage']
        if not math.isfinite(ohm) or ohm <= 0 or type(quantity) is not int or quantity <= 0:
            raise ValueError('The saved component counts are invalid.')
        if ohm in result:
            raise ValueError('The saved component list contains duplicate values.')
        result[ohm] = quantity
    if not result or type(network['count_per_stage']) is not int or sum(result.values()) != network['count_per_stage']:
        raise ValueError('The saved network total does not match its components.')
    return result


def validate_plan(c):
    n = c['settings']['stages']
    if type(n) is not int or n <= 0:
        raise ValueError('The saved active-stage count must be a positive integer.')
    for name in ['front', 'tail']:
        network = c[f'{name}_network']; counts(network)
        if (network.get('total_components') != network['count_per_stage'] * n
                or any(p.get('total_required') != p['count_per_stage'] * n for p in network['components'])
                or not math.isclose(network['equivalent_ohm'], c['settings'][f'{name}_r_stage'], rel_tol=1e-9, abs_tol=1e-8)):
            raise ValueError('Saved per-stage totals or resistance do not match the candidate settings.')


def rating_pass(profile, c):
    s = c['settings']; n, q = s['stages'], s['charge_kv_stage']
    if type(n) is not int or not math.isfinite(q) or q <= 0:
        return False
    energy = .5 * profile['stage_c_uf'] * 1e-6 * (q * 1000) ** 2 / 1000
    return (profile['min_stages'] <= n <= profile['max_stages']
            and q <= profile['stage_kv'] + 1e-9
            and energy <= profile['energy_stage_kj'] + 1e-9
            and n * energy <= profile['energy_total_kj'] + 1e-9)


def network_delta(old, new, old_stages, new_stages):
    before, after = counts(old), counts(new)
    shared = min(old_stages, new_stages)
    values = []
    for ohm in sorted(set(before) | set(after)):
        a, b = before.get(ohm, 0), after.get(ohm, 0)
        values.append({'ohm': ohm, 'baseline_per_stage': a, 'target_per_stage': b,
                       'retained_on_shared_stages': min(a, b) * shared,
                       'added_on_shared_stages': max(b - a, 0) * shared,
                       'removed_from_shared_stages': max(a - b, 0) * shared,
                       'required_on_newly_active_stages': b * max(new_stages - old_stages, 0),
                       'present_on_deactivated_stages': a * max(old_stages - new_stages, 0)})
    # Text is compared conservatively: identical parts and equivalent resistance
    # do not establish identical wiring. No circuit-isomorphism claim is made.
    changed = before != after or old['topology'] != new['topology'] or not math.isclose(
        old['equivalent_ohm'], new['equivalent_ohm'], rel_tol=1e-10, abs_tol=1e-9)
    return {'baseline_topology': old['topology'], 'target_topology': new['topology'],
            'baseline_equivalent_ohm': old['equivalent_ohm'], 'target_equivalent_ohm': new['equivalent_ohm'],
            'connection_plan_changed': changed, 'shared_stage_banks_to_review': shared if changed else 0,
            'parts': values, **{key: sum(p[key] for p in values) for key in [
                'retained_on_shared_stages', 'added_on_shared_stages', 'removed_from_shared_stages',
                'required_on_newly_active_stages', 'present_on_deactivated_stages']}}


def eligibility(run, c):
    reasons = []
    if c.get('compliance', {}).get('nominal_pass') is not True:
        reasons.append('Primary nominal limits do not pass or are not recorded.')
    if c.get('compliance', {}).get('hardware_pass') is not True:
        reasons.append('Saved hardware compliance does not pass or is not recorded.')
    if not rating_pass(run['profile'], c):
        reasons.append('Declared stage voltage or stored-energy limits do not pass.')
    models = ['Primary prediction'] if run['inputs']['solver'] == 'reference' else ['Circuit prediction']
    if run['inputs']['solver'] == 'reference':
        models.append('Independent circuit')
        if (c.get('circuit_crosscheck') or {}).get('compliance', {}).get('nominal_pass') is not True:
            reasons.append('Independent circuit nominal limits do not pass or are not recorded.')
    for name in ['front', 'tail']:
        network = c[f'{name}_network']
        counts(network)
        if network.get('inventory_feasible') is not True or any(
                type(p.get('available_per_stage')) is not int
                or p['count_per_stage'] > p['available_per_stage'] for p in network['components']):
            reasons.append(f'{name.title()} stock feasibility is missing or exceeds declared quantities.')
    return {'eligible_nominal': not reasons, 'reasons': reasons, 'models_checked': models,
            'scope': 'Nominal model, declared stock and rating checks only; no laboratory approval.'}


def plan_transition(baseline_run, baseline_candidate_id, target_run):
    if baseline_run['profile'] != target_run['profile']:
        raise ValueError('Compare plans for the same generator profile and version; different machine assumptions cannot be combined.')
    if baseline_run['inputs']['layout_id'] != target_run['inputs']['layout_id']:
        raise ValueError('Compare the same layout; this planner cannot infer physical changes between layouts.')
    old = candidate(baseline_run, baseline_candidate_id)
    validate_plan(old)
    if not rating_pass(baseline_run['profile'], old):
        raise ValueError('The baseline does not satisfy the declared generator ratings.')
    for name in ['front', 'tail']:
        counts(old[f'{name}_network'])
    before = old['settings']; options = []
    for c in target_run['candidates']:
        validate_plan(c)
        after = c['settings']
        deltas = {name: network_delta(old[f'{name}_network'], c[f'{name}_network'], before['stages'], after['stages'])
                  for name in ['front', 'tail']}
        check = eligibility(target_run, c)
        changed_families = sum(delta['connection_plan_changed'] for delta in deltas.values())
        common_parts = sum(delta['added_on_shared_stages'] + delta['removed_from_shared_stages'] for delta in deltas.values())
        charge_delta = after['charge_kv_stage'] - before['charge_kv_stage']
        options.append({'candidate_id': c['id'], 'original_rank': c['rank'], 'settings': deepcopy(after),
                        'nominal_review': check, 'uncertainty_status': c['compliance']['status'],
                        'verification': deepcopy(c.get('verification')), 'networks': deltas,
                        'changed_network_families': changed_families,
                        'active_stages_added': max(after['stages'] - before['stages'], 0),
                        'active_stages_deactivated': max(before['stages'] - after['stages'], 0),
                        'shared_stage_part_changes': common_parts,
                        'charge_delta_kv_stage': charge_delta,
                        'charge_delta_pct': 100 * charge_delta / before['charge_kv_stage']})
    eligible = [option for option in options if option['nominal_review']['eligible_nominal']]
    key = lambda o: (o['changed_network_families'], o['active_stages_added'] + o['active_stages_deactivated'],
                     o['shared_stage_part_changes'], abs(o['charge_delta_kv_stage']), o['original_rank'])
    closest = min(eligible, key=key) if eligible else None
    if closest is None:
        review = 'No returned option passes every recorded nominal model, stock and rating check.'
    elif not closest['verification'] or not closest['verification'].get('all_checks_pass'):
        review = 'The closest nominal option needs review: its post-ranking challenge fails or was not recorded.'
    else:
        review = 'The closest nominal option also passes its saved finite challenge. Uncertainty and laboratory verification still apply.'
    digest = lambda run: hashlib.sha256(json.dumps(run, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'version': 'saved-setup-transition-v1',
            'baseline': {'run_id': baseline_run['id'], 'candidate_id': old['id'], 'settings': deepcopy(before),
                         'profile_name': baseline_run['profile']['name'], 'layout_id': baseline_run['inputs']['layout_id'],
                         'run_sha256': digest(baseline_run)},
            'target': {'run_id': target_run['id'], 'impulse_type': target_run['inputs']['impulse_type'],
                       'test_kv': target_run['inputs']['test_kv'], 'run_sha256': digest(target_run),
                       'model_version': target_run['model_version'], 'inventory_provenance': target_run['inventory_provenance']},
            'options': options, 'closest_nominal_candidate_id': closest['candidate_id'] if closest else None,
            'eligible_count': len(eligible), 'review': review,
            'priority': ['Changed front/tail network families', 'Active stage-count change',
                         'Shared-stage component additions/removals', 'Absolute charge change', 'Original rank'],
            'optimizer_ranking_changed': False, 'postranking_checks_used_for_selection': False,
            'scope': 'Saved-plan comparison only; the baseline is not authenticated as installed hardware. Uniform networks and corresponding shared stages are assumed. Counts on newly active or deactivated stages describe active plans, not physical installation/removal instructions. Different connection text is conservatively treated as changed wiring. Selection uses nominal checks and the declared change priority; post-ranking challenge and uncertainty remain separate review evidence. No measured climbs, time, shots saved, global minimum or laboratory readiness is claimed.'}
