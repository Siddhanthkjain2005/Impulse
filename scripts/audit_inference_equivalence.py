"""Paired frozen-model inference audit on controlled calculator inputs only.

Extract the original registry source from the baseline Git commit into a temporary
file, then pass it as --baseline-source. This harness fits nothing and never reads
the supplied dataset, generated captures or Hidden Test outcomes.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time

# Configure native libraries before importing pandas, NumPy or scikit-learn.
# An explicitly configured caller value is retained and recorded in the report.
THREAD_SETTINGS=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
for setting in THREAD_SETTINGS:
    os.environ.setdefault(setting,'1')

ROOT=Path(__file__).resolve().parents[1]


def positive_integer(value):
    number=int(value)
    if number<1:
        raise argparse.ArgumentTypeError('Must be a positive integer.')
    return number


def controlled_rows(typ,count,calculate):
    """32 fixed input environments; every fourth row intervenes on front stock."""
    rows=[]
    for index in range(count):
        j=index%32
        inputs=dict(impulse_type=typ,test_kv=(1350. if typ=='Lightning' else 1000.)+j,
            load_c_pf=700.+5*j,divider_c_pf=500.,stray_c_pf=150.,l_uh=18.5,efficiency=.82)
        physical=calculate(**inputs)
        rows.append({'Impulse_Type':typ,'Test_kV':inputs['test_kv'],'Load_C_pF':inputs['load_c_pf'],
            'Divider_C_pF':500.,'Stray_C_pF':150.,'L_uH':18.5,'Efficiency':.82,
            'Stages':physical['stages'],'Charge_kV_Stage':physical['charge_kv_stage'],
            'Front_R_Stage':physical['front_r_stage']+(5. if index%4==0 else 0.),
            'Tail_R_Stage':physical['tail_r_stage'],
            'Physics_FrontPeak_us':physical['front_us'],'Physics_Tail_us':physical['tail_us'],
            'Physics_Crest_kV':physical['crest_kv']})
    return rows


def benchmark(function,repetitions):
    function()  # Warm the frozen registry and estimator paths before timing.
    seconds=[]
    for _ in range(repetitions):
        started=time.perf_counter(); function(); seconds.append(time.perf_counter()-started)
    return {'median_seconds':statistics.median(seconds),'minimum_seconds':min(seconds),
        'repetitions':repetitions}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-source',required=True,type=Path,
        help='Original backend/app/ml/registry.py extracted from the baseline commit.')
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/hardening/inference_equivalence.json')
    parser.add_argument('--rows',type=positive_integer,default=512)
    parser.add_argument('--repetitions',type=positive_integer,default=9)
    args=parser.parse_args()
    source=args.baseline_source.resolve()
    if not source.is_file():
        parser.error('Baseline registry source does not exist.')
    output=args.output.resolve()
    if output.exists():
        parser.error('Output record already exists. Choose another --output path to preserve the initial evidence.')

    sys.path.insert(0,str(ROOT))
    import pandas as pd
    from backend.app.ml import registry as current
    from backend.app.data.workbook_reference import calculate

    # Preserve relative imports in the extracted source without replacing the
    # production module. Both registries load the same frozen V1 model artifacts.
    spec=importlib.util.spec_from_file_location('backend.app.ml.registry_baseline_audit',source)
    baseline=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    report={'source_type':'controlled_development','rows_per_batch':args.rows,'types':{},
        'thread_settings':{setting:os.environ[setting] for setting in THREAD_SETTINGS},
        'protocol':'32 fixed calculator input environments per impulse type; every fourth row changes front resistance by 5 ohms. Paired warmed timing and exact full-dictionary comparisons. No fitting, dataset access, Hidden Test access or threshold tuning.',
        'limitations':'Machine-dependent paired microbenchmarks; not complete pipeline speed or physical/model accuracy evidence.',
        'baseline_registry_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'current_registry_sha256':hashlib.sha256((ROOT/'backend/app/ml/registry.py').read_bytes()).hexdigest(),
        'audit_implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for typ in ('Lightning','Switching'):
        rows=controlled_rows(typ,args.rows,calculate); frame=pd.DataFrame(rows)
        old=baseline.infer(rows); new=current.infer(rows)
        item={'exact_full_output_equivalence':old==new,
            'support_exact_equivalence':bool((baseline.calculator_setting_support(frame)==current.calculator_setting_support(frame)).all()),
            'old_support':benchmark(lambda:baseline.calculator_setting_support(frame),args.repetitions),
            'new_support':benchmark(lambda:current.calculator_setting_support(frame),args.repetitions),
            'old_infer':benchmark(lambda:baseline.infer(rows),args.repetitions),
            'new_infer':benchmark(lambda:current.infer(rows),args.repetitions)}
        for operation in ('support','infer'):
            item[operation+'_speedup']=item['old_'+operation]['median_seconds']/item['new_'+operation]['median_seconds']
        report['types'][typ]=item

    report['equivalence_matrix']=[]
    for typ in ('Lightning','Switching'):
        rows=controlled_rows(typ,args.rows,calculate)
        for profile,mode in [('workbook_reference_profile','hybrid'),('workbook_reference_profile','physics'),
            ('cpri_problem_brief_profile','hybrid'),('cpri_problem_brief_profile','physics')]:
            old=baseline.infer(rows,profile,mode); new=current.infer(rows,profile,mode)
            report['equivalence_matrix'].append({'impulse_type':typ,'profile_id':profile,'mode':mode,
                'rows':len(rows),'exact_complete_output_equivalence':old==new,
                'unsupported_correction_disabled':all(not any(r['correction']) for r in new)
                    if profile!='workbook_reference_profile' or mode=='physics' else None})
    equivalent=all(item['exact_full_output_equivalence'] and item['support_exact_equivalence']
        for item in report['types'].values()) and all(item['exact_complete_output_equivalence']
        for item in report['equivalence_matrix'])
    report['status']='PASS' if equivalent else 'FAIL'
    output.parent.mkdir(parents=True,exist_ok=True)
    try:
        # Exclusive creation also protects a record created during the audit.
        with output.open('x',encoding='utf-8') as stream:
            stream.write(json.dumps(report,indent=2))
    except FileExistsError:
        parser.error('Output record already exists. Choose another --output path to preserve the initial evidence.')
    print(json.dumps(report,indent=2))
    return 0 if equivalent else 1


if __name__=='__main__':
    raise SystemExit(main())
