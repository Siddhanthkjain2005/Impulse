"""Trial attribution, repeated-shot feedback and acquisition-error regressions."""
import io
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
os.environ.setdefault('IMPULSETWIN_DB',str(Path(tempfile.mkdtemp(prefix='impulsetwin-feedback-tests-'))/'audit.sqlite3'))
from backend.app import main, storage
from backend.app.optimization.engine import optimize
from backend.app.schemas import OptimizeRequest
from backend.app.physics.waveform_metrics import analyze, waveform_from_metrics
from backend.app.trial_quality import assess_waveform


@pytest.fixture
def trial_store(tmp_path, monkeypatch):
    database=create_engine('sqlite:///'+str(tmp_path/'trials.sqlite3'),connect_args={'check_same_thread':False})
    storage.metadata.create_all(database)
    monkeypatch.setattr(storage,'engine',database)
    monkeypatch.setattr(main,'ROOT',tmp_path)
    run=json.loads((Path(__file__).resolve().parents[1]/'data/demo/lightning_reference_run.json').read_text())
    yield TestClient(main.app),run
    database.dispose()


def csv_wave(values, coarse=False, clipped=False):
    wave=waveform_from_metrics(*values)
    t=np.array(wave['time_us']);v=np.array(wave['voltage_kv'])
    if coarse:
        ix=np.linspace(0,len(t)-1,11,dtype=int);t=t[ix];v=v[ix]
    if clipped:v=np.minimum(v,.95*max(v))
    return 'time_us,voltage_kv\n'+'\n'.join(f'{a:.15g},{b:.15g}' for a,b in zip(t,v))


def upload(client,run,content,candidate=None):
    return client.post('/api/trials/upload',data={'run_id':run['id'],'candidate_id':candidate or run['candidates'][0]['id']},files={'file':('generated-test.csv',content,'text/csv')})


@pytest.mark.parametrize('measurement_factor',[1.05,1.07])
def test_second_calibration_preserves_prior_bias_and_reapplies_to_original_model(trial_store,measurement_factor):
    client,run=trial_store;c=run['candidates'][0]
    base=np.array(c['prediction']); prior=base*.05
    c['prediction']=(base+prior).tolist();c['hybrid']=dict(zip(['front_us','tail_us','crest_kv'],c['prediction']))
    c['calibration']={'id':'previous-shot','bias':prior.tolist(),'source_type':'generated_stress_test'}
    run=storage.put('run','repeated-shot',run)
    response=upload(client,run,csv_wave(base*measurement_factor));assert response.status_code==200,response.text
    trial=response.json();assert trial['quality']['calibration_allowed']
    np.testing.assert_allclose(trial['calibration_bias'],np.array(trial['bias'])+prior,atol=1e-10)
    cal=client.post(f"/api/trials/{trial['id']}/calibrate");assert cal.status_code==200,cal.text
    calibration=cal.json();assert calibration['calibration_lineage']['parent_calibration_id']=='previous-shot'
    np.testing.assert_allclose(calibration['bias'],base*(measurement_factor-1),rtol=.002)
    corrected=optimize(OptimizeRequest(**run['inputs']),calibration)['calibration_review']
    assert corrected['applied']
    np.testing.assert_allclose(list(corrected['corrected_prediction'].values()),[trial['measured'][k] for k in ['front_us','tail_us','crest_kv']],rtol=1e-8)


def test_demo_export_uses_selected_candidate_and_rejects_invalid_ids(trial_store):
    client,run=trial_store;c=deepcopy(run['candidates'][0]);c['id']='other';c['prediction']=[1.3,55,1200]
    run['candidates'].append(c);run=storage.put('run','candidate-selection',run)
    r=client.get(f"/api/runs/{run['id']}/demo-waveform?candidate_id=other");assert r.status_code==200
    assert 'candidate_id=other' in r.text
    df=pd.read_csv(io.StringIO(r.text),comment='#');m=analyze(df.time_us,df.voltage_kv)
    np.testing.assert_allclose([m[k] for k in ['front_us','tail_us','crest_kv']],[1.3*1.045,55*.97,1200*.985],rtol=.002)
    assert client.get(f"/api/runs/{run['id']}/demo-waveform?candidate_id=missing").status_code==422
    assert upload(client,run,r.text,candidate='missing').status_code==422
    assert not storage.list_records('trial')


@pytest.mark.parametrize('problem',['coarse','clipped'])
def test_suspect_capture_is_retained_but_cannot_create_calibration(trial_store,problem):
    client,run=trial_store;run=storage.put('run','capture-review',run)
    raw=csv_wave(run['candidates'][0]['prediction'],coarse=problem=='coarse',clipped=problem=='clipped')
    response=upload(client,run,raw);assert response.status_code==200,response.text
    trial=response.json();assert not trial['quality']['calibration_allowed']
    assert (main.ROOT/trial['raw_path']).read_bytes()==raw.encode()
    response=client.post(f"/api/trials/{trial['id']}/calibrate")
    assert response.status_code==422 and 'Capture review required' in response.text
    assert not storage.list_records('calibration')


