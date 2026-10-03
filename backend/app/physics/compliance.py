from pathlib import Path
import json
RULES=json.loads((Path(__file__).resolve().parents[3]/'config/compliance.json').read_text(encoding="utf-8"))

def check(impulse_type,test_kv,prediction,uncertainty=None,hardware_ok=True):
    rule=RULES[impulse_type]; p=[prediction[k] for k in ['front_us','tail_us','crest_kv']]
    targets=[rule['front_target_us'],rule['tail_target_us'],test_kv]
    bounds=[(rule['front_min_us'],rule['front_max_us']),(rule['tail_min_us'],rule['tail_max_us']),
            (test_kv*(1-RULES['crest_tolerance_fraction']),test_kv*(1+RULES['crest_tolerance_fraction']))]
    rows=[]
    for j,name in enumerate(['Front / peak time','Time to half-value','Crest voltage']):
        lower,upper=bounds[j]; passed=lower-1e-10<=p[j]<=upper+1e-10
        robust=passed and uncertainty is not None and uncertainty['lower'][j]>=lower and uncertainty['upper'][j]<=upper
        rows.append({'name':name,'target':targets[j],'predicted':p[j],'lower':lower,'upper':upper,
          'deviation':p[j]-targets[j],'deviation_pct':100*(p[j]/targets[j]-1),'pass':passed,'robust':robust,
          'unit':'kV' if j==2 else 'µs','reason':'Inside challenge limits' if passed else 'Outside challenge limits'})
    nominal=all(r['pass'] for r in rows) and hardware_ok
    robust=all(r['robust'] for r in rows) and hardware_ok
    return {'profile_id':RULES['id'],'version':RULES['version'],'source':RULES['source'],'rows':rows,
            'nominal_pass':nominal,'robust_pass':robust,'status':'ROBUST PASS' if robust else ('MARGINAL' if nominal else 'FAIL'),
            'hardware_pass':hardware_ok,'definition':rule['definition']}
