"""Separate, preregistered Train-only experiment. Never evaluates Hidden Test.

V1 artifacts and serving remain unchanged. All selection, scaling and feature
ablation happen inside inner folds; calibration is opened only after freeze.
"""
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, SplineTransformer, StandardScaler
from sklearn.svm import SVR
from threadpoolctl import threadpool_limits

from .reference_knn import FEATURES, PHYSICS, OBSERVED, RESIDUAL, ROOT, WorkbookKNN, metrics
from .train import features as v1_features

VERSION = 'targetwise-physics-v2-experiment'
OUTPUT = ROOT / 'artifacts/experiments/v2'
TYPES = ['Lightning', 'Switching']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_split(split):
    # Filter text rows before parsing numerical outcomes. Hidden Test labels
    # never enter this experiment's dataframe or prediction path.
    with (ROOT / 'data/processed/synthetic_dataset.csv').open(newline='') as f:
        rows = [r for r in csv.DictReader(f) if r['Split'] == split]
    frame = pd.DataFrame(rows)
    for name in set(FEATURES + PHYSICS + OBSERVED + RESIDUAL + ['ID', 'Stages', 'Charge_kV_Stage']):
        frame[name] = pd.to_numeric(frame[name])
    return frame


def basis(frame, name, target):
    c = (frame.Load_C_pF + frame.Divider_C_pF + frame.Stray_C_pF).to_numpy(float)
    l = frame.L_uH.to_numpy(float)
    if name == 'minimal mechanism':
        return [np.column_stack([c, l]), frame[['Load_C_pF']].to_numpy(float),
                np.column_stack([l * c])][target]
    if name == 'compact inputs':
        return frame[FEATURES].to_numpy(float)
    if name == 'physics interactions':
        return np.column_stack([frame[FEATURES].to_numpy(float), c, l*c,
                                np.sqrt(l*c), frame.Load_C_pF.to_numpy(float)/c])
    if name == 'V1 physics features':
        return v1_features(frame)
    raise ValueError(name)


def specs(target):
    result = []
    def add(name, feature_basis, relative, **params):
        result.append({'name':name, 'basis':feature_basis, 'relative':relative, 'params':params})
    for relative in [False, True]:
        add('Constant correction', 'minimal mechanism', relative)
        for alpha in [.01, 1., 100.]:
            add('Ridge', 'minimal mechanism', relative, alpha=alpha)
        for b in ['compact inputs', 'physics interactions', 'V1 physics features']:
            for alpha in [1., 100.]:
                add('Ridge', b, relative, alpha=alpha)
        for alpha in [1., 100.]:
            add('Polynomial Ridge', 'minimal mechanism', relative, alpha=alpha)
    for b in ['compact inputs', 'physics interactions']:
        for c in [1., 10.]:
            add('RBF SVR', b, True, C=c, epsilon=.15)
        for alpha in [1., 100.]:
            add('Spline Ridge', b, True, alpha=alpha)
        for leaf in [5, 15]:
            add('Extra Trees', b, True, min_samples_leaf=leaf)
        for leaves in [7, 15]:
            add('Histogram Boosting', b, True, max_leaf_nodes=leaves)
        for depth in [2, 3]:
            add('XGBoost', b, True, max_depth=depth)
    return result


def estimator(spec):
    p = spec['params']; name = spec['name']
    if name == 'Constant correction': reg = DummyRegressor()
    elif name == 'Ridge': reg = Ridge(**p)
    elif name == 'Polynomial Ridge':
        reg = make_pipeline(PolynomialFeatures(2, include_bias=False), StandardScaler(), Ridge(**p))
    elif name == 'Spline Ridge':
        reg = make_pipeline(SplineTransformer(n_knots=4, degree=2), StandardScaler(), Ridge(**p))
    elif name == 'RBF SVR': reg = SVR(**p)
    elif name == 'Extra Trees':
        reg = ExtraTreesRegressor(n_estimators=80, random_state=71, n_jobs=1, **p)
    elif name == 'Histogram Boosting':
        reg = HistGradientBoostingRegressor(max_iter=100, learning_rate=.05,
            l2_regularization=10, early_stopping=False, random_state=71, **p)
    elif name == 'XGBoost':
        from xgboost import XGBRegressor
        reg = XGBRegressor(n_estimators=120, learning_rate=.035, reg_lambda=10,
                           tree_method='hist', n_jobs=1, random_state=71, **p)
    else: raise ValueError(name)
    return TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(), reg),
                                      transformer=StandardScaler())


def fit_spec(frame, target, spec):
    model = estimator(spec)
    y = frame[RESIDUAL[target]].to_numpy(float)
    if spec['relative']: y = y / frame[PHYSICS[target]].to_numpy(float)
    model.fit(basis(frame, spec['basis'], target), y)
    return model


