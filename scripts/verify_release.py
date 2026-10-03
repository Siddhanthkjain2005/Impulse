"""Local reproducibility checks. Never trains, deploys or downloads dependencies."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
REQUIRED = ['requirements.txt','frontend/package-lock.json','config/generator_profiles.json',
            'config/test_objects.json','config/compliance.json','config/optimization.json',
            'artifacts/models/residual_models.joblib','artifacts/models/registry.json',
            'artifacts/experiments/v2/calibrated_candidate_models.joblib','frontend/out/index.html',
            'frontend/out/judge/index.html','frontend/out/laboratory-evidence/index.html']


def integrity(root):
    manifest = json.loads((root/'config/release_integrity.json').read_text(encoding='utf-8'))
    failures = []
    for name, expected in manifest['files'].items():
        path = root/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append(name)
    return {'status': 'FAIL' if failures else 'PASS', 'checked_files': len(manifest['files']),
            'mismatches': failures, 'baseline_commit': manifest['baseline_commit']}


class Assets(HTMLParser):
    def __init__(self): super().__init__(); self.urls=[]
    def handle_starttag(self, tag, attrs):
        data=dict(attrs)
        if tag in ('script','img','source') and data.get('src'): self.urls.append(data['src'])
        if tag=='link' and data.get('rel') in ('stylesheet','preload','icon','modulepreload') and data.get('href'):
            self.urls.append(data['href'])


def static_assets(root):
    folder=root/'frontend/out'; pages=list(folder.rglob('*.html'))
    missing,remote,local=set(),set(),set()
    for page in pages:
        parser=Assets(); parser.feed(page.read_text(encoding='utf-8'))
        for url in parser.urls:
            parsed=urlparse(url)
            if parsed.scheme in ('http','https') or parsed.netloc: remote.add(url)
            elif not parsed.scheme:
                path=(folder/unquote(parsed.path).lstrip('/')) if parsed.path.startswith('/') else page.parent/unquote(parsed.path)
                if not path.is_file(): missing.add(url)
                else: local.add('/'+path.relative_to(folder).as_posix())
    return {'status':'PASS' if pages and local and not remote and not missing else 'FAIL',
            'pages':len(pages),'local_assets':sorted(local),'missing_assets':sorted(missing),'remote_assets':sorted(remote)}


def configuration(root):
    from backend.app.schemas import GeneratorProfile
    from backend.app.test_objects import catalog
    profiles=json.loads((root/'config/generator_profiles.json').read_text(encoding='utf-8'))
    for p in profiles: GeneratorProfile.model_validate(p)
    if len({p['id'] for p in profiles})!=len(profiles): raise ValueError('Duplicate generator profiles')
    catalog()
    weights=json.loads((root/'config/optimization.json').read_text(encoding='utf-8'))
    for key in ('front_deviation','tail_deviation','crest_deviation','component_count','ood_penalty','stage_utilization_penalty','uncertainty_penalty'):
        if not isinstance(weights[key],(int,float)) or not 0<=weights[key]<100: raise ValueError('Invalid optimizer weight '+key)
    from backend.app.ml.registry import registry,experimental_registry
    bundle,meta=registry(); _,v2=experimental_registry()
    if v2['promotion']['active_model']!=meta['version']: raise ValueError('Registry active model mismatch')
    for item in bundle.values():
        if any(name!='Physics only' and name not in item['models'] for name in item['chosen']):
            raise ValueError('Registry refers to a missing model')
    dataset=hashlib.sha256((root/'data/processed/synthetic_dataset.csv').read_bytes()).hexdigest()
    if dataset!=meta['dataset_sha256']: raise ValueError('Dataset differs from frozen registry')
    hidden=json.loads((root/'artifacts/models/hidden_test_evaluation.json').read_text(encoding='utf-8'))
    if hidden['frozen_config_sha256']!=meta['frozen_config_sha256']: raise ValueError('Frozen config identity mismatch')
    return {'status':'PASS','active_model':meta['version'],'profiles':len(profiles),
            'scope':'Loads frozen artifacts and compares metadata only; never reruns Hidden Test predictions.'}


def run_checks(full=True, root=ROOT):
    checks={}
    def check(name,fn):
        try: checks[name]=fn()
        except Exception as exc: checks[name]={'status':'FAIL','error':str(exc)}
    check('required_files',lambda:{'status':'FAIL' if any(not (root/p).is_file() for p in REQUIRED) else 'PASS',
                                  'missing':[p for p in REQUIRED if not (root/p).is_file()]})
    check('frozen_evidence_hashes',lambda:integrity(root))
    check('configuration_and_registry',lambda:configuration(root))
    env={**os.environ,'PYTHONUTF8':'1','NEXT_TELEMETRY_DISABLED':'1','LOKY_MAX_CPU_COUNT':'4'}
    report_dir=root/'artifacts/release_checks'; report_dir.mkdir(exist_ok=True)
    def command(name,args,cwd=root,timeout=600):
        try:
            output=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
            (report_dir/f'{name}.txt').write_text(output.stdout+'\n'+output.stderr,encoding='utf-8')
            return {'status':'PASS' if output.returncode==0 else 'FAIL','exit_code':output.returncode,
                    'command':args,'log':f'artifacts/release_checks/{name}.txt'}
        except (OSError,subprocess.TimeoutExpired) as exc:
            return {'status':'FAIL','error':str(exc)}
    if full:
        checks['backend_tests']=command('backend_tests',[sys.executable,'-m','pytest','--junitxml=artifacts/release_checks/backend-tests.xml'])
        npm=shutil.which('npm.cmd' if os.name=='nt' else 'npm')
        if npm:
            checks['frontend_typecheck']=command('frontend_typecheck',[npm,'run','typecheck'],root/'frontend')
            checks['frontend_build']=command('frontend_build',[npm,'run','build','--','--webpack'],root/'frontend')
        else:
            checks['frontend_typecheck']=checks['frontend_build']={'status':'NOT TESTED','reason':'npm unavailable'}
    else:
        for name in ('backend_tests','frontend_typecheck','frontend_build'):
            checks[name]={'status':'NOT TESTED','reason':'--quick requested; run full verifier for executed checks'}
    check('static_assets',lambda:static_assets(root))
    checks['fresh_database_offline_smoke']=command('fresh_database_offline_smoke',[sys.executable,'-m','scripts.release_smoke'])
    host_platform = {'Darwin': 'macOS'}.get(platform.system(), platform.system())
    for name in ('macOS','Linux','Windows'):
        checks[f'platform_{name}']={'status':'PASS' if name==host_platform and checks['fresh_database_offline_smoke']['status']=='PASS' else 'NOT TESTED',
                                  'scope':'Local fresh database and application smoke only; see separate build/test/install checks.'}
    checks['physically_disconnected_browser']={'status':'NOT TESTED','reason':'Network denial in the smoke process is not a physically disconnected laptop rehearsal.'}
    # Do not infer a fresh dependency installation from the presence of dependencies.
    install=root/'artifacts/release_checks/clean_install.json'
    checks['clean_install']=json.loads(install.read_text(encoding='utf-8')) if install.exists() else {'status':'NOT TESTED','reason':'Record an actual clean dependency installation separately.'}
    status='FAIL' if any(c['status']=='FAIL' for c in checks.values()) else 'PARTIAL' if any(c['status']=='NOT TESTED' for c in checks.values()) else 'PASS'
    result={'version':'1.0.0','recorded_at':datetime.now(timezone.utc).isoformat(),'status':status,
            'platform':platform.platform(),'python':platform.python_version(),'checks':checks,
            'scope':'Local verification only. No deployment, model fitting or new Hidden Test evaluation.'}
    (root/'artifacts/release_readiness.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (root/'artifacts/release_readiness.md').write_text('# Release readiness\n\n'+status+'\n\n'+ '\n'.join(f"- **{name}: {c['status']}** — {c.get('reason',c.get('scope',c.get('error','See JSON and retained log.')))}" for name,c in checks.items())+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--quick',action='store_true'); args=parser.parse_args()
    result=run_checks(not args.quick)
    print(json.dumps({'status':result['status'],'checks':{k:v['status'] for k,v in result['checks'].items()}},indent=2))
    sys.exit(1 if result['status']=='FAIL' else 0)
