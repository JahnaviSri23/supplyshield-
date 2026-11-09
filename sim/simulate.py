"""
sim/simulate.py - Combined Cascade Simulator & Plan Evaluator (SupplyShield, Person B)

Features:
1. Plan Evaluator (`simulate_scenario`, `_normalize_plan`, `_propagate`):
   - Evaluates disruption recovery plans against scenarios (failed hubs, closed lanes).
   - Computes shipping costs, unmet demand penalties, round-by-round failure propagation, and node utilization.
2. Load-Redistribution Cascade (`simulate_cascade`, `single_hub_failures`, `build_neighbors`):
   - Motter-Lai style cascade simulation modeling spare-room/capacity-proportional load sharing.
   - Guard checks for initial state overloads and robust single-hub failure sweeps.
"""

from collections import defaultdict
import pandas as pd
import math

INF = math.inf
EPS = 1e-9


def _normalize_plan(plan, demand):
    """Accept {(u,v): flow}, {(o,d): {(u,v): flow}} or a list of {"od","edge","flow"} records."""
    if not plan:
        return {}
    if isinstance(plan, list):
        out = {}
        for r in plan:
            out.setdefault(tuple(r["od"]), {})[tuple(r["edge"])] = float(r["flow"])
        return out
    first = next(iter(plan.values()))
    if isinstance(first, dict):
        return {tuple(od): {tuple(e): float(f) for e, f in fl.items()} for od, fl in plan.items()}
    if len(demand) != 1:
        raise ValueError("a single-flow plan needs exactly one demand pair")
    return {next(iter(demand)): {tuple(e): float(f) for e, f in plan.items()}}


def _propagate(planned, demand, node_cap, cap_eff, lane_cap, closed, passes=200):
    actual = {k: {e: (0.0 if e in closed else min(f, lane_cap.get(e, INF))) for e, f in fl.items()}
              for k, fl in planned.items()}
    nodes = set(node_cap) | {n for fl in planned.values() for e in fl for n in e}
    offered = {n: 0.0 for n in nodes}
    delivered = {k: 0.0 for k in planned}
    for _ in range(passes):
        change = 0.0
        for n in nodes:
            cap = cap_eff.get(n, INF)
            want, p_out = {}, {}
            for k, fl in planned.items():
                o, d = k
                inflow = demand.get(k, 0.0) if n == o else sum(
                    f for (u, v), f in actual[k].items() if v == n)
                if n == d:
                    want[k] = inflow
                else:
                    p_out[k] = sum(f for (u, v), f in fl.items() if u == n)
                    want[k] = min(inflow, p_out[k]) if p_out[k] > 0 else 0.0
            total = sum(want.values())
            offered[n] = total
            scale = min(1.0, cap / total) if total > 1e-12 else 1.0
            for k, fl in planned.items():
                t = want[k] * scale
                if n == k[1]:
                    change = max(change, abs(t - delivered[k]))
                    delivered[k] = t
                elif p_out[k] > 0:
                    for (u, v), f in fl.items():
                        if u == n:
                            new = 0.0 if (u, v) in closed else min(f * t / p_out[k],
                                                                  lane_cap.get((u, v), INF))
                            change = max(change, abs(new - actual[k][(u, v)]))
                            actual[k][(u, v)] = new
        if change < 1e-9:
            break
    return actual, offered, delivered


def simulate_scenario(graph, scenario, plan, overload_factor=None, max_rounds=20):
    node_cap, lane_cost = graph["node_cap"], graph["lane_cost"]
    lane_cap, demand = graph.get("lane_cap", {}), graph["demand"]
    penalty = float(scenario.get("penalty", 20.0))

    frac = {h: float(x) for h, x in scenario.get("failed_hubs", {}).items()}
    unknown = [h for h in frac if h not in node_cap]
    if unknown:
        raise ValueError(f"unknown hubs in scenario: {unknown}")
    closed = {tuple(l) for l in scenario.get("closed_lanes", [])}
    planned = _normalize_plan(plan, demand)

    down = {h for h, x in frac.items() if x <= 0}
    by_round = [sorted(down)]
    for _ in range(max_rounds + 1):
        cap_eff = {h: node_cap[h] * (0.0 if h in down else frac.get(h, 1.0)) for h in node_cap}
        actual, offered, delivered = _propagate(planned, demand, node_cap, cap_eff, lane_cap, closed)
        if overload_factor is None:
            break
        newly = sorted(h for h in node_cap if h not in down and cap_eff[h] < INF
                       and offered[h] > overload_factor * cap_eff[h] + 1e-9)
        if not newly:
            break
        down |= set(newly)
        by_round.append(newly)

    shipping = sum(lane_cost.get(e, 0.0) * f for fl in actual.values() for e, f in fl.items())
    unmet = max(sum(demand.values()) - sum(delivered.values()), 0.0)
    through = {h: 0.0 for h in node_cap}
    for k, fl in actual.items():
        for (u, v), f in fl.items():
            if u in through:
                through[u] += f
        if k[1] in through:
            through[k[1]] += delivered[k]
    return {
        "scenario_id": scenario.get("id"),
        "shipping": round(shipping, 6),
        "unmet": round(unmet, 6),
        "total_cost": round(shipping + penalty * unmet, 6),
        "failed_hubs_by_round": by_round,
        "utilization_final": {h: (round(through[h] / node_cap[h], 4) if node_cap[h] > 0 else 0.0)
                              for h in node_cap},
        "rounds": len(by_round),
        "recovery_days": scenario.get("days", 1),
    }


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
    if check_initial:
        over = [n for n in cap if cur[n] > tolerance * cap[n] + EPS]
        if over:
            raise ValueError(f"{len(over)} hubs start above tolerance x capacity, e.g., {over[:5]}")

    if bad:
        raise ValueError(f"unknown hubs in scenario: {bad}")
    
    total = sum(cur.values())
    failed_set, rounds, unserved = set(), [], 0.0
    newly = list(dict.fromkeys(initial_failed))
    
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