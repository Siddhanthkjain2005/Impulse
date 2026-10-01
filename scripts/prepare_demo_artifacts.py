"""Generate clearly labeled offline fallback reports without touching live histories."""
from pathlib import Path
import json
import os
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.environ['IMPULSETWIN_DB'] = str(Path(tempfile.mkdtemp(prefix='impulsetwin-demo-')) / 'demo.sqlite3')
os.environ.setdefault('LOKY_MAX_CPU_COUNT', '4')
os.environ.setdefault('OMP_NUM_THREADS', '1')

from fastapi.testclient import TestClient
from backend.app.main import app


def prepare():
    client = TestClient(app)
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    samples = ROOT / 'data/demo'
    samples.mkdir(exist_ok=True)
    cases = {
        'lightning_reference': {},
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
        (samples / f'{name}_generated_trial.csv').write_bytes(wave.content)
        c = run['candidates'][0]
        evidence[name] = {'source_type': 'generated_stress_test', 'run_id': run['id'],
            'model_version': run['model_version'], 'settings': c['settings'],
            'nominal_pass': c['compliance']['nominal_pass'], 'status': c['compliance']['status'],
            'ml_trust': c['ood']['trust_weight'],
            'circuit_crosscheck': c['circuit_crosscheck']['compliance']['status'] if c['circuit_crosscheck'] else None}
    (samples / 'README.md').write_text(
        '# Offline demonstration samples\n\n'
        'Every CSV here is generated, not a measured laboratory shot. The saved JSON and HTML '
        'reports are reproducible model outputs for rehearsal and fallback. They do not claim '
        'laboratory validation. To upload a CSV, first create a matching live run in the app; '
        'the archived run IDs belong to isolated fallback generation, not your live history.\n\n'
        'Generate again with `python3 -m scripts.prepare_demo_artifacts`.\n')
    (ROOT / 'artifacts/demo_artifact_manifest.json').write_text(json.dumps(evidence, indent=2))
    print(f'Prepared {len(cases)} offline fallback reports, run snapshots and generated waveform CSVs.')


if __name__ == '__main__':
    prepare()
