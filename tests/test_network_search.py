"""Independent electrical/count checks for the expanded stock constructions."""
import re
from collections import Counter
import pytest
from backend.app.optimization.networks import networks,nearest_networks


def evaluate_topology(text):
    bank = re.fullmatch(r'(\d+)×([\d.]+)Ω in parallel', text)
    if bank:
        count, value = int(bank[1]), float(bank[2])
        return value/count, Counter({value:count})
    tokens=re.findall(r'\d+(?:\.\d+)?|[×+∥()]',text)
    pos=0
    def node():
        nonlocal pos
        if tokens[pos]=='(':
            pos+=1;value,counts=expression();assert tokens[pos]==')';pos+=1
            return value,counts
        value=float(tokens[pos]);pos+=1;count=1
        if pos<len(tokens) and tokens[pos]=='×':
            count=int(value);pos+=1;value=float(tokens[pos]);pos+=1
        return value*count,Counter({value:count})
    def expression():
        nonlocal pos
        value,counts=node()
        while pos<len(tokens) and tokens[pos]!=')':
            op=tokens[pos];pos+=1;other,parts=node()
            value=value+other if op=='+' else 1/(1/value+1/other)
            counts+=parts
        return value,counts
    result=expression();assert pos==len(tokens)
    return result


@pytest.mark.parametrize('resistance',[520.,22000.])
def test_four_identical_parallel_units_are_available(resistance):
    rows=networks(((resistance,4),),24)
    c=next(r for r in rows if r['equivalent_ohm']==pytest.approx(resistance/4))
    assert c['components']==[{'ohm':resistance,'count_per_stage':4}]
    assert not any(r['equivalent_ohm']<resistance/4-1e-9 for r in rows)
    assert not any(r['equivalent_ohm']==pytest.approx(resistance/4) for r in networks(((resistance,4),),3))


def test_four_part_series_parallel_tree_preserves_real_inventory():
    stock=((100.,1),(200.,1),(300.,1),(400.,1))
    rows=networks(stock,4)
    assert any(r['equivalent_ohm']==pytest.approx(210) and r['count_per_stage']==4 for r in rows)
    for row in rows:
        resistance,counts=evaluate_topology(row['topology'])
        assert resistance==pytest.approx(row['equivalent_ohm'],rel=1e-12)
        assert dict(counts)=={r['ohm']:r['count_per_stage'] for r in row['components']}
        assert sum(counts.values())<=4
        assert all(q<=dict(stock)[r] for r,q in counts.items())


def test_six_part_small_catalog_trees_and_larger_identical_banks():
    stock=((30.,4),(465.,4),(3700.,4))
    for row in networks(stock,6):
        resistance,counts=evaluate_topology(row['topology'])
        assert resistance==pytest.approx(row['equivalent_ohm'],rel=1e-12)
        assert dict(counts)=={r['ohm']:r['count_per_stage'] for r in row['components']}
        assert sum(counts.values())<=6 and all(q<=4 for q in counts.values())
    assert any(r['equivalent_ohm']==pytest.approx(10) for r in networks(((100.,10),),10))


def test_expansion_keeps_previously_available_simple_target_alternatives():
    stock={r:4 for r in [5,10,15,20,25,30,40,50,75,100,150,200]}
    choices=nearest_networks(stock,50e-6/(.693*(3e-6+9*1500e-12)),24,5)
    # The earlier three-part 15 + (10 || 75) setting must survive additions.
    assert any(c['equivalent_ohm']==pytest.approx(15+10*75/(10+75)) for c in choices)
