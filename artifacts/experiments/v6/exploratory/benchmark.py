from pathlib import Path
import sys,json,time,hashlib,csv
sys.path.insert(0,'/Users/swetha/Downloads/HACKTHON_WIN')
import numpy as np,pandas as pd,joblib
from sklearn.linear_model import Ridge, LinearRegression, QuantileRegressor
from sklearn.preprocessing import StandardScaler,SplineTransformer,PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.kernel_ridge import KernelRidge
from sklearn.model_selection import KFold
from scipy.optimize import linprog
from threadpoolctl import threadpool_limits
from backend.app.ml import experiment_v2 as v2,experiment_v5 as v5
from backend.app.ml.reference_knn import WorkbookKNN,FEATURES,PHYSICS,RESIDUAL,ROOT

OUT=Path('/tmp/impulsetwin-crest-methods')
SPLIT=json.loads((ROOT/'artifacts/experiments/v2/protocol.json').read_text())
frames=v5.load_fit_frames(SPLIT)
old=joblib.load(ROOT/'artifacts/models/residual_models.joblib')
v2spec=json.loads((ROOT/'artifacts/experiments/v2/summary.json').read_text())['selection']['Switching'][2]

def x_basis(frame,name):
    c=(frame.Load_C_pF+frame.Divider_C_pF+frame.Stray_C_pF).to_numpy(float)/1000
    l=frame.L_uH.to_numpy(float)/30
    if name=='lc':return np.column_stack([l*c])
    if name=='c_l_lc':return np.column_stack([c,l,l*c])
    if name=='c_l':return np.column_stack([c,l])
    if name=='lc_root':return np.column_stack([l*c,np.sqrt(l*c)])
    if name=='c_l_lc_eff':return np.column_stack([c,l,l*c,frame.Efficiency.to_numpy(float)])
    if name=='c_l_lc_parts':return np.column_stack([c,l,l*c,frame.Load_C_pF.to_numpy(float)/1000,frame.Divider_C_pF.to_numpy(float)/1000,frame.Stray_C_pF.to_numpy(float)/1000])
    if name=='c_l_lc_voltage':return np.column_stack([c,l,l*c,frame.Test_kV.to_numpy(float)/1000])
    if name=='c_l_lc_eff_voltage':return np.column_stack([c,l,l*c,frame.Efficiency.to_numpy(float),frame.Test_kV.to_numpy(float)/1000])
    if name=='inputs':return frame[FEATURES].to_numpy(float)
    raise ValueError(name)

class Envelope:
    def __init__(self,kind):self.kind=kind
    def fit(self,x,y):
        self.s=StandardScaler().fit(x);z=self.s.transform(x)
        if self.kind=='Minimax':
            d=np.column_stack([np.ones(len(z)),z]);a=np.vstack([np.column_stack([d,-np.ones(len(z))]),np.column_stack([-d,-np.ones(len(z))])]);o=np.zeros(d.shape[1]+1);o[-1]=1
            self.fit_=linprog(o,A_ub=a,b_ub=np.concatenate([y,-y]),bounds=[(None,None)]*d.shape[1]+[(0,None)],method='highs')
            assert self.fit_.success;self.coef=self.fit_.x[:-1]
        else:
            q=[.05,.95] if self.kind=='Q05' else [.1,.9] if self.kind=='Q10' else [.2,.8]
            self.models=[QuantileRegressor(quantile=t,alpha=0,solver='highs').fit(z,y) for t in q]
        return self
    def predict(self,x):
        z=self.s.transform(x)
        if self.kind=='Minimax':return np.column_stack([np.ones(len(z)),z])@self.coef
        return np.mean([m.predict(z) for m in self.models],axis=0)

def specs():
    out=[]
    for relative in [True,False]:
        for basis in ['lc','c_l_lc','lc_root','c_l_lc_eff','c_l_lc_parts','c_l_lc_voltage','c_l_lc_eff_voltage']:
            for a in [.01,1]:out.append(dict(method='Ridge',basis=basis,relative=relative,alpha=a))
    for degree in [2,3]:
        for a in [.1,10]:out.append(dict(method='Poly',basis='c_l',relative=True,degree=degree,alpha=a))
    for basis in ['lc','c_l_lc']:
        for method in ['Minimax','Q05','Q10','Q20']:out.append(dict(method=method,basis=basis,relative=True))
    for basis in ['lc','c_l_lc']:
        for knots in [3,5]:
            for a in [.01,1]:out.append(dict(method='Spline',basis=basis,relative=True,knots=knots,alpha=a))
    for basis in ['lc','c_l_lc']:
        for a in [.01,.1,1]:
            for gamma in [.01,.1]:out.append(dict(method='RBF',basis=basis,relative=True,alpha=a,gamma=gamma))
    return out
