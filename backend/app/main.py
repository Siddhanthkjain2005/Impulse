from pathlib import Path
from datetime import datetime,timezone
import csv
import io
import json
import hashlib
import uuid
import html
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from .schemas import OptimizeRequest,SimulationRequest,ComplianceRequest
from .optimization.engine import optimize, profile_for, PROFILES, physics
from .physics.waveform_metrics import analyze,waveform_from_metrics
from .physics.compliance import check,RULES
from .data.workbook_reference import calculate
from .ml.reference_knn import WorkbookKNN
from .ml.registry import registry
from . import storage
from .reports import report_html

ROOT=Path(__file__).resolve().parents[2]
app=FastAPI(title='ImpulseTwin AI',version='1.0.0',description='Offline physics-guided impulse-generator decision support. No hardware control.',docs_url=None,redoc_url=None)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:3000','http://127.0.0.1:3000','http://localhost:8000','http://127.0.0.1:8000'],allow_methods=['GET','POST'],allow_headers=['*'])

def saved(id,kind):
    try:return storage.get(id,kind)
    except KeyError:raise HTTPException(404,f'{kind} not found')

@app.get('/api/health')
def health():return {'status':'online','version':'1.0.0','mode':'local / offline capable','hardware_control':False}

@app.get('/docs',response_class=HTMLResponse,include_in_schema=False)
def offline_api_docs():
    schema=app.openapi()
    rows=''.join(f'<tr><td><b>{html.escape(method.upper())}</b></td><td><code>{html.escape(path)}</code></td><td>{html.escape(info.get("summary",""))}</td></tr>' for path,methods in schema['paths'].items() for method,info in methods.items())
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>ImpulseTwin API documentation</title><style>body{font:15px system-ui;max-width:1100px;margin:50px auto;color:#16303f;padding:20px}table{width:100%;border-collapse:collapse}td{padding:12px;border-bottom:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f8;padding:20px;font-size:12px}a{color:#087f8c}</style><h1>ImpulseTwin AI API</h1><p>Local API reference. All content on this page is available offline.</p><p><a href="/">Open engineering workspace</a> · <a href="/openapi.json">OpenAPI JSON</a></p><table>'+rows+'</table><h2>Request schemas</h2><pre>'+html.escape(json.dumps(schema.get('components',{}).get('schemas',{}),indent=2))+'</pre></html>'

@app.get('/api/source-status')
def source_status():
    manifest=json.loads((ROOT/'data/processed/manifest.json').read_text())
    workbook=ROOT/'data/source/Hybrid_Physics_ML_Impulse_Generator_Optimiser.xlsx'
    dataset=ROOT/'data/processed/synthetic_dataset.csv'
    _,meta=registry()
    return {'sources':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (ROOT/'data/source').glob('*')],
        'manifest':manifest,'source_hash_matches_snapshot':hashlib.sha256(workbook.read_bytes()).hexdigest()==manifest['source_sha256'],
        'dataset_hash_matches_frozen_model':hashlib.sha256(dataset.read_bytes()).hexdigest()==meta['dataset_sha256'],
        'formula_parity':'golden case and all 1400 cached helper distances/weights verified',
        'published_metrics_parity':'UNRESOLVED: hardcoded table differs from formula-based Validation evaluation',
        'lab_validation':'pending actual measured data','source_reconciliation':'/api/documents/source_reconciliation',
        'standards':RULES,'qa':json.loads((ROOT/'artifacts/qa_summary.json').read_text()) if (ROOT/'artifacts/qa_summary.json').exists() else None}

@app.get('/api/generator-profiles')
def profiles():return PROFILES

@app.get('/api/generator-profiles/{id}')
def profile(id:str):
    try:return profile_for(id)
    except ValueError as e:raise HTTPException(404,str(e))

@app.get('/api/reference')
def reference(impulse_type:str='Lightning'):
    if impulse_type not in ['Lightning','Switching']:raise HTTPException(422,'Unknown impulse type')
    c=calculate(impulse_type=impulse_type)
    q=pd.DataFrame([{'Impulse_Type':impulse_type,'Test_kV':1425,'Load_C_pF':850,'Divider_C_pF':500,'Stray_C_pF':150,'L_uH':18.5,'Efficiency':.82,'Front_R_Stage':c['front_r_stage'],'Tail_R_Stage':c['tail_r_stage']}])
    res,neighbors=WorkbookKNN().predict(q,True); values=np.array([c['front_us'],c['tail_us'],c['crest_kv']])+res[0]
    return {'physics':c,'hybrid':dict(zip(['front_us','tail_us','crest_kv'],values.tolist())),
        'correction':res[0].tolist(),'neighbors':neighbors[0],'kind':'exact workbook reference calculator; inventory unchecked',
        'golden_case_verified':impulse_type=='Lightning','published_validation_table_parity':False}

