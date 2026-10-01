"""Exact workbook calculator, deliberately distinct from the enhanced circuit."""
import math

def calculate(impulse_type='Lightning', test_kv=1425., load_c_pf=850., divider_c_pf=500.,
              stray_c_pf=150., l_uh=18.5, efficiency=.82, max_stages=15,
              max_stage_kv=200., stage_c_uf=3.):
    tf, tt = (1.2, 50.) if impulse_type == 'Lightning' else (250., 2500.)
    n = math.ceil(test_kv / (efficiency * max_stage_kv))
    c2 = (load_c_pf + divider_c_pf + stray_c_pf) * 1e-12
    c1 = stage_c_uf * 1e-6 / n
    theoretical_front = math.sqrt(max(1e-18,(tf / 1e6 / 1.67)**2 - 2.5*l_uh*1e-6*c2))/c2
    theoretical_tail = tt / 1e6 / (.693*(c1+c2))
    rf = math.floor(theoretical_front/n/5 + .5)*5
    rt = math.floor(theoretical_tail/n/5 + .5)*5
    result = predict(n, test_kv/(efficiency*n), rf, rt, load_c_pf, divider_c_pf,
                     stray_c_pf, l_uh, efficiency, stage_c_uf)
    return {**result, 'stages': n, 'charge_kv_stage': test_kv/(efficiency*n),
            'front_r_stage': rf, 'tail_r_stage': rt, 'total_c_pf': c2*1e12,
            'c1_uf': c1*1e6, 'theoretical_front_total_ohm': theoretical_front,
            'theoretical_tail_total_ohm': theoretical_tail,
            'stage_utilization': test_kv/(efficiency*n*max_stage_kv),
            'physics_feasible': n<=max_stages, 'source': 'Hybrid Calculator; workbook equations'}

def predict(stages, charge_kv_stage, front_r_stage, tail_r_stage, load_c_pf,
            divider_c_pf, stray_c_pf, l_uh, efficiency, stage_c_uf=3.):
    c2=(load_c_pf+divider_c_pf+stray_c_pf)*1e-12
    c1=stage_c_uf*1e-6/stages
    return {'front_us':1.67*math.sqrt((front_r_stage*stages*c2)**2+2.5*l_uh*1e-6*c2)*1e6,
            'tail_us':.693*tail_r_stage*stages*(c1+c2)*1e6,
            'crest_kv':stages*charge_kv_stage*efficiency}
