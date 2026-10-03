"""Generate clearly labeled offline fallback reports without touching live histories."""
from pathlib import Path
import json
import os
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
os.environ['IMPULSETWIN_DB'] = str(Path(tempfile.mkdtemp(prefix='impulsetwin-demo-')) / 'demo.sqlite3')
os.environ.setdefault('LOKY_MAX_CPU_COUNT', '4')
os.environ.setdefault('OMP_NUM_THREADS', '1')

from fastapi.testclient import TestClient
from backend.app.main import app


def prepare_transition(samples, reports):
    """Compare archived outputs; never refit or regenerate their predictions."""
    from backend.app.setup_transition import plan_transition
    from backend.app.transition_report import transition_report
    before = json.loads((samples / 'lightning_reference_run.json').read_text())
    after = json.loads((samples / 'lightning_model_agreement_run.json').read_text())
    plan = plan_transition(before, before['candidates'][0]['id'], after)
    plan.update(id='demo-setup-transition-v1', created_at=datetime.now(timezone.utc).isoformat(),
                demo_only=True, source_type='generated_stress_test')
    (samples / 'setup_transition_plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    notice = '<aside class="callout"><strong>Generated demonstration only.</strong> This compares archived synthetic model outputs. The baseline is not verified installed hardware; these are not laboratory measurements.</aside>'
    (reports / 'demo_setup_transition.html').write_text(transition_report(plan).replace('<main>', '<main>' + notice))
    closest = next((o for o in plan['options'] if o['candidate_id'] == plan['closest_nominal_candidate_id']), None)
    return {'source_type': 'generated_stress_test', 'demo_only': True,
            'baseline_run_id': before['id'], 'target_run_id': after['id'],
            'closest_nominal_original_rank': closest['original_rank'] if closest else None,
            'shared_stage_part_changes': closest['shared_stage_part_changes'] if closest else None,
            'optimizer_ranking_changed': False, 'laboratory_evidence': False}


def prepare():
    client = TestClient(app)
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    samples = ROOT / 'data/demo'
    samples.mkdir(exist_ok=True)
    cases = {
        'lightning_reference': {},
        'lightning_model_agreement': {'require_model_agreement': True},
        'lightning_circuit': {'solver': 'circuit'},
        'switching_constructible_ood': {'impulse_type': 'Switching', 'test_kv': 1025,
            'load_c_pf': 1240, 'divider_c_pf': 740, 'stray_c_pf': 320},
    }
    experiment=ROOT/'artifacts/experiments/v2/summary.json'
    if experiment.exists() and json.loads(experiment.read_text())['promotion']['eligible']:
        cases['lightning_v2_candidate']={'model_mode':'experimental_v2'}
    evidence = {}
    for name, inputs in cases.items():
        response = client.post('/api/optimize', json=inputs)
        response.raise_for_status()
        run = response.json()
        report = client.get(f"/api/runs/{run['id']}/report")
        report.raise_for_status()
        (reports / f'demo_{name}.html').write_text(report.text)
        (samples / f'{name}_run.json').write_text(json.dumps(run, indent=2))
        wave = client.get(f"/api/runs/{run['id']}/demo-waveform")
        wave.raise_for_status()
        # Archive identities are provenance, not a claim that these isolated IDs
        # exist in a live app. A live export remains bound to its selected setup.
        archive_wave=wave.content.replace(b'; run_id=',b'; archived_run_id=').replace(b'; candidate_id=',b'; archived_candidate_id=')
        (samples / f'{name}_generated_trial.csv').write_bytes(archive_wave.replace(b'\r\n',b'\n'))
        c = run['candidates'][0]
        evidence[name] = {'source_type': 'generated_stress_test', 'run_id': run['id'],
            'model_version': run['model_version'], 'settings': c['settings'],
            'nominal_pass': c['compliance']['nominal_pass'], 'status': c['compliance']['status'],
            'ml_trust': c['ood']['trust_weight'],
            'model_agreement': c.get('model_agreement'),
            'circuit_crosscheck': c['circuit_crosscheck']['compliance']['status'] if c['circuit_crosscheck'] else None}
    evidence['setup_transition'] = prepare_transition(samples, reports)
    (samples / 'README.md').write_text(
        '# Offline demonstration samples\n\n'
        'Every CSV here is generated, not a measured laboratory shot. The saved JSON and HTML '
        'reports are reproducible model outputs for rehearsal and fallback. They do not claim '
        'laboratory validation. To upload a CSV, first create a matching live run in the app; '
        'the archived run IDs belong to isolated fallback generation, not your live history.\n\n'
        '`setup_transition_plan.json` and `reports/demo_setup_transition.html` compare the archived '
        'Lightning reference and model-agreement outputs. They estimate changes in modeled '
        'component counts, not actual climbs, operating time or shots saved.\n\n'
        'Generate again with `python3 -m scripts.prepare_demo_artifacts`.\n')
    (ROOT / 'artifacts/demo_artifact_manifest.json').write_text(json.dumps(evidence, indent=2))
    print(f'Prepared {len(cases)} offline fallback cases and one saved setup-change comparison.')


if __name__ == '__main__':
    prepare()
