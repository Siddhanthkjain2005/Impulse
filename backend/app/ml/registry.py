import json
from functools import lru_cache
import joblib
import numpy as np
import pandas as pd
from .train import features, ROOT, VERSION, MODEL_FEATURES
from ..data.workbook_reference import calculate

@lru_cache
def registry():
    p=ROOT/'artifacts/models'
    return joblib.load(p/'residual_models.joblib'),json.loads((p/'registry.json').read_text())

@lru_cache
def experimental_registry():
    p=ROOT/'artifacts/experiments/v2'
    if not (p/'summary.json').exists():
        raise ValueError('V2 experiment is not available. Use the frozen V1 hybrid.')
    meta=json.loads((p/'summary.json').read_text())
    if not meta['promotion']['eligible']:
        raise ValueError('V2 did not meet its declared improvement gate. Use the frozen V1 hybrid.')
    return joblib.load(p/'calibrated_candidate_models.joblib'),meta

def calculator_setting_support(q):
    """Training has only calculator-selected settings, no resistor interventions."""
    supported=[]
    for _,r in q.iterrows():
        ref=calculate(impulse_type=r.Impulse_Type,test_kv=float(r.Test_kV),
            load_c_pf=float(r.Load_C_pF),divider_c_pf=float(r.Divider_C_pF),
            stray_c_pf=float(r.Stray_C_pF),l_uh=float(r.L_uH),efficiency=float(r.Efficiency))
        values=[r.Stages,r.Charge_kV_Stage,r.Front_R_Stage,r.Tail_R_Stage]
        expected=[ref[k] for k in ['stages','charge_kv_stage','front_r_stage','tail_r_stage']]
        supported.append(bool(np.allclose(values,expected,rtol=1e-10,atol=1e-8)))
    return np.array(supported,dtype=bool)

def infer(rows, profile_id='workbook_reference_profile', mode='hybrid'):
    if not rows: return []
    bundle,meta=registry(); q=pd.DataFrame(rows); typ=q.iloc[0].Impulse_Type; b=bundle[typ]; x=features(q)
    raw=np.column_stack([np.zeros(len(q)) if name=='Physics only' else b['models'][name].predict(x)[:,j] for j,name in enumerate(b['chosen'])])
    version=VERSION; chosen=b['chosen']; interval_widths=b['interval_halfwidth']
    coverage_limit='Marginal under synthetic exchangeability; not joint, conditional-on-support, optimizer-selected or laboratory coverage.'
    interval_method='90% marginal synthetic split-conformal'
    experimental=mode=='experimental_v2'
    if experimental:
        from .experiment_v2 import final_predict
        candidates,experiment=experimental_registry()
        raw=final_predict(candidates[typ],q,b)
        version=experiment['version']; chosen=[s['name']+' / '+s['basis'] for s in experiment['selection'][typ]]
        interval_widths=candidates[typ]['joint_interval_halfwidth']
        coverage_limit='Joint rectangle under synthetic exchangeability; unvalidated conditional-on-support, optimizer-selected, OOD or laboratory coverage.'
        interval_method='90% simultaneous synthetic split-conformal (three outputs)'
    nearest=b['nn'].kneighbors(b['scaler'].transform(x),n_neighbors=1)[0][:,0]
    widths=np.maximum(b['feature_max']-b['feature_min'],1e-6)
    envelope=np.maximum((b['feature_min']-x)/widths,(x-b['feature_max'])/widths)
    far=np.max(envelope,axis=1)>.2
    # Constant/near-constant features such as Lightning tail resistance are a hard
    # support boundary. Same inputs do not imply support for a new hardware setting.
    trust=np.clip((b['ood_p99']*1.5-nearest)/max(b['ood_p99']*1.5-b['ood_p95'],1e-6),0.,1.)
    trust[far]=0
    settings_supported=calculator_setting_support(q)
    trust[~settings_supported]=0
    if profile_id!='workbook_reference_profile' or mode=='physics': trust[:]=0
    results=[]
    for i in range(len(q)):
        t=float(trust[i]); support='in_distribution' if t==1. else ('limited_support' if t>0 else 'out_of_distribution')
        if profile_id!='workbook_reference_profile': support='profile_not_calibrated'
        if mode=='physics': support='physics_mode'
        correction=raw[i]*t
        base=q.iloc[i][['Physics_FrontPeak_us','Physics_Tail_us','Physics_Crest_kV']].to_numpy(float)
        # Extrapolation sensitivity envelope is explicitly uncalibrated.
        interval=interval_widths*(1+(1-t)*2)+abs(base)*np.array([.05,.05,.03])*(1-t)
        pred=base+correction
        results.append({'model_version':version,'selected_models':chosen,
            'experimental_model':experimental,'support_policy':'calculator-settings-and-envelope-v2',
            'raw_residual':raw[i].tolist(),'correction':correction.tolist(),'prediction':pred.tolist(),
            'ood':{'state':support,'trust_weight':t,'nearest_distance':float(nearest[i]),
                   'threshold_p95':b['ood_p95'],'outside_feature_envelope':bool(far[i]),
                   'calculator_setting_supported':bool(settings_supported[i]),
                   'support_limit':'Synthetic training uses only calculator-selected settings; arbitrary resistor or stage interventions are unsupported.',
                   'lab_calibrated':False},
            'uncertainty':{'lower':(pred-interval).tolist(),'upper':(pred+interval).tolist(),
                'halfwidth':interval.tolist(),'coverage_claim':.90 if t==1. else None,
                'coverage_limit':coverage_limit,
                'method':interval_method if t==1. else 'Uncalibrated OOD sensitivity envelope; no coverage guarantee'}})
    return results
