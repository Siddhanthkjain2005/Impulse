"""Reproducible residual-model competition. Hidden Test evaluated once after freeze."""
from pathlib import Path
import hashlib
import json
import time
from datetime import datetime, timezone
import joblib
import numpy as np
from sklearn.compose import TransformedTargetRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.svm import SVR
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
from sklearn.neighbors import NearestNeighbors
from .reference_knn import data, WorkbookKNN, FEATURES, PHYSICS, OBSERVED, RESIDUAL, metrics, ROOT

MODEL_FEATURES=FEATURES+['Stages','Charge_kV_Stage']+PHYSICS+['Total_C_pF']
VERSION='residual-competition-v1'

def features(df):
    x=df.copy(); x['Total_C_pF']=x.Load_C_pF+x.Divider_C_pF+x.Stray_C_pF
    return x[MODEL_FEATURES].to_numpy(float)

def report_metrics(y,p,physics,typ,latency_ms):
    result=metrics(y,p)
    base=np.sqrt(np.mean((physics-y)**2,axis=0))
    tolerance=np.array([.36,10.,np.mean(y[:,2])*.03]) if typ=='Lightning' else np.array([50.,500.,np.mean(y[:,2])*.03])
    result['normalized_rmse_tolerance']=(np.array(result['rmse'])/tolerance).tolist()
    result['rmse_improvement_vs_physics_pct']=(100*(1-np.array(result['rmse'])/np.maximum(base,1e-12))).tolist()
    result['inference_ms_per_record']=latency_ms
    return result

def candidates():
    return {
      'Ridge':(Ridge(),{'regressor__ridge__alpha':[.1,10.,100.]}),
      'SVR':(MultiOutputRegressor(SVR()),{'regressor__multioutputregressor__estimator__C':[1.,10.]}),
      'Random Forest':(RandomForestRegressor(n_estimators=80,random_state=41,n_jobs=1),{'regressor__randomforestregressor__min_samples_leaf':[5,15]}),
      'Extra Trees':(ExtraTreesRegressor(n_estimators=96,random_state=41,n_jobs=1),{'regressor__extratreesregressor__min_samples_leaf':[3,12]}),
      'Hist Gradient Boosting':(MultiOutputRegressor(HistGradientBoostingRegressor(max_iter=70,max_leaf_nodes=10,l2_regularization=5,random_state=41)),{'regressor__multioutputregressor__estimator__learning_rate':[.04,.1]})}

