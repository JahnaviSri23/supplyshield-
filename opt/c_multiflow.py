"""
SupplyShield - Person C, Day 8-9: ALL traffic shares the hubs.

c_real_graph.py rerouted ONE lane's traffic through empty hubs (optimistic). Here every lane of the
core graph is a flow of its own ('commodity': origin, destination, legs per day). In normal times each
flow uses its own direct lane. Then ONE lane closes and we ask three plans to cope:
   1. do nothing   : the closed lane's legs are lost, every other flow keeps its direct lane
   2. greedy       : the closed lane's flow takes the cheapest detours, using only the room the
                     other (unchanged) flows leave free at each hub
   3. LP           : every flow may change route; minimises total travel hours + penalty for lost legs
All flows share the hub capacity. Capacity of a hub = A's capacity_est, which is defined on its
OUTGOING legs per day, so the rule is: all flows leaving a hub together <= capacity_est.

Run from the project root:  python opt/c_multiflow.py        (needs opt/c_real_graph.py, c_toy_recovery.py)
Output: experiments/c_multiflow_closures.csv
(extra_cost = how much worse the network gets under that plan, against THAT plan's own no-closure cost;
 extra_vs_best_normal = against the best possible no-closure cost, the same for every plan -> use this one to compare plans)

ASSUMPTIONS (write them in docs/c_notes.md):
  - demand of a flow = trips / 14 legs per day (training days)
  - traffic that leaves the core is ignored, but capacity_est counts it, so capacities are still a bit optimistic
  - cost = travel hours; a lost leg costs PENALTY_HOURS; each closure is tested alone
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

import c_real_graph as rg
import c_toy_recovery as c

BIG = 10 ** 9


def build_model(G):
    nodes = list(G.nodes)
    nidx = {n: i for i, n in enumerate(nodes)}
    edges = list(G.edges)
    eidx = {e: i for i, e in enumerate(edges)}
    N, E = len(nodes), len(edges)
    src = np.array([nidx[u] for u, _ in edges])
    dst = np.array([nidx[v] for _, v in edges])
    cost = np.array([G.edges[e]["cost"] for e in edges])
    flows = [(e[0], e[1], G.edges[e]["trips"] / rg.TRAIN_DAYS) for e in edges]   # (origin, destination, q)
    return nodes, nidx, edges, eidx, N, E, src, dst, cost, flows


def solve_multiflow(G, closed=None):
    """Minimum total cost over all flows sharing hub capacity. `closed` = one lane (u, v) that is shut."""
    nodes, nidx, edges, eidx, N, E, src, dst, cost, flows = build_model(G)
    K = len(flows)
    nvar = K * E + K                                   # x[k, e] and unmet[k]
    ks = np.repeat(np.arange(K), E)
    es = np.tile(np.arange(E), K)
    col = ks * E + es

    # flow balance: for flow k at node n:  out - in + [n=origin]*unmet - [n=dest]*unmet = [n=origin]*q - [n=dest]*q
    rows = np.concatenate([ks * N + src[es], ks * N + dst[es]])
    cols = np.concatenate([col, col])
    vals = np.concatenate([np.ones(K * E), -np.ones(K * E)])
    o_idx = np.array([nidx[o] for o, _, _ in flows])
    d_idx = np.array([nidx[d] for _, d, _ in flows])
    q = np.array([qq for _, _, qq in flows])
    karr = np.arange(K)
    rows = np.concatenate([rows, karr * N + o_idx, karr * N + d_idx])
    cols = np.concatenate([cols, K * E + karr, K * E + karr])
    vals = np.concatenate([vals, np.ones(K), -np.ones(K)])
    A_eq = coo_matrix((vals, (rows, cols)), shape=(K * N, nvar)).tocsr()
    b_eq = np.zeros(K * N)
    b_eq[karr * N + o_idx] += q
    b_eq[karr * N + d_idx] -= q

    # hub capacity: everything leaving hub n (all flows together) <= capacity_est(n)
    A_ub = coo_matrix((np.ones(K * E), (src[es], col)), shape=(N, nvar)).tocsr()
    b_ub = np.array([G.nodes[n]["cap"] for n in nodes])

    bounds_hi = np.full(nvar, np.inf)
    bounds_hi[K * E:] = q                              # cannot lose more than the demand
    if closed is not None:
        bounds_hi[np.arange(K) * E + eidx[closed]] = 0.0
    objective = np.concatenate([np.tile(cost, K), np.full(K, rg.PENALTY_HOURS)])
    res = linprog(objective, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=np.column_stack([np.zeros(nvar), bounds_hi]), method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    unmet = float(res.x[K * E:].sum())
    travel = float(np.dot(np.tile(cost, K), res.x[:K * E]))
    return travel + rg.PENALTY_HOURS * unmet, unmet


def baseline_plans(G, lane):
    """do nothing and greedy for the closure of `lane`; every other flow stays on its direct lane."""
    u, v = lane
    q = G.edges[lane]["trips"] / rg.TRAIN_DAYS
    normal_cost = sum(G.edges[e]["cost"] * G.edges[e]["trips"] / rg.TRAIN_DAYS for e in G.edges)
    other_cost = normal_cost - q * G.edges[lane]["cost"]

    # room left at each hub once all OTHER flows sit on their direct lanes
    load = {n: 0.0 for n in G.nodes}
    for (a, b) in G.edges:
        if (a, b) != lane:
            load[a] += G.edges[(a, b)]["trips"] / rg.TRAIN_DAYS
    residual = {n: max(0.0, G.nodes[n]["cap"] - load[n]) for n in G.nodes}

    H = G.copy()
    for n in H.nodes:
        H.nodes[n]["cap"] = residual[n]
    for e in H.edges:
        H.edges[e]["cap"] = BIG
    H.edges[lane]["cap"] = 0.0
    H.nodes[u]["cap"] = H.nodes[v]["cap"] = BIG
    c.SRC, c.DST, c.DEMAND, c.PENALTY = u, v, q, rg.PENALTY_HOURS
    flows, delivered = c.greedy(H)
    detour = sum(H.edges[e]["cost"] * f for e, f in flows.items())
    unmet = q - delivered
    return {"do nothing": (other_cost + rg.PENALTY_HOURS * q, q),
            "greedy": (other_cost + detour + rg.PENALTY_HOURS * unmet, unmet)}, normal_cost


if __name__ == "__main__":
    G = rg.load_core_graph()
    t0 = time.perf_counter()
    base_lp, base_unmet = solve_multiflow(G)
    print(f"\nno closure: LP optimum {base_lp:.1f} leg-hours, unmet {base_unmet:.2f} "
          f"({time.perf_counter() - t0:.1f} s for one solve)")
    top = sorted(G.edges, key=lambda e: -G.edges[e]["trips"])[:10]
    rows = []
    for lane in top:
        plans, normal_cost = baseline_plans(G, lane)
        t0 = time.perf_counter()
        lp_cost, lp_unmet = solve_multiflow(G, closed=lane)
        secs = time.perf_counter() - t0
        plans["LP (all flows)"] = (lp_cost, lp_unmet)
        for name, (total, unmet) in plans.items():
            ref = base_lp if name.startswith("LP") else normal_cost      # each plan is compared with ITS OWN no-closure cost
            rows.append({"lane": f"{lane[0]}->{lane[1]}", "closed_lane_legs_per_day": round(G.edges[lane]["trips"] / rg.TRAIN_DAYS, 2),
                         "plan": name, "total_cost": round(total, 1), "extra_cost": round(total - ref, 1),
                         "extra_vs_best_normal": round(total - base_lp, 1),
                         "unmet": round(unmet, 2), "lp_seconds": round(secs, 2)})
    table = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print("\nEXTRA COST caused by the closure (leg-hours), each plan vs its own no-closure cost:")
    print(table.pivot(index="lane", columns="plan", values="extra_cost").to_string())
    print("\nAverage EXTRA cost per plan:\n", table.groupby("plan")["extra_cost"].mean().round(1).to_string())
    print("\nFAIR COMPARISON (all plans against the same reference = the no-closure LP optimum):")
    print(table.pivot(index="lane", columns="plan", values="extra_vs_best_normal").to_string())
    print("\nAverage extra vs best normal:\n", table.groupby("plan")["extra_vs_best_normal"].mean().round(1).to_string())
    tot = table.pivot(index="lane", columns="plan", values="total_cost")
    print("\nCHECK: LP total <= greedy total in every closure (must be True):",
          bool((tot["LP (all flows)"] <= tot["greedy"] + 1e-6).all()))
    print("\nLegs never delivered, summed over the 10 closures:\n", table.groupby("plan")["unmet"].sum().round(2).to_string())
    print("\nSlowest LP solve (seconds):", table["lp_seconds"].max())
    Path("experiments").mkdir(exist_ok=True)
    table.to_csv("experiments/c_multiflow_closures.csv", index=False)
    print("Saved experiments/c_multiflow_closures.csv")
