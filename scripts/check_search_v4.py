"""Engineering-search development evidence; no ML training or held-out outcomes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import time
import numpy as np
from scipy.optimize import differential_evolution
from backend.app.optimization.engine import optimize, physics, profile_for, stock_for
from backend.app.physics.circuit import simulate
from backend.app.physics.compliance import RULES
from backend.app.schemas import OptimizeRequest
from scripts.check_model_agreement import CASES

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/experiments/search_v4'


def continuous_diagnostic(req):
    """Relax inventory discreteness but require raw reference timing to pass."""
    p=profile_for(req.profile_id);front,tail,_=stock_for(req,p);rule=RULES[req.impulse_type]
    cl=(req.load_c_pf+req.divider_c_pf+req.stray_c_pf+((p['base_c_pf'] or 0) if req.include_base_c else 0))*1e-12
    results=[]
    for n in range(max(p['min_stages'],req.stage_min or 0),min(p['max_stages'],req.stage_max or p['max_stages'])+1):
        cap=min(p['stage_kv'],math.sqrt(2*p['energy_stage_kj']*1e9/p['stage_c_uf'])/1000,
            math.sqrt(2*p['energy_total_kj']*1e9/(n*p['stage_c_uf']))/1000)
        if n*cap*req.efficiency < req.test_kv*(1-RULES['crest_tolerance_fraction']):continue
        rf=[math.sqrt(max(1e-18,(rule[k]*1e-6/1.67)**2-2.5*req.l_uh*1e-6*cl))/(n*cl) for k in ['front_min_us','front_max_us']]
        rt=[rule[k]*1e-6/(.693*(p['stage_c_uf']*1e-6+n*cl)) for k in ['tail_min_us','tail_max_us']]
        # All-series stock sum is an optimistic maximum, ignoring part limit.
        rf[1]=min(rf[1],sum(r*q for r,q in front.items()));rt[1]=min(rt[1],sum(r*q for r,q in tail.items()))
        if rf[0]>rf[1] or rt[0]>rt[1]:continue
        def evaluate(logs,details=False):
            f,t=np.exp(logs);cross=simulate(n,1,f,t,p['stage_c_uf'],cl*1e12,req.l_uh,req.efficiency,req.impulse_type,False)
            q=min(cap,2*req.test_kv/(n*req.efficiency+cross['crest_kv']))
            ref=physics(req,p,n,q,f,t);cross['crest_kv']*=q
            targets=np.array([rule['front_target_us'],rule['tail_target_us'],req.test_kv])
            widths=np.array([(rule['front_max_us']-rule['front_min_us'])/2,(rule['tail_max_us']-rule['tail_min_us'])/2,req.test_kv*.03])
            values=np.array([[x[k] for k in ['front_us','tail_us','crest_kv']] for x in [ref,cross]])
            worst=float(np.max(np.abs(values-targets)/widths))
            return {'stages':n,'front_r_stage':f,'tail_r_stage':t,'charge_kv_stage':q,'worst_tolerance_fraction':worst,'raw_reference':ref,'circuit':{k:cross[k] for k in ['front_us','tail_us','crest_kv']}} if details else worst
        fit=differential_evolution(evaluate,list(zip(np.log([rf[0],rt[0]]),np.log([rf[1],rt[1]]))),
            seed=437+n,popsize=10,maxiter=30,tol=1e-6,polish=True,workers=1)
        results.append(evaluate(fit.x,True))
    return {'scope':'Bounded deterministic development search over continuous raw-reference timing-feasible resistances. '
        'Ignores stock discreteness and ML corrections. Failure to find agreement is not proof of global infeasibility.',
        'settings_are_constructible':False,'best':min(results,key=lambda r:r['worst_tolerance_fraction']) if results else None,'per_stage':results}


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'summary.json').exists():raise SystemExit('Completed search_v4 study exists; preserve the recorded comparison.')
    files=[p for d in ['artifacts/models','artifacts/experiments/v2','artifacts/experiments/v3'] for p in (ROOT/d).rglob('*') if p.is_file()]
    preserved={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    protocol={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'cases':CASES,
        'continuous_search':{'seeds':'437 + stage count','maxiter':30,'popsize':10,'dimensions':2},
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'preserved_artifacts':preserved,
        'scope':'Search and numerical-solver development check, not a new model-accuracy test. No supervised outcomes used.'}
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2))
    started=time.perf_counter();rows={}
    for name,inputs in CASES.items():
        req=OptimizeRequest(**inputs,require_model_agreement=True);t=time.perf_counter();run=optimize(req);c=run['candidates'][0]
        rows[name]={'settings':c['settings'],'reference':c['hybrid'],
            'circuit':{k:c['circuit_crosscheck'][k] for k in ['front_us','tail_us','crest_kv']},
            'agreement':c['model_agreement'],'verification':c['verification'],'envelope_status':c['compliance']['status'],
            'score':c['score'],'seconds':time.perf_counter()-t}
        if not c['model_agreement']['both_nominal_pass']:rows[name]['continuous_diagnostic']=continuous_diagnostic(req)
        print(name,c['model_agreement']['both_nominal_pass'],c['verification']['passed'],flush=True)
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in preserved.items())
    result={'cases':rows,'elapsed_seconds':time.perf_counter()-started,'cloud_spend_usd':0,
            'frozen_models_unchanged':True,'scope':protocol['scope']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    print('Finished',result['elapsed_seconds'],flush=True)


if __name__=='__main__':run()