GRID=specs();SEEDS=[71,101,211]
protocol={'scope':'Exploratory Train fit-only development; previously explored features; no calibrated claim or promotion','fit_ids':SPLIT['fit_ids'],'excluded_calibration_ids':SPLIT['calibration_ids'],'seeds':SEEDS,'folds':5,'grid':GRID,'baselines':['Exact workbook kNN matched fit','V1 frozen params refit','V2 frozen params refit'],'metric':'physical RMSE and rowwise crest tolerance RMSE'}
(OUT/'protocol.json').write_text(json.dumps(protocol,indent=2))

def fit(train,spec):
    method=spec['method'];x=x_basis(train,spec['basis']);y=train[RESIDUAL[2]].to_numpy(float)
    if spec['relative']:y=y/train[PHYSICS[2]].to_numpy(float)
    if method=='Ridge':m=make_pipeline(StandardScaler(),Ridge(alpha=spec['alpha']))
    elif method=='Poly':m=make_pipeline(StandardScaler(),PolynomialFeatures(spec['degree'],include_bias=False),StandardScaler(),Ridge(alpha=spec['alpha']))
    elif method=='Spline':m=make_pipeline(StandardScaler(),SplineTransformer(n_knots=spec['knots'],degree=3),StandardScaler(),Ridge(alpha=spec['alpha']))
    elif method=='RBF':m=make_pipeline(StandardScaler(),KernelRidge(kernel='rbf',alpha=spec['alpha'],gamma=spec['gamma']))
    else:m=Envelope(method)
    m.fit(x,y);return m

def predict(m,held,spec):
    y=m.predict(x_basis(held,spec['basis']))
    return y*held[PHYSICS[2]].to_numpy(float) if spec['relative'] else y

def report(p,y,v):
    e=p-y
    return {'rmse_kv':float(np.sqrt(np.mean(e*e))),'mae_kv':float(np.mean(abs(e))),'tol_rmse':float(np.sqrt(np.mean((e/(.03*v))**2))),'p95_abs':float(np.quantile(abs(e),.95))}

results=[]
with threadpool_limits(limits=1):
 for seed in SEEDS:
    frame=frames['Switching'];y=frame[RESIDUAL[2]].to_numpy(float);v=frame.Test_kV.to_numpy(float)
    parts={t:list(KFold(5,shuffle=True,random_state=seed).split(f)) for t,f in frames.items()}
    preds={name:np.zeros(len(frame)) for name in ['Exact kNN','V1 refit','V2 refit']};cand=np.zeros((len(GRID),len(frame)))
    for k,(a,b) in enumerate(parts['Switching']):
        train,held=frame.iloc[a],frame.iloc[b];other=frames['Lightning'].iloc[parts['Lightning'][k][0]]
        preds['Exact kNN'][b]=WorkbookKNN(pd.concat([train,other],ignore_index=True)).predict(held)[:,2]
        preds['V1 refit'][b]=v2.v1_predict(old['Switching'],v2.v1_refit(old['Switching'],train),held)[:,2]
        preds['V2 refit'][b]=v2.predict_spec(v2.fit_spec(train,2,v2spec),held,2,v2spec)
        for i,spec in enumerate(GRID):cand[i,b]=predict(fit(train,spec),held,spec)
    records=[{'name':name,**report(p,y,v)} for name,p in preds.items()]+[{'spec':spec,**report(cand[i],y,v)} for i,spec in enumerate(GRID)]
    records.sort(key=lambda r:r['tol_rmse']);results.append({'seed':seed,'records':records})
    print('seed',seed,'baselines',[r for r in records if 'name' in r],'leaders',records[:8],flush=True)
    np.savez(OUT/f'predictions-{seed}.npz',candidate=cand,truth=y,voltage=v,**preds)
(OUT/'results.json').write_text(json.dumps(results,indent=2))
means=[]
for i,spec in enumerate(GRID):
 rs=[next(r for r in result['records'] if r.get('spec')==spec) for result in results]
 means.append({'spec':spec,'mean_rmse_kv':float(np.mean([r['rmse_kv'] for r in rs])),'mean_tol_rmse':float(np.mean([r['tol_rmse'] for r in rs])),'per_seed':rs})
means.sort(key=lambda r:r['mean_tol_rmse']);(OUT/'aggregate.json').write_text(json.dumps(means,indent=2))
print('aggregate leaders',means[:10],flush=True)
