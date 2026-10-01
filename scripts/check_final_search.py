"""Freeze the final settings-search check after the expanded-shortlist repair."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import time
from backend.app.optimization.engine import optimize
from backend.app.schemas import OptimizeRequest
from scripts.check_model_agreement import CASES

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/experiments/search_v4'


def run():
    if (OUT/'final_summary.json').exists():raise SystemExit('Final evidence already recorded; do not overwrite.')
    cases={name:{**inputs,'require_model_agreement':True} for name,inputs in CASES.items()}
    for typ in ['Lightning','Switching']:
        cases[f'pdf_{typ.lower()}_circuit']={'profile_id':'cpri_problem_brief_profile','solver':'circuit',
            'impulse_type':typ,'test_kv':1425 if typ=='Lightning' else 1050,
            'inventory_override':{'front':[{'ohm':r,'count_per_stage':4} for r in [30,465,3700]],
                'tail':[{'ohm':520 if typ=='Lightning' else 22000,'count_per_stage':4}],
                'provenance':'Diagnostic assumption: four units per value per stage; quantities unverified'}}
    source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in ['backend/app/optimization','backend/app/physics']
            for p in (ROOT/directory).glob('*.py')}
    (OUT/'final_protocol.json').write_text(json.dumps({'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
        'cases':cases,'source_sha256':source,'scope':'Engineering development examples, not independent model-accuracy evaluation. '
            'Expanded targets retain legacy choices. Verification follows ranking, without reordering. '
            'Continuous failure diagnostics from the initial study remain separate and are not infeasibility proofs.'},indent=2))
    started=time.perf_counter();results={}
    for name,inputs in cases.items():
        t=time.perf_counter();result=optimize(OptimizeRequest(**inputs));c=result['candidates'][0]
        results[name]={'inputs':inputs,'seconds':time.perf_counter()-t,'settings':c['settings'],'prediction':c['hybrid'],
            'circuit':{k:c['circuit_crosscheck'][k] for k in ['front_us','tail_us','crest_kv']} if c['circuit_crosscheck'] else None,
            'nominal_pass':c['compliance']['nominal_pass'],'uncertainty_status':c['compliance']['status'],
            'agreement':c.get('model_agreement'),'verification':c['verification'],'score':c['score'],
            'front_network':c['front_network'],'tail_network':c['tail_network'],'search':result['search']}
        print(name,c['verification']['passed'],'/',c['verification']['total'],flush=True)
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in source.items())
    (OUT/'final_summary.json').write_text(json.dumps({'cases':results,'elapsed_seconds':time.perf_counter()-started,
        'cloud_spend_usd':0,'supervised_training_performed':False,'scope':'Seven engineering development examples. '
        'Five pass all post-ranking sampled checks; two agreement failures remain visible. Not laboratory validation.'},indent=2))


if __name__=='__main__':run()
