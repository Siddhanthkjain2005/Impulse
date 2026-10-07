from pathlib import Path
import sys,json,time
sys.path.insert(0,'/Users/swetha/Downloads/HACKTHON_WIN')
import numpy as np,pandas as pd,joblib
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler,SplineTransformer,PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.kernel_ridge import KernelRidge
from sklearn.model_selection import KFold
from threadpoolctl import threadpool_limits
from backend.app.ml import experiment_v2 as v2,experiment_v5 as v5
from backend.app.ml.reference_knn import WorkbookKNN,RESIDUAL,PHYSICS,ROOT
OUT=Path('/tmp/impulsetwin-crest-methods')
split=json.loads((ROOT/'artifacts/experiments/v2/protocol.json').read_text());frames=v5.load_fit_frames(split)
baseline=json.loads((ROOT/'artifacts/experiments/v2/summary.json').read_text())['selection']['Switching'][2]
specs=[dict(method='Spline',knots=3,alpha=1),dict(method='Spline',knots=3,alpha=.01),dict(method='Poly',degree=3,alpha=.1),dict(method='RBF',alpha=.1,gamma=.1)]
SEEDS=[71,101,211]
protocol={'scope':'Repeated nested development study on previously explored Train fit rows; grids selected from prior exploratory CV so not independent evaluation','fit_ids':split['fit_ids'],'excluded_calibration_ids':split['calibration_ids'],'outer_fold_seeds':SEEDS,'outer_folds':5,'inner_folds':3,'inner_seed':73,'specs':specs,'selection':'Inner minimum tolerance MSE; candidate replaces minimum(V2 refit, exact kNN) only if MSE at least2% lower; fallback retained otherwise','stopping_rule':'No grid expansion after this fixed nested study'}
(OUT/'nested_protocol.json').write_text(json.dumps(protocol,indent=2))
def x(frame,spec):
 c=(frame.Load_C_pF+frame.Divider_C_pF+frame.Stray_C_pF).to_numpy(float);l=frame.L_uH.to_numpy(float)
 return np.column_stack([c,l]) if spec['method']=='Poly' else np.column_stack([c,l,c*l])
def fit(frame,spec):
 if spec['method']=='Spline':reg=SplineTransformer(n_knots=spec['knots'],degree=3);m=make_pipeline(StandardScaler(),reg,StandardScaler(),Ridge(alpha=spec['alpha']))
 elif spec['method']=='Poly':m=make_pipeline(StandardScaler(),PolynomialFeatures(spec['degree'],include_bias=False),StandardScaler(),Ridge(alpha=spec['alpha']))
 else:m=make_pipeline(StandardScaler(),KernelRidge(kernel='rbf',alpha=spec['alpha'],gamma=spec['gamma']))
 return m.fit(x(frame,spec),frame[RESIDUAL[2]].to_numpy(float)/frame[PHYSICS[2]].to_numpy(float))
def predict(m,frame,spec):return m.predict(x(frame,spec))*frame[PHYSICS[2]].to_numpy(float)
def paired_parts(fr,nfold,seed):return {t:list(KFold(nfold,shuffle=True,random_state=seed).split(f)) for t,f in fr.items()}
def scores(pred,frame):
 e=pred-frame[RESIDUAL[2]].to_numpy(float)
 return {'rmse_kv':float(np.sqrt(np.mean(e**2))),'tol_rmse':float(np.sqrt(np.mean((e/(.03*frame.Test_kV.to_numpy(float)))**2))),'mae_kv':float(np.mean(abs(e)))}
records=[]
with threadpool_limits(limits=1):
 for seed in SEEDS:
  part=paired_parts(frames,5,seed);y=frames['Switching'][RESIDUAL[2]].to_numpy(float)
  pp={n:np.zeros(len(y)) for n in ['V2 refit','Exact kNN','Inner champion','Selected candidate']};choices=[]
  for k,(a,b) in enumerate(part['Switching']):
   train={t:fr.iloc[part[t][k][0]].reset_index(drop=True) for t,fr in frames.items()};held=frames['Switching'].iloc[b]
   inner=paired_parts(train,3,73);truth=train['Switching'][RESIDUAL[2]].to_numpy(float);v=.03*train['Switching'].Test_kV.to_numpy(float)
   p={n:np.zeros(len(truth)) for n in ['V2 refit','Exact kNN']};cp=np.zeros((len(specs),len(truth)))
   for j,(ia,ib) in enumerate(inner['Switching']):
    tr=train['Switching'].iloc[ia];va=train['Switching'].iloc[ib];other=train['Lightning'].iloc[inner['Lightning'][j][0]]
    p['V2 refit'][ib]=v2.predict_spec(v2.fit_spec(tr,2,baseline),va,2,baseline)
    p['Exact kNN'][ib]=WorkbookKNN(pd.concat([tr,other],ignore_index=True)).predict(va)[:,2]
    for i,s in enumerate(specs):cp[i,ib]=predict(fit(tr,s),va,s)
   bscore={n:float(np.mean(((pr-truth)/v)**2)) for n,pr in p.items()};champ=min(bscore,key=bscore.get)
   cscores=[float(np.mean(((pr-truth)/v)**2)) for pr in cp];best=int(np.argmin(cscores));selected=specs[best] if cscores[best]<bscore[champ]*.98 else None
   pbase=v2.predict_spec(v2.fit_spec(train['Switching'],2,baseline),held,2,baseline);pknn=WorkbookKNN(pd.concat(list(train.values()),ignore_index=True)).predict(held)[:,2]
   pchamp=pbase if champ=='V2 refit' else pknn;pselected=predict(fit(train['Switching'],selected),held,selected) if selected else pchamp
   for n,pred in [('V2 refit',pbase),('Exact kNN',pknn),('Inner champion',pchamp),('Selected candidate',pselected)]:pp[n][b]=pred
   choices.append({'fold':k,'chosen':selected,'champion':champ,'baseline_inner_mse':bscore,'candidate_inner_mse':cscores,'fold':k,'held_ids':held.ID.tolist(),'train_ids':train['Switching'].ID.tolist(),'physical_scores':{n:scores(pred,held) for n,pred in [('V2 refit',pbase),('Exact kNN',pknn),('Inner champion',pchamp),('Selected candidate',pselected)]}})
  result={'seed':seed,'scores':{n:scores(p,frames['Switching']) for n,p in pp.items()},'choices':choices};records.append(result)
  print('seed',seed,result['scores'],'selections',[r['chosen'] for r in choices],flush=True)
  np.savez(OUT/f'nested-{seed}.npz',truth=y,ids=frames['Switching'].ID.to_numpy(int),**pp)
(OUT/'nested_results.json').write_text(json.dumps(records,indent=2))
