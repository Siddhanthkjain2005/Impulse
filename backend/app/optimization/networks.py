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
    return list(found.values())

def nearest_networks(stock,target,max_components,count=6):
    all_items=networks(tuple(sorted(stock.items())),max_components)
    distance=lambda n:abs(math.log(n['equivalent_ohm']/max(target,1e-6)))
    closest=sorted(all_items,key=lambda n:(distance(n),n['count_per_stage']))[:count]
    simple=sorted([n for n in all_items if distance(n)<.3],key=lambda n:(n['count_per_stage'],distance(n)))[:3]
    return list({round(n['equivalent_ohm'],8):n for n in closest+simple}.values())
