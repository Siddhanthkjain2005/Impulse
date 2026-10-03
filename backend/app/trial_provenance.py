"""Read our optional CSV provenance comments without changing source samples."""
import re


SOURCES = {'synthetic_benchmark': 'synthetic_benchmark', 'generated_demo': 'generated_demo',
           'generated_stress_test': 'generated_demo', 'measured_lab': 'measured_lab'}


def classified_source(record):
    declared = SOURCES.get(record.get('source_type'), 'unknown')
    embedded = record.get('provenance', {}).get('embedded_metadata', {}).get('source_type')
    if embedded is not None and SOURCES.get(embedded, 'unknown') != 'measured_lab':
        return SOURCES.get(embedded, 'unknown')
    return declared


def validate_csv_provenance(text, run_id, candidate_id, time_unit, voltage_unit):
    metadata = {}
    keys = {'source_type', 'run_id', 'candidate_id', 'time_unit', 'voltage_unit'}
    for line in text.splitlines():
        if not line.strip():
            continue
        if not line.lstrip().startswith('#'):
            break
        for key, value in re.findall(r'(\w+)\s*=\s*([^;\s]+)', line):
            if key not in keys:
                continue
            if key in metadata and metadata[key] != value:
                raise ValueError(f'CSV contains conflicting {key} provenance. Use the original export.')
            metadata[key] = value
    expected = {'run_id': run_id, 'candidate_id': candidate_id,
                'time_unit': time_unit.replace('µs', 'us'), 'voltage_unit': voltage_unit}
    for key, value in expected.items():
        recorded = metadata.get(key)
        if key == 'time_unit' and recorded == 'µs':
            recorded = 'us'
        if recorded is not None and recorded != value:
            raise ValueError(f'CSV {key} is {metadata[key]}, but the selected value is {value}. '
                             'Select the matching saved setup and units before uploading.')
    return {'embedded_metadata': metadata,
            'setup_identity': 'matched_export' if metadata.get('run_id') and metadata.get('candidate_id')
                              else 'operator_selected',
            'scope': 'Export identifiers and units are checked when present. Untagged files rely on the selected setup; metadata is not independently authenticated.'}