def test_total_correction_limit_cannot_be_bypassed_by_small_followup_residual(trial_store):
    client,run=trial_store;c=run['candidates'][0];base=np.array(c['prediction']);prior=base*.25
    c['prediction']=(base+prior).tolist();c['hybrid']=dict(zip(['front_us','tail_us','crest_kv'],c['prediction']))
    c['calibration']={'id':'large-prior','bias':prior.tolist(),'source_type':'generated_stress_test'}
    run=storage.put('run','large-total',run)
    response=upload(client,run,csv_wave(base*1.35));assert response.status_code==200
    trial=response.json();assert trial['quality']['calibration_allowed']
    response=client.post(f"/api/trials/{trial['id']}/calibrate")
    assert response.status_code==422 and 'total correction' in response.text


def test_legacy_trial_quality_is_rechecked_and_missing_samples_block_calibration(trial_store):
    client,run=trial_store;run=storage.put('run','legacy-trial',run)
    response=upload(client,run,csv_wave(run['candidates'][0]['prediction']));assert response.status_code==200
    legacy=response.json();legacy.pop('quality');legacy.pop('calibration_lineage');legacy.pop('calibration_bias')
    legacy=storage.put('trial','legacy-good',legacy)
    assert client.post('/api/trials/legacy-good/calibrate').status_code==200
    legacy.pop('waveform');storage.put('trial','legacy-missing',legacy)
    response=client.post('/api/trials/legacy-missing/calibrate')
    assert response.status_code==422 and 'Re-upload' in response.text


def test_acquisition_review_handles_negative_polarity_and_explicit_baseline():
    wave=waveform_from_metrics(1.2,50,1000);raw=7-np.array(wave['voltage_kv']);original=raw.copy()
    m=analyze(wave['time_us'],raw,baseline_kv=7)
    quality=assess_waveform(wave['time_us'],raw,m)
    assert quality['calibration_allowed'] and quality['metrics']['rising_intervals_30_90']>=4
    np.testing.assert_array_equal(raw,original)


@pytest.mark.parametrize('mismatch',['run_id','candidate_id','time_unit','voltage_unit'])
def test_tagged_demo_cannot_be_uploaded_against_wrong_setup_or_units(trial_store,mismatch):
    client,run=trial_store;run=storage.put('run','tagged-source',run)
    export=client.get(f"/api/runs/{run['id']}/demo-waveform").text
    if mismatch=='run_id': export=export.replace('run_id=tagged-source','run_id=another-run')
    elif mismatch=='candidate_id': export=export.replace('candidate_id='+run['candidates'][0]['id'],'candidate_id=another-candidate')
    elif mismatch=='time_unit': export=export.replace('time_unit=us','time_unit=ms')
    else: export=export.replace('voltage_unit=kV','voltage_unit=V')
    response=upload(client,run,export)
    assert response.status_code==422 and mismatch in response.text
    assert not storage.list_records('trial')
    assert not (main.ROOT/'artifacts/trials').exists()


def test_conflicting_provenance_comments_are_rejected(trial_store):
    client,run=trial_store;run=storage.put('run','tag-conflict',run)
    export=client.get(f"/api/runs/{run['id']}/demo-waveform").text
    response=upload(client,run,'# run_id=contradictory\n'+export)
    assert response.status_code==422 and 'conflicting run_id' in response.text


def test_negative_delayed_switching_plot_matches_extracted_metrics_without_changing_raw_capture(trial_store):
    import hashlib
    client,run=trial_store;run['inputs']['impulse_type']='Switching'
    run=storage.put('run','negative-delayed',run)
    wave=waveform_from_metrics(250,2500,1000,'Switching')
    t=np.array(wave['time_us']);v=np.array(wave['voltage_kv'])
    content='seconds,volts\n'+'\n'.join(f'{a},{b}' for a,b in zip((t+700)/1e6,(7-v)*1000))
    response=client.post('/api/trials/upload',data={'run_id':run['id'],'time_column':'seconds','voltage_column':'volts','time_unit':'s','voltage_unit':'V','baseline_kv':7,'time_origin_us':700},files={'file':('negative-delayed.csv',content,'text/csv')})
    assert response.status_code==200,response.text
    trial=response.json();comparison=trial['comparison_waveform'];raw=trial['waveform']
    np.testing.assert_allclose(comparison['time_us'],t,atol=1e-10)
    np.testing.assert_allclose(comparison['voltage_kv'],v,atol=1e-10)
    np.testing.assert_allclose(raw['time_us'],t+700,atol=1e-10)
    np.testing.assert_allclose(raw['voltage_kv'],7-v,atol=1e-10)
    np.testing.assert_allclose([trial['measured'][k] for k in ['front_us','tail_us','crest_kv']],[250,2500,1000],rtol=.001)
    assert trial['measured']['polarity']==-1 and trial['quality']['calibration_allowed']
    assert trial['raw_sha256']==hashlib.sha256(content.encode()).hexdigest()
    assert (main.ROOT/trial['raw_path']).read_bytes()==content.encode()
