"""Controlled exhaustive comparison; no fitting, tuning or Hidden Test access."""
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import statistics
import time
import argparse

from backend.app.schemas import OptimizeRequest
from backend.app.optimization.engine import optimize

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=32)
def exhaustive_catalog(stock_items, maximum):
    """Exact rational DP, retaining every count vector until the final Pareto reduction."""
    if maximum > 4 or len(stock_items) > 3:
        raise ValueError('Exhaustive benchmark restricted to <=4 parts and <=3 stock values.')
    values = [Fraction(str(r)) for r, _ in stock_items]
    limits = tuple(q for _, q in stock_items)
    states = {1: {}}
    for i, value in enumerate(values):
        if limits[i]:
            counts = tuple(int(j == i) for j in range(len(values)))
            states[1][(counts, value)] = f'{float(value):g}Ω'
    for size in range(2, maximum + 1):
        states[size] = {}
        for left_size in range(1, size):
            for (lc, lv), lt in states[left_size].items():
                for (rc, rv), rt in states[size-left_size].items():
                    counts = tuple(a+b for a, b in zip(lc, rc))
                    if any(a>b for a, b in zip(counts, limits)): continue
                    for value, text in [(lv+rv, f'({lt}) + ({rt})'), (lv*rv/(lv+rv), f'({lt}) ∥ ({rt})')]:
                        states[size].setdefault((counts, value), text)
    found = {}
    for size in states:
        for (counts, value), topology in states[size].items():
            key = round(float(value), 8)
            if key in found and found[key]['count_per_stage'] <= size: continue
            found[key] = {'equivalent_ohm': float(value), 'topology': topology,
                          'components': [{'ohm': float(v), 'count_per_stage': q} for v, q in zip(values, counts) if q],
                          'count_per_stage': size, 'inventory_feasible': True}
    return tuple(found[k] for k in sorted(found))


def exhaustive_provider(stock, target, maximum, count):
    return exhaustive_catalog(tuple(sorted(stock.items())), maximum)


def signature(candidate):
    s = candidate['settings']
    return tuple(round(s[k], 8) for k in ('stages', 'charge_kv_stage', 'front_r_stage', 'tail_r_stage'))


def compare(case):
    stock = lambda name: [{'ohm': r, 'count_per_stage': q} for r, q in case[name]]
    inputs = {k: v for k, v in case.items() if k not in ('id', 'front', 'tail')}
    req = OptimizeRequest(**inputs, model_mode='physics', max_components_per_network=3, monte_carlo_samples=8,
                          inventory_override={'front': stock('front'), 'tail': stock('tail'), 'provenance': 'Controlled synthetic benchmark inventory; not CPRI stock'})
    start = time.perf_counter(); bounded = optimize(req); bounded_time = time.perf_counter()-start
    start = time.perf_counter(); exhaustive = optimize(req, _benchmark_networks=exhaustive_provider); exhaustive_time = time.perf_counter()-start
    first, best = bounded['candidates'][0], exhaustive['candidates'][0]
    rank = next((i+1 for i, c in enumerate(exhaustive['benchmark_ranking']) if signature(c) == signature(first)), None)
    return {'id': case['id'], 'source_type': 'synthetic_benchmark', 'inputs': req.model_dump(),
            'same_best_candidate': signature(first) == signature(best),
            'exhaustive_best_in_bounded_top3': signature(best) in [signature(c) for c in bounded['candidates'][:3]],
            'bounded_winner_exhaustive_rank': rank, 'rank_difference': rank-1 if rank is not None else None,
            'objective_gap': first['score']-best['score'],
            'waveform_error_difference': first['accuracy_cost']-best['accuracy_cost'],
            'component_count_difference': first['setup_component_count']-best['setup_component_count'],
            'waveform_metric_difference': {k: first['hybrid'][k]-best['hybrid'][k] for k in ('front_us','tail_us','crest_kv')},
            'worst_waveform_margin_difference': min(1-abs(r['predicted']-r['target'])/((r['upper']-r['lower'])/2) for r in first['compliance']['rows']) - min(1-abs(r['predicted']-r['target'])/((r['upper']-r['lower'])/2) for r in best['compliance']['rows']),
            'bounded_seconds': bounded_time, 'exhaustive_seconds': exhaustive_time,
            'speedup': exhaustive_time/bounded_time,
            'bounded_evaluated': bounded['search']['evaluated'], 'exhaustive_evaluated': exhaustive['search']['evaluated'],
            'bounded_nominal_pass': first['compliance']['nominal_pass'], 'exhaustive_nominal_pass': best['compliance']['nominal_pass'],
            'bounded_settings': first['settings'], 'exhaustive_settings': best['settings'],
            'bounded_rank_key': [not first['compliance']['nominal_pass'], not first['compliance']['robust_pass'], first['score']],
            'exhaustive_rank_key': [not best['compliance']['nominal_pass'], not best['compliance']['robust_pass'], best['score']]}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--split', choices=['development', 'benchmark'], default='benchmark')
    args = parser.parse_args()
    protocol_path = ROOT/'config/search_quality_cases.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    rows = []
    for case in protocol[args.split]:
        row = compare(case); rows.append(row)
        print(case['id'], 'rank', row['bounded_winner_exhaustive_rank'], 'gap', row['objective_gap'], flush=True)
    report = {'version': '1.0.0', 'status': 'COMPLETE', 'split': args.split, 'source_type': 'synthetic_benchmark',
              'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
              'implementation_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['scripts/benchmark_search_quality.py','backend/app/optimization/engine.py','backend/app/optimization/networks.py']},
              'scope': protocol['protocol'], 'cases': rows,
              'top1_match_rate': statistics.mean(r['same_best_candidate'] for r in rows),
              'top3_containment_rate': statistics.mean(r['exhaustive_best_in_bounded_top3'] for r in rows),
              'median_objective_gap': statistics.median(r['objective_gap'] for r in rows),
              'worst_objective_gap': max(r['objective_gap'] for r in rows),
              'median_runtime_speedup': statistics.median(r['speedup'] for r in rows),
              'worst_missed_waveform_margin': max(0, -min(r['worst_waveform_margin_difference'] for r in rows)),
              'limitation': 'Small declared discrete spaces only. Objective gap alone does not reflect the preceding nominal/robust rank keys. Timings include cache effects and are machine-dependent. No global or laboratory claim.'}
    folder = ROOT/'artifacts/search_quality'; folder.mkdir(exist_ok=True)
    (folder/('summary.json' if args.split == 'benchmark' else 'development.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__': main()
