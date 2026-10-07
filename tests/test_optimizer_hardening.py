"""Controlled engineering regressions; no benchmark outcomes or model fitting."""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from backend.app.data.workbook_reference import calculate
from backend.app.ml import registry as ml
from backend.app.optimization import engine
from backend.app.schemas import OptimizeRequest


def circuit_request(test_kv=1425):
    # A deliberate underdamped development case. Stock is an assumption and the
    # workbook capacitance is not the CPRI generator's capacitance.
    return OptimizeRequest(solver='circuit', model_mode='physics', test_kv=test_kv,
        l_uh=80, stage_min=8, stage_max=8, uncertainty_pct=0,
        monte_carlo_samples=8, max_components_per_network=1,
        inventory_override={'front':[{'ohm':30,'count_per_stage':1}],
            'tail':[{'ohm':30,'count_per_stage':1}],
            'provenance':'Controlled development inventory assumption; not CPRI stock'})


def test_circuit_search_solves_charge_before_rejecting_a_stage_count():
    req=circuit_request(); profile=engine.profile_for(req.profile_id)
    assert req.test_kv/(req.efficiency*8)>profile['stage_kv']
    run=engine.optimize(req); candidate=run['candidates'][0]; s=candidate['settings']
    # The passive circuit transfers enough energy to crest above initial source
    # voltage; this is not an active gain or an exemption from capacitor ratings.
    assert s['stages']==8
    assert s['charge_kv_stage']==pytest.approx(191.419731, rel=1e-6)
    assert candidate['physics']['front_us']==pytest.approx(.912652, rel=1e-5)
    assert candidate['physics']['tail_us']==pytest.approx(51.125687, rel=1e-6)
    assert candidate['compliance']['nominal_pass']
    assert candidate['ood']['trust_weight']==0
    assert s['charge_kv_stage']<profile['stage_kv']
    assert s['stored_energy_kj']<profile['energy_total_kj']
    assert s['stored_energy_kj']/s['stages']<profile['energy_stage_kj']


def test_circuit_charge_normalization_still_enforces_stage_voltage():
    # At 200 kV/stage the same network peaks below 1490 kV. Solving crest must
    # reject the required >200 kV charging value rather than clip and claim PASS.
    with pytest.raises(ValueError,match='No settings satisfy'):
        engine.optimize(circuit_request(1490))


@pytest.mark.parametrize('rating,value', [('energy_stage_kj',40.),('energy_total_kj',400.)])
def test_circuit_charge_normalization_still_enforces_each_energy_rating(monkeypatch,rating,value):
    req=circuit_request(); profile=deepcopy(engine.profile_for(req.profile_id))
    profile[rating]=value
    monkeypatch.setattr(engine,'profile_for',lambda pid:profile)
    with pytest.raises(ValueError,match='No settings satisfy'):
        engine.optimize(req)


@pytest.mark.parametrize('impulse,test_kv',[('Lightning',100.),('Lightning',1300.),
    ('Lightning',1425.),('Switching',100.),('Switching',1100.)])
def test_linear_charge_normalization_agrees_with_an_independent_full_solve(impulse,test_kv):
    if impulse=='Lightning':
        req=circuit_request(test_kv)
    else:
        req=OptimizeRequest(impulse_type=impulse,solver='circuit',model_mode='physics',test_kv=test_kv,
            stage_min=8,stage_max=8,uncertainty_pct=0,monte_carlo_samples=8,max_components_per_network=1,
            inventory_override={'front':[{'ohm':6000.,'count_per_stage':1}],
                'tail':[{'ohm':1000.,'count_per_stage':1}],
                'provenance':'Controlled Switching development inventory assumption'})
    p=engine.profile_for(req.profile_id)
    candidate=engine.optimize(req)['candidates'][0]; s=candidate['settings']
    independently_solved=engine.physics(req,p,s['stages'],s['charge_kv_stage'],s['front_r_stage'],s['tail_r_stage'])
    for metric in ('front_us','tail_us','crest_kv','t30_us','t90_us','t50_us','virtual_origin_us'):
        assert candidate['physics'][metric]==pytest.approx(independently_solved[metric],rel=1e-8,abs=1e-9)
    for metric in ('maximum_energy_ratio','maximum_energy_increase_ratio'):
        assert candidate['physics']['diagnostics'][metric]==pytest.approx(independently_solved['diagnostics'][metric],abs=1e-12)


def calculator_row(typ='Lightning',test_kv=1425.):
    req=OptimizeRequest(impulse_type=typ,test_kv=test_kv)
    ref=calculate(typ,test_kv,req.load_c_pf,req.divider_c_pf,req.stray_c_pf,req.l_uh,req.efficiency)
    return engine.ml_row(req,ref,ref)


def test_batch_support_preserves_the_frozen_tolerance_boundary():
    rows=[]; expected=[]
    for typ,test in [('Lightning',1425.),('Switching',1025.)]:
        original=calculator_row(typ,test)
        for field in ('Stages','Charge_kV_Stage','Front_R_Stage','Tail_R_Stage'):
            for factor in (.99,1.01):
                row=original.copy()
                tolerance=1e-8+1e-10*abs(row[field])
                row[field]+=factor*tolerance
                rows.append(row); expected.append(factor<1)
    np.testing.assert_array_equal(ml.calculator_setting_support(pd.DataFrame(rows)),expected)


def test_batch_calculator_cache_distinguishes_impulse_and_remains_local(monkeypatch):
    real_calculate=ml.calculate; calls=[]
    def tracked(**kwargs):
        calls.append(kwargs)
        return real_calculate(**kwargs)
    monkeypatch.setattr(ml,'calculate',tracked)
    rows=[calculator_row('Lightning'),calculator_row('Switching')]*20
    frame=pd.DataFrame(rows)
    assert ml.calculator_setting_support(frame).all()
    assert len(calls)==2
    # Another call recalculates the two environments; scope cannot persist across
    # inference or confuse nominally identical LI/SI environmental inputs.
    assert ml.calculator_setting_support(frame).all()
    assert len(calls)==4
