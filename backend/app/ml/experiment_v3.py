"""Bounded V3 development ablation. Uses only the original Train fit IDs.

No calibration, Validation or Hidden Test outcomes are read. V1 and V2 stay
frozen. Historical feature/parameter exploration limits all CV interpretation.
"""
import hashlib
import json
import time
from pathlib import Path
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.compose import TransformedTargetRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, SplineTransformer, StandardScaler
from threadpoolctl import threadpool_limits

from . import experiment_v2 as v2
from .reference_knn import ROOT, PHYSICS, RESIDUAL, OBSERVED

OUTPUT=ROOT/'artifacts/experiments/v3'
VERSION='smooth-residual-v3-development'


def spec_grid():
    grid=[]
    for relative in [False,True]:
        for alpha in [.1,10.,1000.]:
            grid.append(dict(name='Ridge',relative=relative,alpha=alpha))
        for degree in [2,3]:
            for alpha in [1.,100.]:
                grid.append(dict(name='Polynomial Ridge',relative=relative,alpha=alpha,degree=degree))
        for knots in [3,5]:
            for alpha in [1.,100.]:
                grid.append(dict(name='Spline Ridge',relative=relative,alpha=alpha,knots=knots))
        grid.append(dict(name='Huber',relative=relative,alpha=.01))
    for alpha in [.01,.1,1.]:
        for gamma in [.1,1.]:
            grid.append(dict(name='RBF Kernel Ridge',relative=True,alpha=alpha,gamma=gamma))
    return grid


def x_features(frame,target):
    total=(frame.Load_C_pF+frame.Divider_C_pF+frame.Stray_C_pF).to_numpy(float)
    inductance=frame.L_uH.to_numpy(float)
    # Compact input-only physical groups. No fitted transformation outside folds.
    return [np.column_stack([total,inductance]),frame[['Load_C_pF']].to_numpy(float),
            np.column_stack([total,inductance,total*inductance])][target]


def fit(frame,j,spec):
    name=spec['name'];alpha=spec['alpha']
    if name=='Ridge': reg=Ridge(alpha=alpha)
    elif name=='Huber':reg=HuberRegressor(alpha=alpha,max_iter=500,epsilon=1.35)
    elif name=='Polynomial Ridge':
        reg=make_pipeline(PolynomialFeatures(spec['degree'],include_bias=False),StandardScaler(),Ridge(alpha=alpha))
    elif name=='Spline Ridge':
        reg=make_pipeline(SplineTransformer(n_knots=spec['knots'],degree=3),StandardScaler(),Ridge(alpha=alpha))
    else:reg=KernelRidge(kernel='rbf',alpha=alpha,gamma=spec['gamma'])
    model=TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(),reg),transformer=StandardScaler())
    y=frame[RESIDUAL[j]].to_numpy(float)
    if spec['relative']:y=y/frame[PHYSICS[j]].to_numpy(float)
    return model.fit(x_features(frame,j),y)


def predict(model,frame,j,spec):
    y=model.predict(x_features(frame,j))
    return y*frame[PHYSICS[j]].to_numpy(float) if spec['relative'] else y


def select(frame,j,baseline_spec,typ):
    folds=list(KFold(3,shuffle=True,random_state=73).split(frame))
    base=np.zeros(len(frame));y=frame[RESIDUAL[j]].to_numpy(float)
    denominator=v2.tolerances(frame,typ)[:,j]
    for a,b in folds:
        m=v2.fit_spec(frame.iloc[a],j,baseline_spec)
        base[b]=v2.predict_spec(m,frame.iloc[b],j,baseline_spec)
    baseline_score=float(np.mean(((base-y)/denominator)**2))
    best={'name':'Historical V2 refit','blend':0.};best_score=baseline_score
    scores=[]
    for spec in spec_grid():
        p=np.zeros(len(frame))
        for a,b in folds:p[b]=predict(fit(frame.iloc[a],j,spec),frame.iloc[b],j,spec)
        for weight in [.5,1.]:
            score=float(np.mean(((weight*p+(1-weight)*base-y)/denominator)**2))
            candidate={**spec,'blend':weight}
            scores.append({**candidate,'normalized_mse':score})
            if score<best_score and score<=baseline_score*.98:
                best=candidate;best_score=score
    return best,{'baseline_normalized_mse':baseline_score,'chosen_normalized_mse':best_score,
                 'leaders':sorted(scores,key=lambda s:s['normalized_mse'])[:5]}


