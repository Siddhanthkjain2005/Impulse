"""Small deterministic engineering diagnostic; not a measured-accuracy benchmark."""
from datetime import datetime, timezone
from pathlib import Path
import json
import time

from backend.app.optimization.engine import optimize
from backend.app.schemas import OptimizeRequest

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'workbook_lightning': {},
    'higher_load_lightning': {'load_c_pf': 1500},
    'low_voltage_lightning': {'test_kv': 500},
    'constructible_switching': {'impulse_type': 'Switching', 'test_kv': 1025,
        'load_c_pf': 1240, 'divider_c_pf': 740, 'stray_c_pf': 320},
    'pdf_lightning_assumed_stock': {'profile_id': 'cpri_problem_brief_profile',
        'inventory_override': {'front': [{'ohm': r, 'count_per_stage': 4} for r in [30, 465, 3700]],
            'tail': [{'ohm': 520, 'count_per_stage': 4}],
            'provenance': 'Diagnostic assumption: four per value per stage; unverified laboratory stock'}},
}


def run():
    record = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Five declared engineering cases, including the development Lightning case. '
                 'Two unvalidated simulations, not independent accuracy or laboratory validation.',
        'cases': {}}
    for name, inputs in CASES.items():
        pair = {}
        for agreement in [False, True]:
            started = time.perf_counter()
            result = optimize(OptimizeRequest(**inputs, require_model_agreement=agreement))
            c = result['candidates'][0]
            pair['agreement' if agreement else 'original'] = {
                'settings': c['settings'], 'reference': c['hybrid'],
                'circuit': {k: c['circuit_crosscheck'][k] for k in ['front_us', 'tail_us', 'crest_kv']},
                'both_nominal_pass': c['compliance']['nominal_pass'] and c['circuit_crosscheck']['compliance']['nominal_pass'],
                'envelope_status': c['compliance']['status'], 'agreement': c.get('model_agreement'),
                'ml_trust': c['ood']['trust_weight'], 'search': result['search'],
                'seconds': time.perf_counter() - started,
            }
        record['cases'][name] = {'inputs': inputs, **pair}
        print(name, {k: pair[k]['both_nominal_pass'] for k in pair}, flush=True)
    path = ROOT / 'artifacts/qa/model_agreement_diagnostic.json'
    path.write_text(json.dumps(record, indent=2))


if __name__ == '__main__':
    run()
