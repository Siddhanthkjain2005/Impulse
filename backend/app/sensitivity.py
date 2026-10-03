"""One-parameter raw-physics comparisons, separate from saved recommendations."""
import hashlib
import json
import math
from copy import deepcopy

from .schemas import OptimizeRequest, GeneratorProfile, SimulationSettings
from .optimization.engine import physics
from .physics.compliance import check, RULES
from .physics.circuit import VERSION as CIRCUIT_VERSION
from .physics.waveform_metrics import waveform_from_metrics
from .setup_transition import rating_pass

PARAMETERS = {
    'front_r_stage': ('Front resistance / stage', 'Ω', 'settings'),
    'tail_r_stage': ('Tail resistance / stage', 'Ω', 'settings'),
    'load_c_pf': ('Test-object capacitance', 'pF', 'inputs'),
    'divider_c_pf': ('Divider capacitance', 'pF', 'inputs'),
    'stray_c_pf': ('Stray capacitance', 'pF', 'inputs'),
    'l_uh': ('Connection inductance', 'µH', 'inputs'),
}
METRICS = ['front_us', 'tail_us', 'crest_kv']
SETTING_KEYS = ['stages', 'charge_kv_stage', 'front_r_stage', 'tail_r_stage']


def solve(inputs, profile, settings, solver):
    request = OptimizeRequest.model_validate({**inputs, 'solver': solver, 'require_model_agreement': False})
    raw = physics(request, profile, settings['stages'], settings['charge_kv_stage'],
                  settings['front_r_stage'], settings['tail_r_stage'], True)
    metrics = {key: raw[key] for key in METRICS}
    if not all(math.isfinite(value) and value > 0 for value in metrics.values()):
        raise ValueError('The raw model did not return finite positive waveform metrics.')
    waveform = raw.get('waveform')
    plot_error = None
    if waveform is None:
        try:
            waveform = waveform_from_metrics(*[metrics[key] for key in METRICS], request.impulse_type)
        except ValueError as error:
            # A reconstruction failure does not erase valid formula metrics.
            plot_error = str(error)
    limits = check(request.impulse_type, request.test_kv, metrics)
    total_c = (request.load_c_pf + request.divider_c_pf + request.stray_c_pf
               + ((profile['base_c_pf'] or 0) if request.include_base_c else 0))
    return {'metrics': metrics, 'waveform': waveform, 'plot_error': plot_error,
            'effective_total_c_pf': total_c,
            'waveform_limits': {'nominal_pass': limits['nominal_pass'], 'rows': limits['rows'],
                                'scope': 'Raw-model waveform limits only; no stock, uncertainty or laboratory approval.'}}


def compare_sensitivity(run, candidate_id, request):
    selected = next((c for c in run['candidates'] if c['id'] == candidate_id), None)
    if selected is None:
        raise ValueError('The selected candidate does not belong to this saved run.')
    inputs = OptimizeRequest.model_validate(run['inputs']).model_dump()
    profile = GeneratorProfile.model_validate(run['profile']).model_dump()
    settings = SimulationSettings.model_validate({key: selected['settings'][key] for key in SETTING_KEYS}).model_dump()
    if inputs['profile_id'] != profile['id'] or not profile['enabled'] or not rating_pass(profile, selected):
        raise ValueError('The saved profile and settings must satisfy the declared generator ratings.')
    label, unit, location = PARAMETERS[request.parameter]
    before = settings if location == 'settings' else inputs
    value = before[request.parameter]
    changed_value = value * (1 + request.change_pct / 100)
    modified_inputs, modified_settings = deepcopy(inputs), deepcopy(settings)
    (modified_settings if location == 'settings' else modified_inputs)[request.parameter] = changed_value
    # Percentage changes must still respect the public simulation input limits.
    modified_inputs = OptimizeRequest.model_validate(modified_inputs).model_dump()
    modified_settings = SimulationSettings.model_validate(modified_settings).model_dump()
    models = []
    for solver, model_label, version in [('reference', 'Workbook equations', 'workbook-reference-v1'),
                                         ('circuit', 'Equivalent circuit', CIRCUIT_VERSION)]:
        result = {'id': solver, 'label': model_label, 'physics_version': version}
        try:
            baseline = solve(inputs, profile, settings, solver)
            variant = solve(modified_inputs, profile, modified_settings, solver)
            result.update(available=True, baseline=baseline, variant=variant,
                          changes=[{'metric': key, 'unit': 'kV' if key == 'crest_kv' else 'µs',
                                    'baseline': baseline['metrics'][key], 'variant': variant['metrics'][key],
                                    'delta': variant['metrics'][key] - baseline['metrics'][key],
                                    'delta_pct': 100 * (variant['metrics'][key] / baseline['metrics'][key] - 1)}
                                   for key in METRICS])
        except (ValueError, ArithmeticError) as error:
            result.update(available=False, error=str(error))
        models.append(result)
    resistor_changed = location == 'settings' and changed_value != value
    return {'version': 'one-parameter-raw-physics-v1', 'source_type': 'generated_stress_test',
            'run_id': run['id'], 'candidate_id': selected['id'], 'original_rank': selected['rank'],
            'run_sha256': hashlib.sha256(json.dumps(run, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'saved_model_version': run['model_version'], 'saved_uncertainty_status': selected['compliance']['status'],
            'rules_version_used': RULES['version'], 'saved_rules_version': run['rules']['version'],
            'profile': profile, 'baseline_inputs': inputs, 'baseline_settings': settings,
            'variant_inputs': modified_inputs, 'variant_settings': modified_settings,
            'parameter': {'key': request.parameter, 'label': label, 'unit': unit, 'location': location,
                          'baseline_value': value, 'variant_value': changed_value,
                          'requested_change_pct': request.change_pct, 'value_changed': changed_value != value},
            'models': models, 'resistor_plan_requires_new_search': resistor_changed,
            'saved_correction_applied': False, 'optimizer_ranking_changed': False,
            'saved_recommendation_changed': False,
            'scope': 'Educational one-parameter comparison at fixed active-stage count, charging voltage and efficiency. '
                     'Both raw physics models are recomputed using the captured profile and current versioned equations. '
                     'ML residuals, trial corrections and uncertainty envelopes are not applied. '
                     'Reference curves reconstruct metrics; circuit curves come from the lumped circuit. '
                     'Resistor changes are hypothetical equivalents with no verified stock construction. '
                     'Other inputs remain fixed; interactions and continuous-range guarantees are not evaluated. '
                     'Saved ranking and evidence are unchanged. This is not measured accuracy, an operating instruction '
                     'or a universal monotonic law.'}