def run():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    if (OUTPUT/'summary.json').exists():
        print('Frozen V3 experiment exists; no retuning.');return
    previous=json.loads((ROOT/'artifacts/experiments/v2/summary.json').read_text())
    split=json.loads((ROOT/'artifacts/experiments/v2/protocol.json').read_text())
    train=v2.read_split('Train')
    frames={t:train.set_index('ID',drop=False).loc[split['fit_ids'][t]].reset_index(drop=True) for t in v2.TYPES}
    preserved={str(p.relative_to(ROOT)):v2.sha(p) for directory in ['artifacts/models','artifacts/experiments/v2'] for p in (ROOT/directory).rglob('*') if p.is_file()}
    protocol={'version':VERSION,'registered_at':datetime.now(timezone.utc).isoformat(),
        'runner_sha256':v2.sha(Path(__file__)),'dataset_sha256':v2.sha(ROOT/'data/processed/synthetic_dataset.csv'),
        'fit_ids':split['fit_ids'],'preserved_sha256':preserved,'grid':spec_grid(),
        'blends':[.5,1.],'inner_selection':'Minimum tolerance-normalized MSE only if at least 2% better than historical V2 fallback.',
        'outer':{'folds':5,'seed':71},'inner':{'folds':3,'seed':73},
        'promotion':'At least 5% macro tolerance-normalized RMSE improvement, no target >2% regression. Passing only permits consideration; no automatic production change.',
        'scope':'Train development ablation with previously explored features and historically selected V2 comparator. No independent test, calibration or laboratory evaluation.'}
    protocol_path=OUTPUT/'protocol.json'
    if protocol_path.exists():
        prior=json.loads(protocol_path.read_text());assert {k:v for k,v in prior.items() if k!='registered_at'}=={k:v for k,v in protocol.items() if k!='registered_at'}
    else:protocol_path.write_text(json.dumps(protocol,indent=2))
    started=time.perf_counter();result={'version':VERSION,'scope':protocol['scope'],'protocol_sha256':v2.sha(protocol_path),'nested_cv':{}}
    oof=[]
    for typ,frame in frames.items():
        p=np.zeros((len(frame),3));base=np.zeros_like(p);choices=[]
        for k,(a,b) in enumerate(KFold(5,shuffle=True,random_state=71).split(frame)):
            af,bf=frame.iloc[a],frame.iloc[b];fold=[]
            for j in range(3):
                baseline_spec=previous['selection'][typ][j]
                s,log=select(af,j,baseline_spec,typ)
                baseline=v2.fit_spec(af,j,baseline_spec)
                base[b,j]=v2.predict_spec(baseline,bf,j,baseline_spec)
                p[b,j]=base[b,j] if s['blend']==0 else s['blend']*predict(fit(af,j,s),bf,j,s)+(1-s['blend'])*base[b,j]
                fold.append({'selection':s,**log})
            choices.append(fold)
            for pos in b:oof.append({'id':int(frame.iloc[pos].ID),'type':typ,'fold':k,'train_ids':af.ID.tolist(),
                'observed':frame.iloc[pos][OBSERVED].to_numpy(float).tolist(),
                'v3_prediction':(frame.iloc[pos][PHYSICS].to_numpy(float)+p[pos]).tolist(),
                'v2_refit_prediction':(frame.iloc[pos][PHYSICS].to_numpy(float)+base[pos]).tolist()})
            print(f'{typ} fold {k+1}/5 complete',flush=True)
        physics=frame[PHYSICS].to_numpy(float)
        table={name:v2.metric_report(frame,pred,typ) for name,pred in [('V3 search',physics+p),('Historical V2 refit',physics+base),('Physics only',physics)]}
        improvement=100*(1-np.array(table['V3 search']['rmse'])/table['Historical V2 refit']['rmse'])
        result['nested_cv'][typ]={'metrics':table,'improvement_vs_v2_pct':improvement.tolist(),'fold_choices':choices}
    baseline=np.concatenate([result['nested_cv'][t]['metrics']['Historical V2 refit']['normalized_rmse_tolerance'] for t in v2.TYPES])
    candidate=np.concatenate([result['nested_cv'][t]['metrics']['V3 search']['normalized_rmse_tolerance'] for t in v2.TYPES])
    gains=np.concatenate([result['nested_cv'][t]['improvement_vs_v2_pct'] for t in v2.TYPES])
    macro=float(100*(1-candidate.mean()/baseline.mean()));eligible=bool(macro>=5 and gains.min()>=-2)
    result.update(macro_improvement_pct=macro,promotion_eligible=eligible,hidden_test_evaluated=False,
        calibration_evaluated=False,validation_evaluated=False,cloud_spend_usd=0,elapsed_seconds=time.perf_counter()-started,
        decision='Candidate merits separate independent validation; V1/V2 unchanged.' if eligible else 'No promotion: additional complexity did not meet the preregistered improvement threshold. V1/V2 unchanged.')
    assert all(v2.sha(ROOT/p)==digest for p,digest in preserved.items())
    result['preserved_artifacts_verified']=True
    (OUTPUT/'oof_predictions.json').write_text(json.dumps(oof,separators=(',',':')))
    (OUTPUT/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ['macro_improvement_pct','promotion_eligible','decision','elapsed_seconds']}),flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=1):run()
