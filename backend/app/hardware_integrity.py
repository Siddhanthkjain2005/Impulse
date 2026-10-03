"""Source confidence is not physical hardware verification."""

PARAMETERS = {
    'voltage_min_kv': 'Minimum requested voltage (kV)', 'voltage_max_kv': 'Maximum voltage (kV)',
    'min_stages': 'Minimum active stages', 'max_stages': 'Maximum stages',
    'stage_kv': 'Stage voltage (kV)', 'stage_c_uf': 'Stage capacitance (µF)',
    'energy_stage_kj': 'Energy per stage (kJ)', 'energy_total_kj': 'Total energy (kJ)',
    'front_values': 'Front stock values (Ω)', 'lightning_tail_values': 'Lightning tail values (Ω)',
    'switching_tail_values': 'Switching tail values (Ω)',
    'units_per_value_per_stage': 'Stock quantity per value per stage', 'base_c_pf': 'Basic capacitance (pF)',
    'charging_r_ohm': 'Charging resistance (Ω)', 'potential_r_ohm': 'Potential resistance (Ω)',
    'discharge_r_ohm': 'Discharge resistances (Ω)', 'sphere_diameter_cm': 'Sphere diameter (cm)',
    'pulses_per_min': 'Pulses per minute', 'pulse_rating': 'Resistor pulse rating',
    'allowed_mounting': 'Permitted mounting', 'allowed_topologies': 'Permitted physical connections',
}


def hardware_integrity(profile):
    rows = []
    workbook = profile['kind'] == 'synthetic_reference'
    for key, label in PARAMETERS.items():
        value = profile.get(key)
        status = 'UNKNOWN' if value is None or value == [] else 'SOURCE PROVIDED'
        source = profile['source'] if status != 'UNKNOWN' else None
        note = None
        if workbook and key in ('voltage_max_kv', 'energy_stage_kj', 'energy_total_kj'):
            status = 'DERIVED'
            note = 'Mathematical reference: stage count × voltage or 0.5 C V²; not verified physical ratings.'
        if workbook and key in ('voltage_min_kv', 'min_stages', 'base_c_pf'):
            status = 'ASSUMED'
            note = 'Application operating/default assumption for the synthetic reference profile.'
        if key == 'base_c_pf' and profile['id'] == 'cpri_problem_brief_profile':
            note = 'REVIEW REQUIRED: role of 545 pF is ambiguous; do not double-count divider/system capacitance.'
        rows.append({'parameter': key, 'label': label, 'value': value, 'status': status,
                     'source': source, 'profile_version': profile['version'], 'source_date': None,
                     'note': note})
    return {'profile_id': profile['id'], 'profile_name': profile['name'], 'parameters': rows,
            'inventory_override_required': profile['units_per_value_per_stage'] is None,
            'physical_hardware_verified': False, 'notes': profile['notes'],
            'conflict': {'status': 'CONFLICTING SOURCE',
                         'workbook': {'max_stages': 15, 'stage_c_uf': 3},
                         'problem_statement': {'max_stages': 12, 'stage_c_uf': .125},
                         'message': 'Profiles are intentionally separate. Combining them produces inconsistent energy and capacitance assumptions.'},
            'scope': 'Declared stock arithmetic and voltage/energy constraints can be checked. Source-provided values are not independent laboratory verification.'}
