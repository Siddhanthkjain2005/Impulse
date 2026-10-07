import sys,json,hashlib,time
from pathlib import Path
import numpy as np
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler,SplineTransformer
from sklearn.linear_model import Ridge
from scipy.optimize import minimize_scalar,linprog
from threadpoolctl import threadpool_limits
ROOT=Path('/Users/swetha/Downloads/HACKTHON_WIN')
sys.path.insert(0,str(ROOT))
from backend.app.ml import experiment_v2 as v2
from backend.app.ml.experiment_v5 import load_fit_frames
from backend.app.ml.experiment_v6 import CrestRegressor
OUT=Path('/tmp/impulsetwin-crest-structural')
NAMES=['Product cubic spline','Product quadratic Ridge','Product saturation','Product quadratic minimax','Fixed half product/control blend','Compact V6 spline control','Historical V2 refit']
if (OUT/'summary.json').exists(): raise RuntimeError('Frozen investigation; no rerun/retuning')
split=json.loads((ROOT/'artifacts/experiments/v2/protocol.json').read_text())
historical=json.loads((ROOT/'artifacts/experiments/v2/summary.json').read_text())['selection']['Switching'][2]
protocol={'hypothesis':'Remove separate capacitance/inductance nuisance dimensions while learning a compact relative crest trend on their product; compare finite smooth/saturating/envelope fits and a fixed blend to reduce estimator variance.', 'scope':'One compact exploratory original-Train-only CV, no nested winner claims or serving promotion. Historical V6 inspected; new fold seed does not create independent data. Stop after this fixed study.', 'outer_seed':881,'folds':5,'candidates':NAMES,'spline':{'knots':3,'degree':3,'alpha':1},'quadratic_ridge_alpha':.01,'saturation':'intercept + slope*u/(1+b*u), b>=0; optimize b by scalar profiled least squares; no external physical parameter assumed','minimax':'relative-error quadratic LP; all transforms per fold', 'blend':.5,'fit_ids':split['fit_ids']['Switching'],'dataset_sha256':hashlib.sha256((ROOT/'data/processed/synthetic_dataset.csv').read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT/'protocol.json').write_text(json.dumps(protocol,indent=2))
f=load_fit_frames(split)['Switching']
def product(fr):return ((fr.Load_C_pF+fr.Divider_C_pF+fr.Stray_C_pF)*fr.L_uH).to_numpy(float).reshape(-1,1)
def models(train,held):
    y=train.Residual_Crest.to_numpy(float)/train.Physics_Crest_kV.to_numpy(float)
    scale=StandardScaler().fit(product(train));a=scale.transform(product(train));b=scale.transform(product(held))
    spline=SplineTransformer(n_knots=3,degree=3,include_bias=False).fit(a);sa=spline.transform(a);sb=spline.transform(b);sc2=StandardScaler().fit(sa);sa=sc2.transform(sa);sb=sc2.transform(sb)
    ps=Ridge(alpha=1).fit(sa,y).predict(sb)
    qa=np.column_stack([a,a*a]);qb=np.column_stack([b,b*b]);sc3=StandardScaler().fit(qa);qa=sc3.transform(qa);qb=sc3.transform(qb)
    pq=Ridge(alpha=.01).fit(qa,y).predict(qb)
    norm=np.median(product(train));ua=product(train).ravel()/norm;ub=product(held).ravel()/norm
    def solution(beta):
        da=np.column_stack([np.ones(len(ua)),ua/(1+beta*ua)]);coef=np.linalg.lstsq(da,y,rcond=None)[0];return float(np.mean((da@coef-y)**2)),coef
    result=minimize_scalar(lambda logb:solution(np.exp(logb))[0],bounds=(-12,12),method='bounded')
    beta=float(np.exp(result.x));_,coef=solution(beta)
    sat=np.column_stack([np.ones(len(ub)),ub/(1+beta*ub)])@coef
    des=np.column_stack([np.ones(len(qa)),qa]);A=np.vstack([np.column_stack([des,-np.ones(len(qa))]),np.column_stack([-des,-np.ones(len(qa))])]);objective=np.array([0.,0.,0.,1.]);lp=linprog(objective,A_ub=A,b_ub=np.concatenate([y,-y]),bounds=[(None,None)]*3+[(0,None)],method='highs');assert lp.success
    mini=np.column_stack([np.ones(len(qb)),qb])@lp.x[:-1]
    control=CrestRegressor(dict(name='Relative Spline',alpha=1.,weighted=False)).fit(train).predict(held)/held.Physics_Crest_kV.to_numpy(float)
    hist=v2.predict_spec(v2.fit_spec(train,2,historical),held,2,historical)/held.Physics_Crest_kV.to_numpy(float)
    voltage=held.Physics_Crest_kV.to_numpy(float)
    return [v*voltage for v in [ps,pq,sat,mini,.5*(ps+control),control,hist]],{'saturation_beta':beta,'minimax_radius':float(lp.x[-1])}
def metrics(y,p):
    e=p-y;return {'rmse_kv':float(np.sqrt(np.mean(e*e))),'mae_kv':float(np.mean(abs(e))),'p95_error_kv':float(np.quantile(abs(e),.95)),'worst_error_kv':float(np.max(abs(e)))}
outputs={n:np.zeros(len(f)) for n in NAMES};folds=[]
with threadpool_limits(limits=1):
    for fold,(a,b) in enumerate(KFold(5,shuffle=True,random_state=881).split(f)):
        train,held=f.iloc[a],f.iloc[b];pred,info=models(train,held)
        for name,p in zip(NAMES,pred):outputs[name][b]=p
        fm={name:metrics(held.Residual_Crest.to_numpy(float),p) for name,p in zip(NAMES,pred)}
        folds.append({'fold':fold,'train_ids':train.ID.astype(int).tolist(),'held_ids':held.ID.astype(int).tolist(),'metrics':fm,**info});print(f'Fold {fold+1}/5 done',flush=True)
summary={'protocol':protocol,'metrics':{n:metrics(f.Residual_Crest.to_numpy(float),p) for n,p in outputs.items()},'folds':folds,'serving_changed':False,'selected_promoted':False}
for n,m in summary['metrics'].items():m['improvement_vs_v2_pct']=100*(1-m['rmse_kv']/summary['metrics']['Historical V2 refit']['rmse_kv']);m['fold_wins_vs_v2']=sum(r['metrics'][n]['rmse_kv']<r['metrics']['Historical V2 refit']['rmse_kv'] for r in folds)
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
(OUT/'oof.json').write_text(json.dumps({'ids':f.ID.astype(int).tolist(),'observed_residual':f.Residual_Crest.astype(float).tolist(),'physics':f.Physics_Crest_kV.astype(float).tolist(),'predicted_residuals':{n:p.tolist() for n,p in outputs.items()}},indent=2))
print(json.dumps(summary['metrics'],indent=2))
