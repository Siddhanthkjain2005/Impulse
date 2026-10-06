"""Controlled numerical stress probe; no workbook rows or laboratory evidence."""
import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--solver-source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose another path to preserve the earlier record.')
    root=args.root.resolve();sys.path.insert(0,str(root))
    source=(args.solver_source or root/'backend/app/physics/circuit.py').resolve()
    # A source override compares the frozen pre-change solver using the same
    # shared (unchanged) waveform analyzer without editing a working checkout.
    namespace={'__name__':'backend.app.physics.stress_probe','__package__':'backend.app.physics'}
    exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),namespace)
    simulate=namespace['simulate']
    protocols=[
        ('ordinary_extremes',
         ['total_c_pf','l_uh','front_r_stage','tail_r_stage'],
         [[.1,1,100,1500,100000,300000],[0,1e-8,1e-7,1e-4,.01,12,10000],
          [.01,30,465,3700,1e6],[.01,520,22000,1e8]],
         {'stages':11,'charge_kv_stage':180,'stage_c_uf':.125,
          'efficiency':.83,'impulse_type':'Lightning','include_waveform':False}),
        ('extreme_stiffness',
         ['stages','stage_c_uf','total_c_pf','l_uh','front_r_stage','tail_r_stage'],
         [[2,12,30],[.125,3],[.001,100,300000],[1.01e-8,1e-6,1,10000],
          [30,1e8],[520,1e8]],
         {'charge_kv_stage':180,'efficiency':.83,'impulse_type':'Switching',
          'include_waveform':False}),
    ]
    results=[]
    for name,fields,values,fixed in protocols:
        failures=[];completed=0;maximum_energy_ratio=0
        for combo in itertools.product(*values):
            inputs={**fixed,**dict(zip(fields,combo))}
            try:
                result=simulate(**inputs)
                metrics=[result[k] for k in ['front_us','tail_us','crest_kv']]
                if not np.isfinite(metrics).all() or min(metrics)<=0:
                    raise ValueError('Non-finite or non-positive extracted metrics.')
                energy=result['diagnostics']['maximum_energy_ratio']
                if not np.isfinite(energy) or energy>1+1e-8:
                    raise ValueError('Numerical trajectory violates passive energy bound.')
                maximum_energy_ratio=max(maximum_energy_ratio,energy)
                completed+=1
            except (ValueError,ArithmeticError,np.linalg.LinAlgError) as exc:
                failures.append({'inputs':inputs,'error_type':type(exc).__name__,'message':str(exc)})
        results.append({'name':name,'fixed_inputs':fixed,'varying_fields':fields,
                        'varying_values':values,'case_count':completed+len(failures),
                        'resolved_case_count':completed,'diagnostic_failure_count':len(failures),
                        'maximum_energy_ratio_among_resolved_cases':maximum_energy_ratio,
                        'diagnostic_failures':failures})
    payload={'schema_version':1,'solver_version':namespace['VERSION'],
             'source':str(source),'numpy_version':np.__version__,
             'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
             'scope':'Deterministic generated circuit inputs for numerical regression; '
                     'not training data, independent measured evidence, a search-quality '
                     'benchmark, or a statistical reliability estimate.',
             'protocols':results}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:r[k] for k in ['name','case_count','resolved_case_count',
                                       'diagnostic_failure_count']} for r in results]))


if __name__=='__main__':main()
