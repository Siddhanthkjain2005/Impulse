"""Bounded knapsack series search plus parallel/mixed topologies, exact counts."""
from functools import lru_cache
from collections import Counter
from itertools import combinations_with_replacement
from decimal import Decimal
import math

@lru_cache(maxsize=40)
def networks(stock_tuple,max_components=24):
    stock={float(r):int(q) for r,q in stock_tuple if q>0}
    if not stock: return []
    found={}
    def add(value,counts,topology):
        count=sum(counts.values())
        if count>max_components or any(q>stock.get(r,0) for r,q in counts.items()): return
        key=round(value,8)
        item={'equivalent_ohm':float(value),'topology':topology,
              'components':[{'ohm':r,'count_per_stage':q} for r,q in sorted(counts.items())],
              'count_per_stage':count,'inventory_feasible':True}
        if key not in found or count<found[key]['count_per_stage']: found[key]=item
    # Exact decimal series DP; retain minimum-part construction for a sum.
    # Bound sum-state count to keep arbitrary imported values responsive.
    states={Decimal(0):Counter()}
    for r,qty in sorted(stock.items()):
        nxt=dict(states)
        for total,counts in states.items():
            for q in range(1,min(qty,max_components-sum(counts.values()))+1):
                key=total+Decimal(str(r))*q; new=counts+Counter({r:q})
                if key not in nxt or sum(new.values())<sum(nxt[key].values()): nxt[key]=new
        if len(nxt)>30000: raise ValueError('Inventory search exceeds 30000 sums; reduce distinct stock values or component bound.')
        states=nxt
    for counts in states.values():
        if counts: add(sum(r*q for r,q in counts.items()),counts,' + '.join(f'{q}×{r:g}Ω' for r,q in sorted(counts.items())))
    values=list(stock)
    for count in [2,3]:
        for combo in combinations_with_replacement(values,count):
            c=Counter(combo); add(1/sum(1/r for r in combo),c,' ∥ '.join(f'{r:g}Ω' for r in combo))
            if count==3:
                a,b,d=combo
                for x,y,z in [(a,b,d),(b,a,d),(d,a,b)]:
                    add(x+1/(1/y+1/z),c,f'{x:g}Ω + ({y:g}Ω ∥ {z:g}Ω)')
                    add(1/(1/x+1/(y+z)),c,f'{x:g}Ω ∥ ({y:g}Ω + {z:g}Ω)')
    legacy_values=set(found)
    # Count-aware series/parallel trees include four-part bridge-free networks.
    # Keep distinct component-count vectors in intermediate states: dropping a
    # more expensive realization here could hide a later stock-feasible tree.
    # Small hardware catalogs also receive five/six-part trees. This is bounded,
    # not a claim to enumerate every topology allowed by max_components.
    depth=min(max_components,sum(stock.values()),6 if len(stock)<=3 else 4)
    levels={1:{}}
    for i,r in enumerate(values):
        counts=tuple(int(j==i) for j in range(len(values)))
        levels[1][(counts,round(r,8))]=(r,f'{r:g}Ω')
    for size in range(2,depth+1):
        current={}
        for left_size in range(1,size//2+1):
            right_size=size-left_size
            for li,((lc,_),(lv,lt)) in enumerate(levels[left_size].items()):
                for ri,((rc,_),(rv,rt)) in enumerate(levels[right_size].items()):
                    if left_size==right_size and ri<li:continue
                    counts=tuple(a+b for a,b in zip(lc,rc))
                    if any(q>stock[r] for r,q in zip(values,counts)):continue
                    for value,topology in [(lv+rv,f'({lt}) + ({rt})'),
                                           (lv*rv/(lv+rv),f'({lt}) ∥ ({rt})')]:
                        key=(counts,round(value,8))
                        if key not in current:current[key]=(value,topology)
        levels[size]=current
        if size>=4:
            for (counts,_),(value,topology) in current.items():
                add(value,Counter({r:q for r,q in zip(values,counts) if q}),topology)
    # Identical parallel banks have a closed form and remain cheap at large
    # quantities, including the previously missing fourth 520/22000-ohm unit.
    for r,qty in stock.items():
        for count in range(4,min(qty,max_components)+1):
            add(r/count,Counter({r:count}),f'{count}×{r:g}Ω in parallel')
    for value,item in found.items():item['legacy_catalog_value']=value in legacy_values
    return list(found.values())

def nearest_networks(stock,target,max_components,count=6):
    all_items=networks(tuple(sorted(stock.items())),max_components)
    distance=lambda n:abs(math.log(n['equivalent_ohm']/max(target,1e-6)))
    def shortlist(items):
        closest=sorted(items,key=lambda n:(distance(n),n['count_per_stage']))[:count]
        simple=sorted([n for n in items if distance(n)<.3],key=lambda n:(n['count_per_stage'],distance(n)))[:3]
        return closest+simple
    # Expanded candidates supplement the old shortlist. Merely adding close
    # four-part values must not crowd out a simpler previously available setup.
    legacy=shortlist([n for n in all_items if n['legacy_catalog_value']])
    return list({round(n['equivalent_ohm'],8):n for n in legacy+shortlist(all_items)}.values())