def train():
    target=ROOT/'artifacts/models'; target.mkdir(exist_ok=True,parents=True)
    if (target/'hidden_test_evaluation.json').exists():
        print('Frozen model and one-time Hidden Test evaluation already exist. Reusing; no hidden-test retuning.'); return
    df=data(); output={'version':VERSION,'created_at':datetime.now(timezone.utc).isoformat(),
        'dataset_sha256':hashlib.sha256((ROOT/'data/processed/synthetic_dataset.csv').read_bytes()).hexdigest(),
        'feature_list':MODEL_FEATURES,'source_profile':'workbook_reference_profile@1.0.0',
        'training_protocol':'Official Train only; seeded 80/20 fit/calibration within each type; 3-fold CV within fit; Validation selects per-target model; Hidden Test evaluated once after freeze.',
        'source_type':'supplied_synthetic','validation':{},'selection':{},'cv':{},
        'published_metric_parity':'unresolved source discrepancy; exact workbook formulas and cached case verified',
        'interval_method':'90% marginal split-conformal using held-out Train calibration; no lab coverage claim'}
    bundle={}
    exact=WorkbookKNN()
    for typ in ['Lightning','Switching']:
        tr=df[(df.Split=='Train')&(df.Impulse_Type==typ)]
        va=df[(df.Split=='Validation')&(df.Impulse_Type==typ)]
        fit,cal=train_test_split(tr,test_size=.2,random_state=41)
        xf,xc,xv=features(fit),features(cal),features(va)
        models={}; vp={}; cp={}; cv={}; latencies={}
        vp['Physics only']=np.zeros((len(va),3)); cp['Physics only']=np.zeros((len(cal),3)); latencies['Physics only']=0.
        start=time.perf_counter(); vp['Exact workbook kNN']=exact.predict(va); latencies['Exact workbook kNN']=(time.perf_counter()-start)*1000/len(va)
        for name,(reg,grid) in candidates().items():
            pipeline=TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(),reg),transformer=StandardScaler())
            search=GridSearchCV(pipeline,grid,cv=KFold(3,shuffle=True,random_state=41),scoring='neg_mean_squared_error',n_jobs=1)
            search.fit(xf,fit[RESIDUAL].to_numpy())
            models[name]=search.best_estimator_; cv[name]={'best_params':search.best_params_,'cv_mse':-float(search.best_score_)}
            start=time.perf_counter(); vp[name]=models[name].predict(xv); latencies[name]=(time.perf_counter()-start)*1000/len(va)
            cp[name]=models[name].predict(xc)
        y=va[OBSERVED].to_numpy(); base=va[PHYSICS].to_numpy()
        table={name:report_metrics(y,base+res,base,typ,latencies[name]) for name,res in vp.items()}
        # Exact reference kNN uses all Train rows; it is a benchmark, not a contender
        # for this held-out-calibration production pipeline.
        eligible=list(cp)
        chosen=[min(eligible,key=lambda name:table[name]['rmse'][j]) for j in range(3)]
        final=np.column_stack([vp[name][:,j] for j,name in enumerate(chosen)])
        calpred=cal[PHYSICS].to_numpy()+np.column_stack([cp[name][:,j] for j,name in enumerate(chosen)])
        errors=abs(cal[OBSERVED].to_numpy()-calpred)
        level=min(1.,np.ceil((len(cal)+1)*.90)/len(cal))
        widths=np.quantile(errors,level,axis=0,method='higher')
        scaler=StandardScaler().fit(xf); scaled=scaler.transform(xf)
        nn=NearestNeighbors(n_neighbors=2).fit(scaled); loo=nn.kneighbors(scaled)[0][:,1]
        table['Selected hybrid']=report_metrics(y,base+final,base,typ,sum(latencies[n] for n in set(chosen)))
        table['Selected hybrid']['interval_coverage_validation']=(abs(y-(base+final))<=widths).mean(axis=0).tolist()
        bundle[typ]={'models':models,'chosen':chosen,'interval_halfwidth':widths,'scaler':scaler,'nn':nn,
          'ood_p95':float(np.quantile(loo,.95)),'ood_p99':float(np.quantile(loo,.99)),
          'feature_min':xf.min(axis=0),'feature_max':xf.max(axis=0),
          'fit_ids':fit.ID.tolist(),'calibration_ids':cal.ID.tolist()}
        output['validation'][typ]=table; output['selection'][typ]=chosen; output['cv'][typ]=cv
        print(typ,chosen,'selected RMSE',table['Selected hybrid']['rmse'],flush=True)
    # Persist the exact configuration and models before reading hidden outcomes.
    frozen=json.dumps(output,sort_keys=True)
    output['frozen_config_sha256']=hashlib.sha256(frozen.encode()).hexdigest()
    joblib.dump(bundle,target/'residual_models.joblib')
    (target/'registry.json').write_text(json.dumps(output,indent=2))
    hidden={'evaluated_at':datetime.now(timezone.utc).isoformat(),'frozen_config_sha256':output['frozen_config_sha256'],
            'policy':'One final evaluation. No model changes in response to these scores.','metrics':{}}
    for typ in bundle:
        h=df[(df.Split=='Hidden Test')&(df.Impulse_Type==typ)]; b=bundle[typ]; x=features(h)
        res=np.column_stack([np.zeros(len(h)) if name=='Physics only' else b['models'][name].predict(x)[:,j] for j,name in enumerate(b['chosen'])])
        y=h[OBSERVED].to_numpy(); base=h[PHYSICS].to_numpy()
        hidden['metrics'][typ]={'Selected hybrid':report_metrics(y,base+res,base,typ,None),
            'Physics only':report_metrics(y,base,base,typ,None),
            'Exact workbook kNN':report_metrics(y,base+exact.predict(h),base,typ,None)}
    (target/'hidden_test_evaluation.json').write_text(json.dumps(hidden,indent=2))
    print('Frozen models and one-time Hidden Test evaluation saved.')

if __name__=='__main__': train()
