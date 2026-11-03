"""
sim/simulate.py - Cascade simulator v1 (Person B)

Load-redistribution cascade (Motter-Lai style):
- every hub has a capacity and a current load
- a failed hub's load goes to its alive neighbours, in proportion to their spare room
  (if nobody has spare room: in proportion to capacity)
- a hub fails when load > tolerance * capacity
- rounds repeat until no new hub fails
- load with nowhere to go is "unserved"
"""

from collections import defaultdict
import pandas as pd

EPS = 1e-9


def build_neighbors(edges):
    """edges: list of (hub_a, hub_b). Lanes are treated as two-way for load sharing."""
    nb = defaultdict(set)
    for a, b in edges:
        if a != b:
            nb[a].add(b)
            nb[b].add(a)
    return {k: sorted(v) for k, v in nb.items()}


def simulate_cascade(capacity, load, neighbors, initial_failed, tolerance=1.0, max_rounds=20, check_initial=True):
    cap = dict(capacity)
    cur = {n: float(load.get(n, 0.0)) for n in cap}
    bad = [h for h in initial_failed if h not in cap]
    # Guard against starting in an already-broken state
    if check_initial:
        over = [n for n in cap if cur[n] > tolerance * cap[n] + EPS]
        if over:
            raise ValueError(f"{len(over)} hubs start above tolerance x capacity, e.g., {over[:5]}")

    if bad:
        raise ValueError(f"unknown hubs in scenario: {bad}")
    
    total = sum(cur.values())
    failed_set, rounds, unserved = set(), [], 0.0
    newly = list(dict.fromkeys(initial_failed))  # drop duplicates, keep order
    
    for r in range(max_rounds + 1):
        if not newly:
            break
        failed_set.update(newly)
        add, shifted = defaultdict(float), 0.0
        
        for h in newly:
            moved, cur[h] = cur[h], 0.0
            shifted += moved
            if moved <= 0:
                continue
            
            alive = [j for j in neighbors.get(h, []) if j not in failed_set]
            if not alive:
                unserved += moved
                continue
            
            spare = {j: max(cap[j] - cur[j], 0.0) for j in alive}
            weight = spare if sum(spare.values()) > EPS else {j: cap[j] for j in alive}
            tot_w = sum(weight.values())
            
            if tot_w <= EPS:
                unserved += moved
                continue
            
            for j in alive:
                add[j] += moved * weight[j] / tot_w
                
        for j, a in add.items():
            cur[j] += a
            
        rounds.append({
            "round": r,
            "newly_failed": list(newly),
            "load_shifted": shifted,
            "total_failed": len(failed_set)
        })
        
        newly = [n for n in cap if n not in failed_set and cur[n] > tolerance * cap[n] + EPS]
        
    alive_load = {n: cur[n] for n in cap if n not in failed_set}
    util = [alive_load[n] / cap[n] for n in alive_load if cap[n] > 0]
    
    return {
        "initial_failed": list(initial_failed),
        "failed": sorted(failed_set),
        "n_failed": len(failed_set),
        "n_rounds": len(rounds),
        "rounds": rounds,
        "converged": len(newly) == 0,
        "total_load": total,
        "unserved_load": unserved,
        "unserved_share": unserved / total if total > 0 else 0.0,
        "final_load": alive_load,
        "max_utilization": max(util) if util else 0.0,
        "conserved": abs(total - (unserved + sum(alive_load.values()))) < 1e-6,
    }


def single_hub_failures(capacity, load, neighbors, tolerance=1.0, max_rounds=20, check_initial=True):
    """Fail each hub on its own and record how far the cascade spreads."""
    rows = []
    for h in capacity:
        r = simulate_cascade(capacity, load, neighbors, [h], tolerance, max_rounds, check_initial=check_initial)
        rows.append({
            "hub": h,
            "own_load": load.get(h, 0.0),
            "n_failed": r["n_failed"],
            "n_rounds": r["n_rounds"],
            "unserved_share": round(r["unserved_share"], 3),
            "max_util_alive": round(r["max_utilization"], 3)
        })
    return pd.DataFrame(rows).sort_values(["n_failed", "unserved_share"], ascending=False).reset_index(drop=True)