@app.post('/api/optimize')
def run_optimize(req:OptimizeRequest):
    try:
        cal=saved(req.calibration_id,'calibration') if req.calibration_id else None
        result=optimize(req,cal)
    except ValueError as e:raise HTTPException(422,str(e))
    id=uuid.uuid4().hex[:12]; result['run_id']=id
    return storage.put('run',id,result)

@app.post('/api/simulate')
def run_simulate(body:SimulationRequest):
    try:
        req=body.inputs; p=profile_for(req.profile_id); s=body.settings.model_dump()
        n=s['stages']; q=s['charge_kv_stage']
        if not p['enabled'] or not p['min_stages']<=n<=p['max_stages'] or not 0<q<=p['stage_kv']:raise ValueError('Settings exceed profile ratings.')
        return physics(req,p,n,q,s['front_r_stage'],s['tail_r_stage'],True)
    except (KeyError,TypeError,ValueError) as e:raise HTTPException(422,str(e))

@app.post('/api/compliance/check')
def run_compliance(body:ComplianceRequest):
    try:return {**check(body.impulse_type,body.test_kv,body.prediction.model_dump()),'scope':'Waveform-only check. Hardware feasibility must be evaluated by the optimizer.'}
    except (KeyError,ValueError,TypeError) as e:raise HTTPException(422,str(e))

@app.get('/api/models')
def models():
    _,meta=registry()
    result={**meta,'hidden_test':json.loads((ROOT/'artifacts/models/hidden_test_evaluation.json').read_text())}
    experiment=ROOT/'artifacts/experiments/v2/summary.json'
    if experiment.exists():
        result['experiment_v2']=json.loads(experiment.read_text())
    return result

@app.get('/api/models/{id}/metrics')
def model_metrics(id:str):
    result=models()
    if id==result.get('experiment_v2',{}).get('version'):return result['experiment_v2']
    if id!=result['version']:raise HTTPException(404,'Unknown model version')
    return result

@app.post('/api/explain')
def explain(body:dict):
    run=saved(body.get('run_id',''),'run'); candidate=next((c for c in run['candidates'] if c['id']==body.get('candidate_id')),run['candidates'][0])
    return {k:candidate[k] for k in ['explanation','score_breakdown','physics','correction','hybrid','ood','robustness','front_network','tail_network']}

@app.get('/api/runs')
def runs():
    return [{'id':r['id'],'created_at':r['created_at'],'profile':r['profile']['name'],'inputs':r['inputs'],'status':r['candidates'][0]['compliance']['status'],'model_version':r['model_version']} for r in storage.list_records('run')]

@app.get('/api/runs/{id}')
def get_run(id:str):return saved(id,'run')

@app.get('/api/runs/{id}/report',response_class=HTMLResponse)
def report(id:str):return HTMLResponse(report_html(saved(id,'run')),headers={'Content-Disposition':f'inline; filename="ImpulseTwin-{id}.html"'})