def predict_spec(model, frame, target, spec):
    p = model.predict(basis(frame, spec['basis'], target))
    return p * frame[PHYSICS[target]].to_numpy(float) if spec['relative'] else p


def v1_refit(old, frame):
    fitted = {}
    for name in set(old['chosen']):
        if name != 'Physics only':
            fitted[name] = clone(old['models'][name]).fit(v1_features(frame), frame[RESIDUAL].to_numpy(float))
    return fitted


def v1_predict(old, fitted, frame):
    x = v1_features(frame)
    return np.column_stack([np.zeros(len(frame)) if name == 'Physics only'
        else fitted[name].predict(x)[:,j] for j,name in enumerate(old['chosen'])])


def tolerances(frame, typ):
    front, tail = (.36, 10.) if typ == 'Lightning' else (50., 500.)
    return np.column_stack([np.full(len(frame),front), np.full(len(frame),tail),
                            .03*frame.Test_kV.to_numpy(float)])


def search(frame, typ, old, other_frame):
    """Choose full model+basis+parameters using inner folds only."""
    folds = list(KFold(3, shuffle=True, random_state=73).split(frame))
    truth = frame[RESIDUAL].to_numpy(float); tol = tolerances(frame,typ)
    # The frozen V1 procedure is eligible as a per-target fallback. Refits see
    # precisely the same rows as every other contender.
    vp = np.zeros_like(truth); kp = np.zeros_like(truth)
    for train_idx, test_idx in folds:
        a,b = frame.iloc[train_idx],frame.iloc[test_idx]
        vp[test_idx] = v1_predict(old,v1_refit(old,a),b)
        kp[test_idx] = WorkbookKNN(pd.concat([a,other_frame],ignore_index=True)).predict(b)
    choices=[]; leaderboards=[]
    for j in range(3):
        candidates = specs(j)
        scores=[]
        for spec in candidates:
            prediction=np.zeros(len(frame))
            for train_idx,test_idx in folds:
                a,b=frame.iloc[train_idx],frame.iloc[test_idx]
                model=fit_spec(a,j,spec)
                prediction[test_idx]=predict_spec(model,b,j,spec)
            scores.append(float(np.mean(((prediction-truth[:,j])/tol[:,j])**2)))
        fallback=[{'name':'Physics only','basis':'fixed','relative':False,'params':{}},
                  {'name':'Matched V1 refit','basis':'V1 physics features','relative':False,'params':{}},
                  {'name':'Matched exact kNN','basis':'workbook exact distance','relative':False,'params':{}}]
        for prediction in [np.zeros(len(frame)),vp[:,j],kp[:,j]]:
            scores.append(float(np.mean(((prediction-truth[:,j])/tol[:,j])**2)))
        candidates+=fallback
        order=np.argsort(scores,kind='stable'); best=int(order[0])
        choices.append(candidates[best])
        leaderboards.append([{**candidates[int(i)],'inner_normalized_mse':scores[int(i)]}
                              for i in order[:8]])
    return choices,leaderboards


def final_fit(frame, other_frame, choices, old):
    models={}; fallback=v1_refit(old,frame)
    for j,s in enumerate(choices):
        if s['name'] not in ['Physics only','Matched V1 refit','Matched exact kNN']:
            models[j]=fit_spec(frame,j,s)
    return {'models':models,'v1':fallback,'knn':WorkbookKNN(pd.concat([frame,other_frame],ignore_index=True)),
            'selection':choices}


def final_predict(bundle, frame, old):
    vp=v1_predict(old,bundle['v1'],frame); kp=bundle['knn'].predict(frame)
    return np.column_stack([np.zeros(len(frame)) if s['name']=='Physics only'
        else vp[:,j] if s['name']=='Matched V1 refit'
        else kp[:,j] if s['name']=='Matched exact kNN'
        else predict_spec(bundle['models'][j],frame,j,s) for j,s in enumerate(bundle['selection'])])


def metric_report(frame, predictions, typ):
    y=frame[OBSERVED].to_numpy(float); result=metrics(y,predictions)
    result['normalized_rmse_tolerance']=np.sqrt(np.mean(((predictions-y)/tolerances(frame,typ))**2,axis=0)).tolist()
    result['p95_absolute_error']=np.quantile(abs(predictions-y),.95,axis=0).tolist()
    return result


