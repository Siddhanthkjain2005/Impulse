"""Model agreement must change the hardware, never the challenge thresholds."""
from copy import deepcopy
import json

import numpy as np
import pytest
from pydantic import ValidationError

from backend.app.optimization.engine import optimize, robustness
from backend.app.schemas import OptimizeRequest
from backend.app.physics.circuit import simulate
from backend.app.physics.compliance import check
from backend.app.data.workbook_reference import predict
from backend.app.ml.reference_knn import ROOT


@pytest.fixture(scope='module')
def agreement_run():
    return optimize(OptimizeRequest(require_model_agreement=True))


def test_agreement_search_meets_both_checks_without_relaxing_limits(agreement_run):
    c=agreement_run['candidates'][0];s=c['settings'];req=agreement_run['inputs']
    assert c['model_agreement']['both_nominal_pass']
    assert c['model_agreement']['sampled_both_pass_pct']==100
    # Independently recompute both numeric paths at the returned hardware.
    reference=predict(s['stages'],s['charge_kv_stage'],s['front_r_stage'],s['tail_r_stage'],850,500,150,18.5,.82,3)
    circuit=simulate(s['stages'],s['charge_kv_stage'],s['front_r_stage'],s['tail_r_stage'],3,1500,18.5,.82,'Lightning',False)
    for ph in [reference,circuit]:assert check('Lightning',1425,ph)['nominal_pass']
    assert agreement_run['rules']==json.loads((ROOT/'config/compliance.json').read_text())
    for k in ['front_us','tail_us','crest_kv']:
        assert reference[k]==pytest.approx(c['hybrid'][k],rel=1e-9)
        assert circuit[k]==pytest.approx(c['circuit_crosscheck'][k],rel=1e-9)
    assert c['settings']['front_r_stage']!=50
    assert c['uncertainty']['coverage_claim'] is None
    assert c['compliance']['status']=='MARGINAL'


def test_agreement_search_keeps_component_voltage_energy_and_support_constraints(agreement_run):
    p=agreement_run['profile']
    for c in agreement_run['candidates']:
        s=c['settings'];assert s['charge_kv_stage']<=p['stage_kv']
        energy=s['stages']*.5*p['stage_c_uf']*1e-6*(s['charge_kv_stage']*1000)**2/1000
        assert energy==pytest.approx(s['stored_energy_kj'])
        assert energy<=p['energy_total_kj'] and energy/s['stages']<=p['energy_stage_kj']
        for key in ['front_network','tail_network']:
            for part in c[key]['components']:
                assert part['count_per_stage']<=part['available_per_stage']
                assert part['total_required']==s['stages']*part['count_per_stage']
        assert c['ood']['trust_weight']==0
        np.testing.assert_array_equal(c['correction'],[0,0,0])


def test_unavailable_agreement_stays_a_diagnostic_failure():
    req=OptimizeRequest(require_model_agreement=True,stage_min=9,stage_max=9,monte_carlo_samples=8,
        inventory_override={'front':[{'ohm':100,'count_per_stage':1}],
                            'tail':[{'ohm':100,'count_per_stage':1}],'provenance':'Restricted test fixture'})
    run=optimize(req)
    assert run['search']['agreement_feasible']==0
    assert all(not c['model_agreement']['both_nominal_pass'] for c in run['candidates'])
    assert any('No settings satisfying both' in w for w in run['warnings'])


def test_agreement_option_rejects_an_incompatible_solver():
    with pytest.raises(ValidationError,match='Agreement search'):
        OptimizeRequest(solver='circuit',require_model_agreement=True)


@pytest.mark.parametrize('uncertainty_pct',[.5,2,5])
def test_calibration_bias_cannot_transfer_outside_its_input_scope(agreement_run,uncertainty_pct):
    from scipy.stats import qmc
    c=deepcopy(agreement_run['candidates'][0]);s=c['settings']
    req=OptimizeRequest(require_model_agreement=True,uncertainty_pct=uncertainty_pct)
    scope={**req.model_dump(),**s,'model_version':c['model_version'],
        'generator_profile':agreement_run['profile'],'rules_version':agreement_run['rules']['version'],
        'front_topology':c['front_network']['topology'],'tail_topology':c['tail_network']['topology']}
    cal={'id':'scope-test','scope':scope,'bias':[0.,0.,100.],'source_type':'generated_stress_test'}
    c['calibration']=cal
    robustness(req,agreement_run['profile'],c,'hybrid',cal)
    samples=qmc.LatinHypercube(d=4,seed=73).random(req.monte_carlo_samples)
    # All four changed inputs must remain within 1% of the recorded trial.
    inside=np.all(np.abs((2*samples-1)*uncertainty_pct)<=1,axis=1)
    assert c['robustness']['calibrated_scenarios']==int(inside.sum())
    assert c['robustness']['outside_calibration_scope_scenarios']==int((~inside).sum())
    expected=s['stages']*s['charge_kv_stage']*req.efficiency+inside*100
    assert c['robustness']['minimum'][2]==pytest.approx(expected.min())
    assert c['robustness']['maximum'][2]==pytest.approx(expected.max())
    assert c['uncertainty']['coverage_claim'] is None


def test_v3_study_never_changes_frozen_evidence():
    from backend.app.ml.experiment_v2 import sha
    path=ROOT/'artifacts/experiments/v3'
    protocol=json.loads((path/'protocol.json').read_text());summary=json.loads((path/'summary.json').read_text())
    assert summary['hidden_test_evaluated'] is False
    assert summary['validation_evaluated'] is False
    assert summary['calibration_evaluated'] is False
    for name,digest in protocol['preserved_sha256'].items():assert sha(ROOT/name)==digest
    rows=json.loads((path/'oof_predictions.json').read_text())
    assert len(rows)==1120
    for row in rows:
        assert row['id'] not in row['train_ids']
        assert set(row['train_ids'])<=set(protocol['fit_ids'][row['type']])
