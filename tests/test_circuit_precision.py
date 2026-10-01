"""Cross-check modal metrics against independent time-domain integration."""
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from backend.app.physics.circuit import simulate


@pytest.mark.parametrize('impulse,rf,rt,end_us',[
    ('Lightning',40,24,500),('Switching',4000,1100,15000)])
def test_continuous_metrics_match_independent_charge_current_ode(impulse,rf,rt,end_us):
    n=9;charge=190;eff=.82;cg=3e-6/n;cl=1500e-12;inductance=18.5e-6
    # Integrate generator charge, load charge and branch current, rather than
    # diagonalizing the production voltage/current state matrix.
    def rhs(t,z):
        vg=z[0]/cg;vl=z[1]/cl;current=z[2]
        return [-vg/(rt*n)-current,current,(vg-vl-current*rf*n)/inductance]
    def peak_event(t,z):return z[2]
    peak_event.direction=-1
    integration=solve_ivp(rhs,(0,end_us*1e-6),[cg*n*charge*eff,0,0],method='Radau',
        rtol=2e-10,atol=[1e-16,1e-18,1e-10],dense_output=True,events=peak_event)
    assert integration.success
    peaks=integration.t_events[0];peaks=peaks[peaks>1e-12]
    tp=peaks[np.argmax(integration.sol(peaks)[1])]
    voltage=lambda t:float(integration.sol(t)[1]/cl)
    crest=voltage(tp)
    a=brentq(lambda t:voltage(t)-crest*.3,0,tp,xtol=1e-15)*1e6
    b=brentq(lambda t:voltage(t)-crest*.9,0,tp,xtol=1e-15)*1e6
    half=brentq(lambda t:voltage(t)-crest*.5,tp,end_us*1e-6,xtol=1e-15)*1e6
    expected=[1.67*(b-a) if impulse=='Lightning' else tp*1e6,
              half-a+.5*(b-a) if impulse=='Lightning' else half,crest]
    result=simulate(n,charge,rf,rt,3,1500,18.5,eff,impulse,False)
    np.testing.assert_allclose([result[k] for k in ['front_us','tail_us','crest_kv']],expected,rtol=2e-7)
    assert 'root refinement' in result['diagnostics']['metric_extraction']


def test_old_circuit_calibration_does_not_transfer_to_new_solver():
    from backend.app.optimization.engine import optimize,calibration_matches
    from backend.app.schemas import OptimizeRequest
    from backend.app.physics.circuit import VERSION
    req=OptimizeRequest(solver='circuit',monte_carlo_samples=8)
    run=optimize(req);c=run['candidates'][0]
    scope={**req.model_dump(),**c['settings'],'model_version':c['model_version'],
        'generator_profile':run['profile'],'rules_version':run['rules']['version'],
        'front_topology':c['front_network']['topology'],'tail_topology':c['tail_network']['topology']}
    cal={'scope':scope}
    assert not calibration_matches(cal,req,c)
    scope['physics_version']='lumped RLC Marx equivalent v1'
    assert not calibration_matches(cal,req,c)
    scope['physics_version']=VERSION
    assert calibration_matches(cal,req,c)