def run():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    if (OUTPUT/'summary.json').exists():
        print('V2 frozen experiment already exists; refusing post-result retuning.',flush=True); return
    data_path=ROOT/'data/processed/synthetic_dataset.csv'
    preserved={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'artifacts/models/residual_models.joblib',
        ROOT/'artifacts/models/registry.json',ROOT/'artifacts/models/hidden_test_evaluation.json']}
    old=joblib.load(ROOT/'artifacts/models/residual_models.joblib')
    train=read_split('Train'); assert len(train)==1400 and train.ID.is_unique
    fit={};cal={}
    for typ in TYPES:
        rows=train[train.Impulse_Type==typ]; assert len(rows)==700
        fit[typ],cal[typ]=train_test_split(rows,test_size=.2,random_state=41)
        assert fit[typ].ID.tolist()==old[typ]['fit_ids']
        assert set(fit[typ].ID).isdisjoint(cal[typ].ID)
    protocol={'version':VERSION,'registered_at':datetime.now(timezone.utc).isoformat(),
        'dataset_sha256':sha(data_path),'preserved_v1_sha256':preserved,
        'evaluation_scope':'Nested Train CV development evidence; no new untouched test or laboratory evaluation.',
        'fit_ids':{t:fit[t].ID.tolist() for t in TYPES},'calibration_ids':{t:cal[t].ID.tolist() for t in TYPES},
        'outer_cv':{'folds':5,'shuffle':True,'seed':71},'inner_cv':{'folds':3,'shuffle':True,'seed':73},
        'search_candidates':specs(0),'selection':'Per-target minimum inner tolerance-normalized MSE; V1, physics and exact kNN eligible fallbacks.',
        'promotion_rule':'Experimental candidate only if macro normalized RMSE improves at least 5% versus matched V1, no target RMSE regresses >2%; active V1 unchanged regardless.',
        'calibration_rule':'After model/config freeze; 90% joint rectangle, score=max target absolute error / fit-only scale; exact finite-sample order statistic.',
        'validation_policy':'Previously used Validation, development diagnostic only; read after freeze. Hidden Test never parsed or evaluated.',
        'compute':'Local CPU; estimator and BLAS single-thread; no cloud resources.',
        'versions':{'numpy':np.__version__},'runner_source_sha256':sha(Path(__file__))}
    import sklearn,xgboost
    protocol['versions'].update(sklearn=sklearn.__version__,xgboost=xgboost.__version__)
    protocol_path=OUTPUT/'protocol.json'
    if protocol_path.exists():
        existing=json.loads(protocol_path.read_text())
        # Resume only the identical declared experiment; do not silently replace a protocol.
        # Historical completed experiments are returned above. An interrupted
        # protocol without a source hash cannot resume under different code.
        assert 'runner_source_sha256' in existing,'Unhashed interrupted protocol cannot resume; use a separate experiment version.'
        for key in set(protocol)-{'registered_at'}:
            assert existing[key]==protocol[key],f'Protocol changed: {key}'
        protocol=existing
    else: protocol_path.write_text(json.dumps(protocol,indent=2))
    started=time.perf_counter(); folds={t:list(KFold(5,shuffle=True,random_state=71).split(fit[t])) for t in TYPES}
    output={'version':VERSION,'status':'experimental','evaluation_scope':protocol['evaluation_scope'],
        'protocol_sha256':sha(protocol_path),'nested_cv':{},'selection':{},'calibration':{},'validation_diagnostic':{}}
    bundles={};oof_records=[]
    for typ in TYPES:
        other=next(t for t in TYPES if t!=typ); frame=fit[typ]
        predictions={name:np.zeros((len(frame),3)) for name in ['V2 search','Matched V1 refit','Matched exact kNN']}
        fold_choices=[];fold_rmse=[]
        for k,(a,b) in enumerate(folds[typ]):
            other_a=folds[other][k][0]
            fa,fb=frame.iloc[a],frame.iloc[b]; fo=fit[other].iloc[other_a]
            tick=time.perf_counter(); choices,leaders=search(fa,typ,old[typ],fo)
            bundle=final_fit(fa,fo,choices,old[typ])
            predictions['V2 search'][b]=final_predict(bundle,fb,old[typ])
            predictions['Matched V1 refit'][b]=v1_predict(old[typ],bundle['v1'],fb)
            predictions['Matched exact kNN'][b]=bundle['knn'].predict(fb)
            rmse=np.sqrt(np.mean((predictions['V2 search'][b]-fb[RESIDUAL].to_numpy(float))**2,axis=0))
            fold_rmse.append(rmse.tolist());fold_choices.append({'fold':k,'selection':choices,'inner_leaders':leaders})
            print(f'{typ} outer fold {k+1}/5 RMSE {rmse.round(6).tolist()} ({time.perf_counter()-tick:.1f}s)',flush=True)
            for row,pos in enumerate(b):
                oof_records.append({'impulse_type':typ,'id':int(frame.iloc[pos].ID),'fold':k,
                    'train_ids':fa.ID.tolist(),'observed':fb.iloc[row][OBSERVED].to_numpy(float).tolist(),
                    'physics':fb.iloc[row][PHYSICS].to_numpy(float).tolist(),
                    **{name: (fb.iloc[row][PHYSICS].to_numpy(float)+p[pos]).tolist() for name,p in predictions.items()}})
            (OUTPUT/f'outer-{typ}-{k}.json').write_text(json.dumps(fold_choices[-1],indent=2))
        base=frame[PHYSICS].to_numpy(float)
        table={name:metric_report(frame,base+p,typ) for name,p in predictions.items()}
        table['Physics only']=metric_report(frame,base,typ)
        gain=100*(1-np.array(table['V2 search']['rmse'])/np.array(table['Matched V1 refit']['rmse']))
        output['nested_cv'][typ]={'metrics':table,'improvement_vs_v1_pct':gain.tolist(),
                                 'fold_rmse':fold_rmse,'fold_selections':fold_choices}
        choices,leaders=search(frame,typ,old[typ],fit[other])
        bundles[typ]=final_fit(frame,fit[other],choices,old[typ])
        output['selection'][typ]=choices
        output.setdefault('final_inner_leaders',{})[typ]=leaders
        print(f'{typ} final selection {[s["name"]+" / "+s["basis"] for s in choices]}',flush=True)
    joblib.dump(bundles,OUTPUT/'candidate_models.joblib')
    output['frozen_candidate_sha256']=sha(OUTPUT/'candidate_models.joblib')
    (OUTPUT/'frozen_configuration.json').write_text(json.dumps(output,indent=2))
    # No model selection below this point. Calibration and legacy development
    # diagnostics cannot trigger any parameter, feature or family changes.
    validation=read_split('Validation')
    for typ in TYPES:
        cf=cal[typ]; pred=cf[PHYSICS].to_numpy(float)+final_predict(bundles[typ],cf,old[typ])
        errors=abs(cf[OBSERVED].to_numpy(float)-pred)
        fixed_scale=np.maximum(np.std(fit[typ][RESIDUAL].to_numpy(float),axis=0),1e-12)
        rank=int(np.ceil((len(cf)+1)*.90)); scores=np.max(errors/fixed_scale,axis=1)
        quantile=float(np.sort(scores)[rank-1]); widths=quantile*fixed_scale
        bundles[typ]['joint_interval_halfwidth']=widths
        vf=validation[validation.Impulse_Type==typ]; vbase=vf[PHYSICS].to_numpy(float)
        tick=time.perf_counter(); vpred=vbase+final_predict(bundles[typ],vf,old[typ]); latency=(time.perf_counter()-tick)*1000/len(vf)
        output['calibration'][typ]={'rows':len(cf),'order_statistic_rank':rank,
            'fixed_scale_from_fit':fixed_scale.tolist(),'joint_halfwidth':widths.tolist(),
            'scope':'90% simultaneous synthetic exchangeability; unvalidated for OOD, support conditioning, optimizer selection or laboratory shots.'}
        output['validation_diagnostic'][typ]={'metrics':metric_report(vf,vpred,typ),
            'joint_empirical_coverage':float(np.mean(np.all(abs(vf[OBSERVED].to_numpy(float)-vpred)<=widths,axis=1))),
            'inference_ms_per_record':latency,'scope':'Previously observed development split; not independent final test.'}
    improvements=np.concatenate([output['nested_cv'][t]['improvement_vs_v1_pct'] for t in TYPES])
    baseline=np.concatenate([output['nested_cv'][t]['metrics']['Matched V1 refit']['normalized_rmse_tolerance'] for t in TYPES])
    candidate=np.concatenate([output['nested_cv'][t]['metrics']['V2 search']['normalized_rmse_tolerance'] for t in TYPES])
    macro_gain=float(100*(1-candidate.mean()/baseline.mean()))
    eligible=bool(macro_gain>=5 and improvements.min()>=-2)
    output['promotion']={'eligible':eligible,'macro_normalized_rmse_improvement_pct':macro_gain,
        'worst_target_improvement_pct':float(improvements.min()),'active_model':'residual-competition-v1',
        'reason':'Experimental gate passed; V1 remains active pending new independent evidence.' if eligible else 'Preregistered 5% macro / 2% non-regression gate not met; V1 remains active.'}
    output['elapsed_seconds']=time.perf_counter()-started
    output['hidden_test_evaluated']=False
    output['cloud_resources_created']=False
    output['v1_preserved']=all(sha(ROOT/p)==digest for p,digest in preserved.items())
    assert output['v1_preserved']
    joblib.dump(bundles,OUTPUT/'calibrated_candidate_models.joblib')
    (OUTPUT/'oof_predictions.json').write_text(json.dumps(oof_records,separators=(',',':')))
    (OUTPUT/'summary.json').write_text(json.dumps(output,indent=2))
    print(json.dumps(output['promotion']),flush=True)
    print(f'Finished in {output["elapsed_seconds"]:.1f}s. Frozen V1 preserved; Hidden Test not evaluated.',flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=1): run()
