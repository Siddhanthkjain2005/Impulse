"""Evidence must fail closed; all waveform fixtures are generated, never lab evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.evidence import source_type, evidence_record, recommendation_evidence, laboratory_summary
from backend.app.hardware_integrity import hardware_integrity
from backend.app.optimization.engine import PROFILES, profile_for
from backend.app.schemas import OptimizeRequest
from backend.app.test_objects import catalog, validate_request
from backend.app.experiment_timeline import timeline
from scripts.benchmark_search_quality import exhaustive_catalog


@pytest.mark.parametrize('declared,embedded,expected', [
    ('measured_lab','generated_demo','generated_demo'),
    ('measured_lab','generated_stress_test','generated_demo'),
    ('measured_lab','synthetic_benchmark','synthetic_benchmark'),
    ('measured_lab','unrecognized','unknown'),
    ('generated_demo','measured_lab','generated_demo'),
    ('measured_lab',None,'measured_lab'), ('unrecognized',None,'unknown')])
def test_provenance_cannot_upgrade_generated_data(declared,embedded,expected):
    record={'source_type':declared,'provenance':{'embedded_metadata':{}}}
    if embedded:record['provenance']['embedded_metadata']['source_type']=embedded
    assert source_type(record)==expected


def test_missing_metadata_remains_unknown():
    record=evidence_record({'source_type':'measured_lab'}, {})
    assert record['captured_at'] is record['measurement_instrument'] is record['model_version'] is None
    assert not record['eligible_for_calibration'] and not record['eligible_for_external_accuracy']


def test_laboratory_empty_state_is_explicit(tmp_path):
    summary=laboratory_summary([],[],lambda *args:None,tmp_path)
    assert summary['measured_captures']==0 and summary['captures']==[]
    assert 'does not establish laboratory accuracy' in summary['empty_message']


def test_orphan_capture_excluded(tmp_path):
    def missing(*args):raise KeyError('missing saved run')
    result=laboratory_summary([{'id':'fixture','run_id':'missing','source_type':'measured_lab'}],[],missing,tmp_path)
    assert result['measured_captures']==result['excluded_captures']==1
    assert result['usable_for_calibration']==0
    assert result['captures'][0]['exclusion_reasons']


def candidate():
    return {'ood':{'trust_weight':0},'compliance':{'nominal_pass':True},
            'front_network':{'inventory_feasible':True},'tail_network':{'inventory_feasible':True}}


def test_every_evidence_level_transition():
    c=candidate(); assert recommendation_evidence(c)['level']==0
    c['ood']['trust_weight']=1; assert recommendation_evidence(c)['level']==1
    c['circuit_crosscheck']={'compliance':{'nominal_pass':True}}
    assert recommendation_evidence(c)['level']==2
    c['verification']={'all_checks_pass':True,'total':144,'passed':144,'unique_scenarios':144}
    assert recommendation_evidence(c)['level']==3
    c['calibration']={'id':'generated-fixture','source_type':'generated_stress_test'}
    assert recommendation_evidence(c)['level']==3
    c['calibration']['source_type']='measured_lab'
    assert recommendation_evidence(c)['level']==4
    assert recommendation_evidence(c,['verified-evaluation'])['level']==5
    assert recommendation_evidence(c)['level']==4


@pytest.mark.parametrize('verification',[{}, {'all_checks_pass':True,'total':0,'passed':0},
    {'all_checks_pass':True,'total':144,'passed':143}])
def test_incomplete_challenge_cannot_upgrade(verification):
    c=candidate(); c['circuit_crosscheck']={'compliance':{'nominal_pass':True}}; c['verification']=verification
    assert recommendation_evidence(c)['level']==2


def test_hardware_unknowns_and_source_conflicts():
    rows={r['parameter']:r for r in hardware_integrity(profile_for('cpri_problem_brief_profile'))['parameters']}
    assert rows['units_per_value_per_stage']['value'] is None
    assert rows['pulse_rating']['status']=='UNKNOWN'
    assert rows['stage_c_uf']['value']==.125 and rows['stage_c_uf']['status']=='SOURCE PROVIDED'
    assert 'REVIEW REQUIRED' in rows['base_c_pf']['note']
    assert all(not hardware_integrity(p)['physical_hardware_verified'] for p in PROFILES)


def test_unknown_test_reference_does_not_invent_voltage():
    review=validate_request(OptimizeRequest(test_object_id='400kv_insulator_lightning'),PROFILES[0])
    assert review['reference_kv'] is None and review['status']=='unknown'
    assert not review['confirmation_required']


def test_known_reference_mismatch_requires_confirmation():
    data=deepcopy(catalog()); obj=data['objects'][0]
    obj.update(recommended_test_level_kv=1550,source='Synthetic test fixture reference',status='source_verified')
    req=OptimizeRequest(test_object_id=obj['id'])
    assert validate_request(req,PROFILES[0],data)['confirmation_required']
    assert validate_request(req.model_copy(update={'confirm_reference_mismatch':True}),PROFILES[0],data)['confirmed']


@pytest.mark.parametrize('changes',[{'test_kv':3500},{'test_kv':2500,'profile_id':'cpri_problem_brief_profile'},
    {'test_kv':2400,'stage_max':9},{'test_object_id':'missing'},{'test_object_id':'400kv_insulator_switching'}])
def test_invalid_request_reference_or_capability_rejected(changes):
    req=OptimizeRequest(**changes)
    with pytest.raises(ValueError):validate_request(req,profile_for(req.profile_id))


def test_timeline_reads_saved_decisions_and_hashes():
    result=timeline(); entries=result['experiments']
    assert [x['status'] for x in entries]==['PROMOTED','EXPERIMENTAL','REJECTED','REJECTED','REJECTED']
    assert all(x['protocol_hash_matches'] for x in entries[1:])
    assert all(not x['hidden_test_evaluated'] for x in entries[1:])
    assert entries[1]['performance_change_pct']==pytest.approx(5.365555163706571)


def test_exact_enumerator_includes_every_two_part_tree():
    rows=exhaustive_catalog(((10.,1),(20.,1)),2)
    assert {round(r['equivalent_ohm'],8) for r in rows}=={10.,20.,30.,round(20/3,8)}
    assert all(sum(c['count_per_stage'] for c in r['components'])==r['count_per_stage'] for r in rows)


def test_benchmark_cases_are_disjoint_and_do_not_reference_hidden_test():
    data=json.loads(Path('config/search_quality_cases.json').read_text(encoding='utf-8'))
    assert not {c['id'] for c in data['development']} & {c['id'] for c in data['benchmark']}
    assert len(data['benchmark'])==4


def test_fixed_development_benchmark_reproduces_ranking():
    from scripts.benchmark_search_quality import compare
    data=json.loads(Path('config/search_quality_cases.json').read_text(encoding='utf-8'))
    first=compare(data['development'][0]); second=compare(data['development'][0])
    for key in ('same_best_candidate','bounded_winner_exhaustive_rank','objective_gap','component_count_difference','bounded_settings','exhaustive_settings'):
        assert first[key]==second[key]
    assert first['exhaustive_evaluated']>=first['bounded_evaluated']


def test_readonly_evidence_api_values():
    client=TestClient(app)
    for path in ['/api/hardware-integrity','/api/test-objects','/api/experiment-timeline','/api/search-quality','/api/laboratory-evidence']:
        response=client.get(path); assert response.status_code==200,response.text
    response=client.post('/api/test-objects/validate',json={'equipment_reference_kv':1550,'equipment_reference_source':'Operator fixture'})
    assert response.json()['confirmation_required']


def test_judge_api_uses_saved_candidate_values():
    client=TestClient(app)
    result=client.post('/api/optimize',json={'stage_min':9,'stage_max':9,'monte_carlo_samples':8})
    assert result.status_code==200,result.text
    run=result.json(); judge=client.get(f"/api/runs/{run['id']}/judge").json()
    assert judge['candidates'][0]['settings']==run['candidates'][0]['settings']
    assert judge['candidates'][0]['hybrid']==run['candidates'][0]['hybrid']
    assert judge['candidates'][0]['evidence']['level']<4
    assert 2<=len(judge['alternatives'])<=3
