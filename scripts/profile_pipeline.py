"""Fixed development/runtime observations; no model fitting or Hidden Test reads."""
import argparse, cProfile, hashlib, json, os, platform, pstats, statistics, subprocess, sys, time
from pathlib import Path

REPOSITORY=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label',required=True)
parser.add_argument('--repeats',type=int,default=3)
parser.add_argument('--source-root',type=Path,default=REPOSITORY,
                    help='Immutable comparison checkout, if profiling the old implementation.')
args=parser.parse_args()
if args.repeats < 2 or Path(args.label).name != args.label or args.label in ('.', '..'):
 raise SystemExit('Use at least two repetitions and a simple record label.')
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
 os.environ.setdefault(variable,'1')
os.environ.setdefault('LOKY_MAX_CPU_COUNT','4')
ROOT=args.source_root.resolve()
sys.path.insert(0,str(ROOT)); os.chdir(ROOT)
from backend.app.schemas import OptimizeRequest
from backend.app.optimization.engine import optimize
from backend.app.reports import report_html
from scripts.benchmark_search_quality import compare

CASES={
 'default_lightning':{},
 'default_switching':{'impulse_type':'Switching'},
 'cpri_matched_1425':{'profile_id':'cpri_problem_brief_profile','solver':'circuit','model_mode':'physics',
   'load_c_pf':650,'divider_c_pf':250,'stray_c_pf':55,'include_base_c':True,'l_uh':12,'efficiency':.83,
   'max_components_per_network':1,'inventory_override':{
    'front':[{'ohm':30,'count_per_stage':1}], 'tail':[{'ohm':520,'count_per_stage':1}],
    'provenance':'Regression assumption: one 30 ohm front and one 520 ohm tail unit per stage; stock unverified'}},
}
def snapshot(run):
 c=run['candidates'][0]
 return {'settings':c['settings'],'prediction':c['hybrid'],'nominal_pass':c['compliance']['nominal_pass'],
         'uncertainty_status':c['compliance']['status'],'ood':c['ood'],'verification':c['verification'],
         'search':run['search'],'score':c['score'],
         'ranked_candidates':[{'settings':x['settings'],'prediction':x['hybrid'],'score':x['score'],
                              'status':x['compliance']['status']} for x in run['candidates']]}
def main():
 folder=REPOSITORY/'artifacts/hardening'/args.label
 if (folder/'runtime.json').exists():
  raise SystemExit('This profiling record already exists; choose a new --label to preserve it.')
 folder.mkdir(parents=True,exist_ok=True)
 revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
 results={'cases':{},'source_type':'synthetic_development','scope':'Fixed requests, no laboratory observations; sequential idle-host repetitions; timings machine-dependent.',
          'source_revision':revision,'platform':platform.platform(),'python':platform.python_version(),
          'thread_environment':{key:os.environ.get(key) for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','LOKY_MAX_CPU_COUNT')}}
 for name, inputs in CASES.items():
  req=OptimizeRequest(**inputs); times=[]
  for i in range(args.repeats):
   start=time.perf_counter();run=optimize(req);times.append(time.perf_counter()-start)
  prof=cProfile.Profile();prof.enable();profiled=optimize(req);prof.disable()
  stats=pstats.Stats(prof);stats.sort_stats('cumulative')
  funcs=sorted(stats.stats.items(),key=lambda x:x[1][3],reverse=True)
  function_times=[{'function':f'{Path(k[0]).name}:{k[1]} {k[2]}','calls':v[1],'self_seconds':v[2],'cumulative_seconds':v[3]} for k,v in funcs[:35]]
  component_times=[{'function':f'{Path(k[0]).name}:{k[1]} {k[2]}','calls':v[1],'self_seconds':v[2],'cumulative_seconds':v[3]} for k,v in funcs
                   if k[2] in ('nearest_networks','simulate','infer','robustness','verify_settings','waveform_from_metrics')]
  start=time.perf_counter();encoded=json.dumps(run);serialization=time.perf_counter()-start
  start=time.perf_counter();report=report_html({**run,'id':'profiling-example','created_at':'2026-10-06T00:00:00+00:00'});report_seconds=time.perf_counter()-start
  results['cases'][name]={'inputs':req.model_dump(),'seconds':times,'cold_seconds':times[0],
    'warm_median_seconds':statistics.median(times[1:] or times),'serialization_seconds':serialization,
    'report_seconds':report_seconds,'response_bytes':len(encoded.encode()),'profile':function_times,'component_profile':component_times,**snapshot(run)}
  print(name,times,run['candidates'][0]['settings'],flush=True)
 protocol=json.loads((ROOT/'config/search_quality_cases.json').read_text(encoding='utf-8'))
 results['search_quality']=[compare(c) for c in protocol['benchmark']]
 manifest=json.loads((ROOT/'config/release_integrity.json').read_text(encoding='utf-8'))
 results['protected_hashes']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in manifest['files']}
 results['protected_hashes_match']=all(results['protected_hashes'][name]==digest for name,digest in manifest['files'].items())
 (folder/'runtime.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 print('Saved',folder/'runtime.json',flush=True)
if __name__=='__main__':main()
