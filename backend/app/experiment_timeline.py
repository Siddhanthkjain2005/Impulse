"""Read saved experiments only. This module never fits or scores a model."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def timeline(root=ROOT):
    def read(path):
        return json.loads((root / path).read_text(encoding='utf-8'))
    def digest(path):
        return hashlib.sha256((root / path).read_bytes()).hexdigest()
    registry = read('artifacts/models/registry.json')
    result = [{'version': registry['version'], 'name': 'V1', 'status': 'PROMOTED',
               'hypothesis': 'Correct systematic residual error relative to workbook physics.',
               'baseline': 'Physics and exact workbook kNN', 'dataset': registry['dataset_sha256'],
               'protocol': registry['training_protocol'], 'performance_change_pct': None,
               'promotion_criterion': 'Original frozen per-target model selection on Validation.',
               'decision': 'Active default. Saved synthetic Hidden Test results; no measured accuracy claim.',
               'evidence_type': 'SYNTHETIC BENCHMARK', 'hidden_test_evaluated': True,
               'evidence_path': 'artifacts/models/hidden_test_evaluation.json',
               'evidence_sha256': digest('artifacts/models/hidden_test_evaluation.json'),
               'metrics': read('artifacts/models/hidden_test_evaluation.json')}]
    for version in ('v2', 'v3', 'v4', 'v5'):
        path = f'artifacts/experiments/{version}'
        if not (root / path / 'summary.json').is_file():
            result.append({'name': version.upper(), 'status': 'NOT RECORDED'})
            continue
        summary, protocol = read(path + '/summary.json'), read(path + '/protocol.json')
        promotion = summary.get('promotion', {})
        baselines = list(next(iter(summary.get('nested_cv', {}).values()), {}).get('metrics', {}))
        result.append({'version': summary['version'], 'name': version.upper(),
                       'status': 'EXPERIMENTAL' if version == 'v2' else 'REJECTED' if not summary.get('promotion_eligible') else 'REVIEW REQUIRED',
                       'hypothesis': protocol.get('hypothesis') or summary['version'].replace('-', ' '),
                       'baseline': ', '.join(b for b in baselines if 'refit' in b or 'control' in b.lower()),
                       'dataset': protocol['dataset_sha256'],
                       'protocol': summary.get('evaluation_scope') or summary.get('scope') or protocol.get('scope'),
                       'performance_change_pct': promotion.get('macro_normalized_rmse_improvement_pct', summary.get('macro_improvement_pct')),
                       'promotion_criterion': protocol.get('promotion_rule', protocol.get('promotion')),
                       'decision': promotion.get('reason', summary.get('decision')),
                       'evidence_type': 'SYNTHETIC DEVELOPMENT CV',
                       'hidden_test_evaluated': summary['hidden_test_evaluated'],
                       'protocol_hash_matches': digest(path + '/protocol.json') == summary['protocol_sha256'],
                       'evidence_path': path + '/summary.json', 'evidence_sha256': digest(path + '/summary.json')})
    return {'active_model': registry['version'], 'experiments': result,
            'scope': 'Different comparators and protocols: improvements cannot be added. Development CV is not an independent test. No new training or Hidden Test evaluation was performed.'}
