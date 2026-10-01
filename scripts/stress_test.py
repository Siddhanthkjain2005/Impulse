"""Independent generated circuit scenarios, separate from official ML benchmark."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.app.data.workbook_reference import predict
from backend.app.physics.circuit import simulate
from backend.app.physics.compliance import check

def run():
    rng=np.random.default_rng(20260930); rows=[]
    for i in range(120):
        # Deliberate pass/fail and boundary spread; not a measured distribution.
        typ='Lightning' if i<60 else 'Switching'
        stage=int(rng.integers(8,16)); charge=float(rng.uniform(30,195)); eta=.82; test=stage*charge*eta
        load=float(rng.uniform(600,1500)); div=float(rng.uniform(350,750)); stray=float(rng.uniform(80,330)); l=float(rng.uniform(5,35))
        rf=float(rng.choice([30,50,75,100])) if typ=='Lightning' else float(rng.choice([3500,4500,5500]))
        rt=float(rng.choice([20,25,30])) if typ=='Lightning' else float(rng.choice([1000,1200,1400]))
        ref=predict(stage,charge,rf,rt,load,div,stray,l,eta,3)
        circuit=simulate(stage,charge,rf,rt,3,load+div+stray,l,eta,typ,False)
        rp=check(typ,test,ref)['nominal_pass']; cp=check(typ,test,circuit)['nominal_pass']
        row={'source_type':'generated_stress_test','id':i+1,'impulse_type':typ,'test_kv':test,
            'stages':stage,'charge_kv_stage':charge,'front_r_stage':rf,'tail_r_stage':rt,
            'load_c_pf':load,'divider_c_pf':div,'stray_c_pf':stray,'l_uh':l,'efficiency':eta,
            'reference_pass':rp,'circuit_pass':cp}
        row.update({f'reference_{k}':ref[k] for k in ['front_us','tail_us','crest_kv']})
        row.update({f'circuit_{k}':circuit[k] for k in ['front_us','tail_us','crest_kv']})
        rows.append(row)
    df=pd.DataFrame(rows); df.to_csv(ROOT/'data/processed/generated_stress_test.csv',index=False)
    summary={'source_type':'generated_stress_test','count':len(df),'seed':20260930,
        'reference_pass_count':int(df.reference_pass.sum()),'circuit_pass_count':int(df.circuit_pass.sum()),
        'reference_pass_circuit_fail':int((df.reference_pass&~df.circuit_pass).sum()),
        'reference_fail_circuit_pass':int((~df.reference_pass&df.circuit_pass).sum()),
        'agreement_fraction':float((df.reference_pass==df.circuit_pass).mean()),
        'limitations':'This is a deliberately broad synthetic model-disagreement diagnostic, not laboratory false-pass accuracy. The lumped circuit is also an unvalidated model. No rows used for fitting or official benchmark claims. Values are circuit stress settings, not recommendations; stock feasibility is tested separately by the optimizer.'}
    (ROOT/'artifacts/stress_test_summary.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))
if __name__=='__main__':run()
