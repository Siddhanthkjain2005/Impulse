"""Saved-plan changes and conservative selection use isolated fixtures."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

os.environ.setdefault('IMPULSETWIN_DB', str(Path(tempfile.mkdtemp(prefix='impulsetwin-transition-tests-')) / 'audit.sqlite3'))
from backend.app import main, storage
from backend.app.setup_transition import plan_transition


@pytest.fixture
def runs():
    source = json.loads((Path(__file__).resolve().parents[1] / 'data/demo/lightning_reference_run.json').read_text())
    before = deepcopy(source); before['id'] = 'baseline'
    after = deepcopy(source); after['id'] = 'target'
    for run in [before, after]:
        run['candidates'] = run['candidates'][:1]
        c = run['candidates'][0]; c['rank'] = 1
        c['circuit_crosscheck'] = {'compliance': {'nominal_pass': True}}
        c['verification'] = {'all_checks_pass': True, 'passed': 144, 'total': 144}
    return before, after


def network(c, name, parts, ohm, topology):
    n = c['settings']['stages']; c['settings'][f'{name}_r_stage'] = ohm
    c[f'{name}_network'] = {'equivalent_ohm': ohm, 'topology': topology,
                           'inventory_feasible': True, 'count_per_stage': sum(parts.values()),
                           'total_components': sum(parts.values()) * n,
                           'components': [{'ohm': r, 'count_per_stage': count, 'total_required': count * n,
                                           'available_per_stage': 4} for r, count in parts.items()]}


def stage_count(c, n):
    c['settings']['stages'] = n
    for name in ['front', 'tail']:
        net = c[f'{name}_network']; net['total_components'] = net['count_per_stage'] * n
        for p in net['components']:p['total_required'] = p['count_per_stage'] * n


def test_charge_only_option_is_closest_without_reordering_or_using_challenge(runs):
    before, after = runs; original = deepcopy(after)
    rewired = after['candidates'][0]; rewired['id'] = 'rewired'
    network(rewired, 'front', {20: 2}, 40, '2×20Ω')
    charge_only = deepcopy(before['candidates'][0]); charge_only['id'] = 'charge-only'; charge_only['rank'] = 2
    charge_only['settings']['charge_kv_stage'] += 1
    charge_only['verification'] = {'all_checks_pass': False, 'passed': 0, 'total': 144}
    after['candidates'].append(charge_only); frozen = deepcopy(after)
    plan = plan_transition(before, before['candidates'][0]['id'], after)
    assert plan['closest_nominal_candidate_id'] == 'charge-only'
    assert [o['candidate_id'] for o in plan['options']] == ['rewired', 'charge-only']
    assert plan['options'][1]['changed_network_families'] == 0
    assert plan['options'][1]['shared_stage_part_changes'] == 0
    assert 'challenge fails' in plan['review']
    assert plan['postranking_checks_used_for_selection'] is False
    assert after == frozen and before['candidates'][0]['settings'] == original['candidates'][0]['settings']


def test_parts_on_shared_new_and_deactivated_stages_are_separate(runs):
    before, after = runs; c = after['candidates'][0]
    stage_count(c, 10); network(c, 'tail', {10: 1, 15: 1}, 25, '10Ω + 15Ω')
    option = plan_transition(before, before['candidates'][0]['id'], after)['options'][0]
    front, tail = option['networks']['front'], option['networks']['tail']
    assert front['retained_on_shared_stages'] == 9 and front['required_on_newly_active_stages'] == 1
    assert tail['added_on_shared_stages'] == 18 and tail['removed_from_shared_stages'] == 9
    assert tail['required_on_newly_active_stages'] == 2
    assert option['active_stages_added'] == 1 and option['shared_stage_part_changes'] == 27
    after = deepcopy(before); stage_count(after['candidates'][0], 8)
    option = plan_transition(before, before['candidates'][0]['id'], after)['options'][0]
    assert option['active_stages_deactivated'] == 1 and option['shared_stage_part_changes'] == 0
    assert option['networks']['front']['present_on_deactivated_stages'] == 1


def test_wiring_change_is_not_hidden_by_identical_part_counts(runs):
    before, after = runs
    network(before['candidates'][0], 'front', {20: 1, 30: 1}, 50, '20Ω + 30Ω')
    network(after['candidates'][0], 'front', {20: 1, 30: 1}, 12, '20Ω ∥ 30Ω')
    option = plan_transition(before, before['candidates'][0]['id'], after)['options'][0]
    assert option['shared_stage_part_changes'] == 0
    assert option['changed_network_families'] == 1
    assert option['networks']['front']['shared_stage_banks_to_review'] == 9


@pytest.mark.parametrize('problem', ['circuit_fail', 'missing_circuit', 'missing_stock', 'rating_fail', 'hardware_fail'])
def test_failing_or_unknown_checks_do_not_become_closest_option(runs, problem):
    before, after = runs; c = after['candidates'][0]
    if problem == 'circuit_fail':c['circuit_crosscheck']['compliance']['nominal_pass'] = False
    elif problem == 'missing_circuit':c['circuit_crosscheck'] = None
    elif problem == 'missing_stock':c['front_network']['components'][0].pop('available_per_stage')
    elif problem == 'rating_fail':c['settings']['charge_kv_stage'] = 250
    else:c['compliance']['hardware_pass'] = False
    plan = plan_transition(before, before['candidates'][0]['id'], after)
    assert plan['closest_nominal_candidate_id'] is None and plan['eligible_count'] == 0
    assert plan['options'][0]['nominal_review']['reasons']


def test_circuit_only_option_is_explicitly_single_model(runs):
    before, after = runs; after['inputs']['solver'] = 'circuit'
    after['candidates'][0]['circuit_crosscheck'] = None
    option = plan_transition(before, before['candidates'][0]['id'], after)['options'][0]
    assert option['nominal_review']['eligible_nominal']
    assert option['nominal_review']['models_checked'] == ['Circuit prediction']
    assert option['uncertainty_status'] == 'MARGINAL'


@pytest.mark.parametrize('problem', ['profile', 'layout', 'bad_candidate', 'inconsistent_counts'])
def test_incompatible_or_corrupt_plans_are_rejected(runs, problem):
    before, after = runs; identifier = before['candidates'][0]['id']
    if problem == 'profile':after['profile']['version'] = 'different-generator-assumptions'
    elif problem == 'layout':after['inputs']['layout_id'] = 'other-layout'
    elif problem == 'bad_candidate':identifier = 'not-in-run'
    else:after['candidates'][0]['front_network']['components'][0]['total_required'] = 500
    with pytest.raises(ValueError):plan_transition(before, identifier, after)


def test_api_saves_immutable_comparison_and_escapes_printable_report(runs, tmp_path, monkeypatch):
    before, after = runs
    for run in [before, after]:run['profile']['name'] = 'Generator <script>alert(1)</script>'
    engine = create_engine('sqlite:///' + str(tmp_path / 'audit.sqlite3'), connect_args={'check_same_thread': False})
    storage.metadata.create_all(engine); monkeypatch.setattr(storage, 'engine', engine)
    before = storage.put('run', 'baseline', before); after = storage.put('run', 'target', after)
    client = TestClient(main.app)
    response = client.post('/api/runs/target/setup-transitions', json={'baseline_run_id': 'baseline', 'baseline_candidate_id': before['candidates'][0]['id']})
    assert response.status_code == 200, response.text
    plan = response.json()
    assert client.get(f"/api/setup-transitions/{plan['id']}/json").json() == plan
    report = client.get(f"/api/setup-transitions/{plan['id']}/report")
    assert report.status_code == 200 and '&lt;script&gt;' in report.text and '<script>' not in report.text
    assert 'Original optimizer ranking is unchanged' in report.text
    assert storage.get('baseline', 'run') == before and storage.get('target', 'run') == after
    assert client.post('/api/runs/target/setup-transitions', json={'baseline_run_id': 'baseline', 'baseline_candidate_id': 'wrong'}).status_code == 422
    engine.dispose()
