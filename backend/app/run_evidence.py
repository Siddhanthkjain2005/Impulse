"""Compact saved-run evidence without recalculating or upgrading old results."""


def summarize_evidence(run):
    candidate = run['candidates'][0]
    nominal = candidate.get('compliance', {}).get('nominal_pass')
    cross = candidate.get('circuit_crosscheck')
    agreement = None
    if cross and nominal is not None:
        circuit_pass = cross.get('compliance', {}).get('nominal_pass')
        if circuit_pass is not None:
            agreement = {
                'both_nominal_pass': bool(nominal and circuit_pass),
                'required': bool(run.get('inputs', {}).get('require_model_agreement', False)),
            }
    verification = candidate.get('verification')
    if verification:
        verification = {
            'passed': verification['passed'], 'total': verification['total'],
            'all_checks_pass': verification['all_checks_pass'],
            'models_checked': verification['models_checked'],
            'unique_scenarios': verification.get('unique_scenarios'),
            'minimum_margin_fraction': verification.get('worst_case', {}).get('minimum_margin_fraction'),
        }
    calibration = candidate.get('calibration') or {}
    return {
        'primary_nominal_pass': nominal,
        'agreement': agreement,
        'verification': verification,
        'ml_support': candidate.get('ood', {}).get('state'),
        'lab_calibrated': calibration.get('source_type') == 'measured_lab',
        'calibration_source': calibration.get('source_type'),
    }
