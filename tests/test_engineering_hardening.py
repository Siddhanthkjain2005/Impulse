"""Capability checks must use the selected physical path and supplied ratings."""
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from backend.app import main
from backend.app.hardware_integrity import hardware_integrity
from backend.app.optimization.engine import profile_for
from backend.app.schemas import OptimizeRequest
from backend.app.test_objects import validate_request


def test_circuit_request_is_not_rejected_by_workbook_ideal_crest_limit():
    values={'stage_min':8,'stage_max':8,'l_uh':80}
    with pytest.raises(ValueError,match='charging capability'):
        validate_request(OptimizeRequest(**values),profile_for('workbook_reference_profile'))
    result=validate_request(OptimizeRequest(**values,solver='circuit'),profile_for('workbook_reference_profile'))
    assert result['reference_kv'] is None
    # The source's declared maximum test voltage remains a hard limit.
    with pytest.raises(ValueError,match='profile capability'):
        validate_request(OptimizeRequest(test_kv=3001,solver='circuit'),profile_for('workbook_reference_profile'))


def test_cpri_physical_references_and_assumed_operating_minima():
    profile=profile_for('cpri_problem_brief_profile')
    rows={r['parameter']:r for r in hardware_integrity(profile)['parameters']}
    assert rows['voltage_min_kv']['status']==rows['min_stages']['status']=='ASSUMED'
    assert rows['stage_c_uf']['status']=='SOURCE PROVIDED'
    assert rows['units_per_value_per_stage']['status']=='UNKNOWN'
    energy=.5*profile['stage_c_uf']*1e-6*(profile['stage_kv']*1000)**2/1000
    assert energy==pytest.approx(2.5)
    assert profile['energy_stage_kj']==pytest.approx(energy)
    assert profile['energy_total_kj']==pytest.approx(12*energy)


@pytest.mark.parametrize('stage_rating,total_rating',[(1.,30.),(2.5,5.)])
def test_direct_simulation_enforces_supplied_energy_ratings(monkeypatch,stage_rating,total_rating):
    # A source may declare a rating below 1/2 CV^2 at maximum charging voltage.
    # Check the actual rating rather than deriving permission from voltage alone.
    profile=deepcopy(profile_for('cpri_problem_brief_profile'))
    profile.update(energy_stage_kj=stage_rating,energy_total_kj=total_rating)
    monkeypatch.setattr(main,'profile_for',lambda _:profile)
    response=TestClient(main.app).post('/api/simulate',json={
        'inputs':{'profile_id':profile['id'],'solver':'circuit'},
        'settings':{'stages':11,'charge_kv_stage':180,'front_r_stage':30,'tail_r_stage':520}})
    assert response.status_code==422
    assert 'energy rating' in response.json()['detail']
