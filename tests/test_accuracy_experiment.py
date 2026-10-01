"""Protect new experiment evidence, support boundaries and opt-in serving."""
import hashlib
import json

import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.ml.experiment_v2 import basis, read_split
from backend.app.ml.reference_knn import OBSERVED, PHYSICS, RESIDUAL, ROOT
from backend.app.ml.registry import infer, registry

PATH = ROOT / 'artifacts/experiments/v2'


def test_v2_oof_is_disjoint_from_fit_and_calibration_and_v1_is_preserved():
    protocol=json.loads((PATH/'protocol.json').read_text())
    summary=json.loads((PATH/'summary.json').read_text())
    records=json.loads((PATH/'oof_predictions.json').read_text())
    assert len(records)==1120
    assert summary['hidden_test_evaluated'] is False
    assert summary['v1_preserved'] is True
    for relative,digest in protocol['preserved_v1_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest
    for typ in ['Lightning','Switching']:
        rows=[r for r in records if r['impulse_type']==typ]
        assert {r['id'] for r in rows}==set(protocol['fit_ids'][typ])
        assert len(rows)==len({r['id'] for r in rows})==560
        for row in rows:
            assert row['id'] not in row['train_ids']
            assert not set(row['train_ids']) & set(protocol['calibration_ids'][typ])
            assert np.isfinite(row['V2 search']).all()


def test_v2_feature_bases_ignore_outcomes_and_split_metadata():
    frame=read_split('Train').iloc[:8].copy()
    corrupted=frame.copy();corrupted[OBSERVED+RESIDUAL]=1e12
    corrupted['ID']=-1;corrupted['Split']='Hidden Test'
    for name in ['minimal mechanism','compact inputs','physics interactions','V1 physics features']:
        for j in range(3):
            np.testing.assert_array_equal(basis(frame,name,j),basis(corrupted,name,j))


def test_v2_serves_joint_intervals_only_for_supported_settings():
    frame=read_split('Train');bundle,_=registry()
    summary=json.loads((PATH/'summary.json').read_text())
    for typ in ['Lightning','Switching']:
        row=frame.loc[frame.ID==bundle[typ]['fit_ids'][0]].iloc[0].to_dict()
        result=infer([row],mode='experimental_v2')[0]
        assert result['experimental_model'] is True
        assert result['model_version']==summary['version']
        assert result['uncertainty']['coverage_claim']==.90
        assert 'simultaneous' in result['uncertainty']['method']
        np.testing.assert_allclose(result['uncertainty']['halfwidth'],summary['calibration'][typ]['joint_halfwidth'])
        # An intervention may still fall inside coordinate min/max ranges.
        # The source has no intervention examples, so residual is disabled.
        changed={**row,'Front_R_Stage':row['Front_R_Stage']+1}
        for mode in ['hybrid','experimental_v2']:
            fallback=infer([changed],mode=mode)[0]
            assert fallback['ood']['calculator_setting_supported'] is False
            assert fallback['ood']['trust_weight']==0
            assert fallback['uncertainty']['coverage_claim'] is None
            np.testing.assert_allclose(fallback['prediction'],[row[k] for k in PHYSICS])


def test_v2_optional_api_evidence_and_optimizer_retain_default_v1():
    client=TestClient(app)
    models=client.get('/api/models').json()
    assert models['version']=='residual-competition-v1'
    assert models['experiment_v2']['hidden_test_evaluated'] is False
    assert client.get('/api/models/'+models['experiment_v2']['version']+'/metrics').json()['hidden_test_evaluated'] is False
    response=client.post('/api/optimize',json={'model_mode':'experimental_v2','monte_carlo_samples':8})
    assert response.status_code==200,response.text
    run=response.json()
    assert run['model_version']==models['experiment_v2']['version']
    assert run['inputs']['model_mode']=='experimental_v2'
    assert any('No V2 Hidden Test' in message for message in run['warnings'])
    assert all(c['experimental_model'] for c in run['candidates'])
    assert all(np.isfinite(c['prediction']).all() for c in run['candidates'])
    report=client.get('/api/runs/'+run['id']+'/report').text
    assert 'Experimental V2 residual correction (development evidence)' in report
    assert 'No V2 Hidden Test' in report