@app.get('/api/runs/{id}/json')
def run_json(id:str):return Response(json.dumps(saved(id,'run'),indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="ImpulseTwin-{id}.json"'})

@app.get('/api/runs/{id}/demo-waveform')
def demo_waveform(id:str):
    run=saved(id,'run'); c=run['candidates'][0]; pred=c['prediction']
    wave=waveform_from_metrics(pred[0]*1.045,pred[1]*.97,pred[2]*.985,run['inputs']['impulse_type'])
    stream=io.StringIO(); stream.write('# source_type=generated_stress_test; demo only, not measured lab data\n')
    writer=csv.writer(stream); writer.writerow(['time_us','voltage_kv']); writer.writerows(zip(wave['time_us'],wave['voltage_kv']))
    return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="generated_stress_test_trial.csv"'})

@app.post('/api/trials/upload')
async def upload_trial(file:UploadFile=File(...),run_id:str=Form(...),candidate_id:str=Form(''),
    time_column:str=Form('time_us'),voltage_column:str=Form('voltage_kv'),time_unit:str=Form('us'),
    voltage_unit:str=Form('kV'),baseline_kv:float=Form(0),source_type:str=Form('generated_stress_test'),time_origin_us:float=Form(0)):
    run=saved(run_id,'run'); candidate=next((c for c in run['candidates'] if c['id']==candidate_id),run['candidates'][0])
    if source_type not in ['generated_stress_test','measured_lab']:raise HTTPException(422,'Source type must identify demo or measured laboratory data.')
    content=await file.read(5_000_001)
    if len(content)>5_000_000:raise HTTPException(413,'CSV exceeds the 5 MB upload limit.')
    try:
        text=content.decode('utf-8-sig')
        if 'source_type=generated_stress_test' in text[:1000]:source_type='generated_stress_test'
        df=pd.read_csv(io.StringIO(text),comment='#')
        ts={'us':1,'µs':1,'ms':1000,'s':1e6,'ns':.001}[time_unit]
        vs={'kV':1,'V':.001,'MV':1000}[voltage_unit]
        t=df[time_column].to_numpy(float)*ts; v=df[voltage_column].to_numpy(float)*vs
        measured=analyze(t,v,run['inputs']['impulse_type'],baseline_kv,time_origin_us)
    except (UnicodeError,ValueError,KeyError,TypeError) as e:raise HTTPException(422,f'CSV validation failed: {e}')
    id=uuid.uuid4().hex[:12]; path=ROOT/'artifacts/trials'/f'{id}.csv'; path.parent.mkdir(exist_ok=True,parents=True); path.write_bytes(content)
    bias=[measured[k]-candidate['hybrid'][k] for k in ['front_us','tail_us','crest_kv']]
    result={'run_id':run_id,'candidate_id':candidate['id'],'source_type':source_type,'original_filename':file.filename,
        'raw_sha256':hashlib.sha256(content).hexdigest(),'raw_path':str(path.relative_to(ROOT)),
        'processing':{'time_column':time_column,'voltage_column':voltage_column,'time_unit':time_unit,'voltage_unit':voltage_unit,'baseline_kv':baseline_kv,'time_origin_us':time_origin_us,'polarity':measured['polarity'],'steps':['Units converted without changing raw file','Explicit baseline subtracted only for analysis','Polarity normalized for metric extraction','Linear interpolation at crossings']},
        'measured':measured,'predicted':candidate['hybrid'],'physics':candidate['physics'],'bias':bias,
        'waveform':{'time_us':t.tolist(),'voltage_kv':v.tolist(),'kind':source_type},
        'compliance':check(run['inputs']['impulse_type'],run['inputs']['test_kv'],measured)}
    return storage.put('trial',id,result)

@app.get('/api/trials')
def trials():return storage.list_records('trial',50)

@app.post('/api/trials/{id}/calibrate')
def calibrate(id:str):
    trial=saved(id,'trial'); run=saved(trial['run_id'],'run'); c=next(c for c in run['candidates'] if c['id']==trial['candidate_id'])
    if any(abs(b)>abs(p)*.3 for b,p in zip(trial['bias'],c['prediction'])):
        raise HTTPException(422,'The shot differs by more than 30%. Review units, setup and waveform before local calibration.')
    scope={**{k:run['inputs'][k] for k in ['profile_id','impulse_type','layout_id','solver','model_mode','include_base_c','test_kv','load_c_pf','divider_c_pf','stray_c_pf','l_uh','efficiency']},
        'model_version':run['model_version'],
        'generator_profile':run['profile'],'rules_version':run['rules']['version'],
        'front_topology':c['front_network']['topology'],'tail_topology':c['tail_network']['topology'],
        **{k:c['settings'][k] for k in ['stages','front_r_stage','tail_r_stage','charge_kv_stage']}}
    return storage.put('calibration',uuid.uuid4().hex[:12],{'trial_id':id,'source_type':trial['source_type'],
        'bias':trial['bias'],'scope':scope,'production_model_changed':False,
        'retraining_queue':'Stored for later engineer-reviewed retraining; no automatic training',
        'limitation':'Applies only to same profile, layout, solver and hardware settings with inputs within 1%. Reduced-voltage transfer to a higher-voltage shot is not inferred.'})

@app.get('/api/documents/{name}')
def document(name:str):
    paths={'source_reconciliation':ROOT/'docs/source_reconciliation.md','data_audit':ROOT/'reports/data_audit.html','assumptions':ROOT/'docs/assumptions.md','accuracy_v2_results':ROOT/'docs/accuracy_v2_results.md'}
    p=paths.get(name)
    if p is None or not p.exists():raise HTTPException(404,'Document not found')
    return FileResponse(p,media_type='text/html' if p.suffix=='.html' else 'text/plain')

if (ROOT/'frontend/out').exists():app.mount('/',StaticFiles(directory=ROOT/'frontend/out',html=True),name='frontend')
