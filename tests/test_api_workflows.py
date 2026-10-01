"""Meaningful end-to-end API checks, with isolated temporary audit storage."""
import os
import tempfile
os.environ.setdefault('IMPULSETWIN_DB',str(__import__('pathlib').Path(tempfile.mkdtemp(prefix='impulsetwin-test-'))/'audit.sqlite3'))
os.environ.setdefault('LOKY_MAX_CPU_COUNT','4')
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture(scope='module')
def client():return TestClient(app)

@pytest.fixture(scope='module')
def run(client):
    r=client.post('/api/optimize',json={}); assert r.status_code==200,r.text
    return r.json()

def test_offline_default_ranked_and_reported(client,run):
    assert len(run['candidates'])==5
    c=run['candidates'][0]
    assert c['compliance']['nominal_pass'] and c['settings']['stages']==9
    assert c['circuit_crosscheck']['compliance']['nominal_pass'] is False
    assert c['verification']['fresh_samples']['primary_passed']==128
    assert c['verification']['passed']==0 and not c['verification']['used_for_ranking']
    assert c['waveform']['kind']=='metric_reconstruction'
    report=client.get(f"/api/runs/{run['id']}/report")
    assert report.status_code==200 and 'engineer verification' in report.text
    assert 'Post-ranking settings challenge' in report.text
    assert client.get(f"/api/runs/{run['id']}").json()['model_version']==run['model_version']
    assert client.get('/api/source-status').json()['published_metrics_parity'].startswith('UNRESOLVED')

def test_switching_constructible_but_ood(client):
    r=client.post('/api/optimize',json={'impulse_type':'Switching','test_kv':1025,'load_c_pf':1240,'divider_c_pf':740,'stray_c_pf':320})
    assert r.status_code==200,r.text
    c=r.json()['candidates'][0]
    assert c['compliance']['nominal_pass'] and c['ood']['trust_weight']==0
    assert c['settings']['front_r_stage']<=5740
    assert c['uncertainty']['coverage_claim'] is None
    for n in [c['front_network'],c['tail_network']]:
        assert all(i['count_per_stage']<=i['available_per_stage'] for i in n['components'])

@pytest.mark.parametrize('body',[
    {'test_kv':3500}, {'test_kv':-100},{'test_kv':2800,'profile_id':'cpri_problem_brief_profile'},
    {'efficiency':1.2},{'stage_min':12,'stage_max':5},{'profile_id':'briefing_3mv_profile'},
    {'profile_id':'cpri_problem_brief_profile'},
    {'inventory_override':{'front':[],'tail':[],'provenance':'empty test inventory'}},
    {'equipment_reference_kv':1550,'equipment_reference_source':'user-provided test reference'}])
def test_reject_bad_inputs(client,body):
    assert client.post('/api/optimize',json=body).status_code==422

def test_hardware_valid_ood_fallback(client):
    response=client.post('/api/optimize',json={'test_kv':300})
    assert response.status_code==200,response.text
    for c in response.json()['candidates']:
        assert c['ood']['trust_weight']==0 and c['correction']==[0,0,0]
        assert c['uncertainty']['coverage_claim'] is None

def test_trial_calibration_and_raw_provenance(client,run):
    sample=client.get(f"/api/runs/{run['id']}/demo-waveform")
    r=client.post('/api/trials/upload',data={'run_id':run['id'],'source_type':'measured_lab'},files={'file':('demo.csv',sample.content,'text/csv')})
    assert r.status_code==200,r.text
    trial=r.json(); assert trial['source_type']=='generated_stress_test'
    assert abs(trial['measured']['front_us']/trial['predicted']['front_us']-1.045)<.002
    cal=client.post(f"/api/trials/{trial['id']}/calibrate").json()
    assert cal['production_model_changed'] is False
    new=client.post('/api/optimize',json={'calibration_id':cal['id']}).json()
    assert new['calibration_review']['applied'] is True
    assert new['calibration_review']['source_type']=='generated_stress_test'
    other=client.post('/api/optimize',json={'calibration_id':cal['id'],'layout_id':'another-layout'}).json()
    assert other['calibration_review']['applied'] is False

def test_csv_unit_mapping_negative_polarity(client,run):
    import numpy as np
    from backend.app.physics.waveform_metrics import waveform_from_metrics
    w=waveform_from_metrics(1.2,50,1425)
    content='seconds,volts\n'+'\n'.join(f'{t/1e6},{-v*1000}' for t,v in zip(w['time_us'],w['voltage_kv']))
    response=client.post('/api/trials/upload',data={'run_id':run['id'],'time_column':'seconds','voltage_column':'volts','time_unit':'s','voltage_unit':'V'},files={'file':('negative.csv',content,'text/csv')})
    assert response.status_code==200,response.text
    m=response.json()['measured']
    assert m['polarity']==-1
    np.testing.assert_allclose([m['front_us'],m['tail_us'],m['crest_kv']],[1.2,50,1425],rtol=.002)

def test_invalid_csv_and_missing_runs(client,run):
    content='time_us,voltage_kv\n'+'\n'.join('1,10' for _ in range(15))
    r=client.post('/api/trials/upload',data={'run_id':run['id']},files={'file':('bad.csv',content,'text/csv')})
    assert r.status_code==422
    assert client.get('/api/runs/does-not-exist').status_code==404

def test_simulation_validation(client):
    for settings in [dict(stages=2.5,charge_kv_stage=100,front_r_stage=50,tail_r_stage=25),dict(stages=9,charge_kv_stage=100,front_r_stage=-50,tail_r_stage=25)]:
        assert client.post('/api/simulate',json={'inputs':{},'settings':settings}).status_code==422

def test_reference_and_model_registry(client):
    ref=client.get('/api/reference').json()
    assert ref['golden_case_verified'] and not ref['published_validation_table_parity']
    assert abs(ref['hybrid']['crest_kv']-1432.94658495185)<1e-9
    m=client.get('/api/models').json()
    assert set(m['validation'])=={'Lightning','Switching'}
    assert m['hidden_test']['frozen_config_sha256']==m['frozen_config_sha256']

@pytest.mark.parametrize('body',[{'load_c_pf':.001,'divider_c_pf':0,'stray_c_pf':0},
    {'load_c_pf':100000,'divider_c_pf':100000,'stray_c_pf':100000},{'l_uh':10000}])
def test_extreme_allowed_inputs_return_finite_diagnostic_failures(client,body):
    import math
    r=client.post('/api/optimize',json=body)
    assert r.status_code==200,r.text
    for c in r.json()['candidates']:
        assert not c['compliance']['nominal_pass']
        assert all(math.isfinite(v) and v>0 for v in c['prediction'])
