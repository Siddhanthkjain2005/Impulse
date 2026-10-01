"""Post-ranking challenges must not become another optimistic selection score."""
from copy import deepcopy
import pytest
from backend.app.optimization.engine import optimize,profile_for
from backend.app.optimization.verification import verify_settings
from backend.app.schemas import OptimizeRequest
from backend.app.physics.circuit import simulate


@pytest.fixture(scope='module')
def run():return optimize(OptimizeRequest(require_model_agreement=True))


def test_separate_seed_boundary_checks_and_reproducible_worst_case(run):
    c=run['candidates'][0];v=c['verification'];s=c['settings'];w=v['worst_case'];i=w['inputs']
    assert v['seed']!=c['robustness']['seed']
    assert not v['used_for_ranking'] and v['unique_scenarios']==144
    assert v['fresh_samples']['total']==128 and v['boundary_corners']['total']==16
    assert v['all_checks_pass'] and v['passed']==144
    assert w['limiting_model']=='Independent circuit' and w['limiting_metric']=='Front / peak time'
    measured=simulate(s['stages'],s['charge_kv_stage'],s['front_r_stage'],s['tail_r_stage'],3,
        i['load_c_pf']+i['divider_c_pf']+i['stray_c_pf'],i['l_uh'],.82,'Lightning',False)
    assert measured['front_us']==pytest.approx(w['predicted'],rel=1e-10)


def test_zero_uncertainty_reports_duplicate_scenarios_honestly(run):
    req=OptimizeRequest(require_model_agreement=True,uncertainty_pct=0)
    before=deepcopy(run['candidates'][0]);after=deepcopy(before)
    v=verify_settings(req,run['profile'],after,'hybrid')
    assert v['unique_scenarios']==1
    assert before==after  # Verification cannot modify score, prediction or ranking.


def test_rank_is_fixed_before_verification_even_when_checks_fail(monkeypatch):
    from backend.app.optimization import engine
    calls=[]
    def failed_audit(req,p,c,mode,cal):
        calls.append((c['id'],c['rank']))
        return {'all_checks_pass':False,'passed':0,'total':144}
    monkeypatch.setattr(engine,'verify_settings',failed_audit)
    result=optimize(OptimizeRequest(monte_carlo_samples=8))
    assert calls==[(c['id'],c['rank']) for c in result['candidates']]
    assert result['candidates'][0]['settings']['front_r_stage']==50
    assert all(c['verification']['passed']==0 for c in result['candidates'])
