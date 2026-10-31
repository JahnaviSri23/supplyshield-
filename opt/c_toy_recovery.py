"""
SupplyShield - Person C starter (Day 1 + Day 2).
A toy 8-hub network, a hub failure, and three ways to respond:
  1. do nothing     - keep sending along the original cheapest route
  2. greedy         - cheapest surviving route first, then the next, until nothing is left
  3. optimizer (LP) - best split of parcels over all routes (minimum total cost)
Run from the project root:  python opt/c_toy_recovery.py   (needs: pip install scipy numpy networkx pandas)
Put this file in opt/ and import the functions from your notebook later.
"""
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.optimize import linprog

SRC, DST = "S", "T"
DEMAND = 100          # parcels per day that must go from S to T
PENALTY = 20.0        # cost of one parcel that is NOT delivered (angry customer, refund)


def build_toy_graph():
    """Nodes have a daily capacity; edges have a cost per parcel (and optionally a cap)."""
    G = nx.DiGraph()
    caps = {"A": 60, "B": 60, "C": 50, "D": 60, "E": 40, "F": 40}
    for n, c in caps.items():
        G.add_node(n, cap=c)
    G.add_node(SRC, cap=10**6)
    G.add_node(DST, cap=10**6)
    edges = [("S", "A", 1), ("S", "B", 2), ("A", "C", 2), ("A", "D", 3), ("B", "D", 1),
             ("B", "E", 2), ("C", "T", 2), ("D", "T", 2), ("E", "F", 1), ("F", "T", 1)]
    for u, v, cost in edges:
        G.add_edge(u, v, cost=cost, cap=10**6)
    G.add_edge("S", "T", cost=12, cap=30)   # express van: expensive, limited
    return G


def fail_node(G, node, remaining=0.0):
    """Return a copy where `node` keeps only `remaining` (0 = fully down) of its capacity."""
    H = G.copy()
    H.nodes[node]["cap"] = H.nodes[node]["cap"] * remaining
    return H


def evaluate(G, flows, delivered):
    """Total cost = shipping cost of the flows + penalty for undelivered parcels."""
    ship = sum(G.edges[e]["cost"] * f for e, f in flows.items())
    unmet = DEMAND - delivered
    return {"shipping": round(ship, 1), "unmet": round(unmet, 1),
            "total_cost": round(ship + PENALTY * unmet, 1)}


# ---------------------------------------------------------------- optimizer
def solve_lp(G):
    """Minimum-cost split of DEMAND parcels over all routes, respecting node/edge capacities.
    Variables: one flow per edge, plus 'unmet' (parcels we fail to deliver)."""
    edges = list(G.edges)
    n_e = len(edges)                      # variable i < n_e is the flow on edges[i]; last one is unmet
    idx = {e: i for i, e in enumerate(edges)}
    cost = np.array([G.edges[e]["cost"] for e in edges] + [PENALTY])

    A_eq, b_eq, A_ub, b_ub = [], [], [], []

    row = np.zeros(n_e + 1)               # parcels leaving the source = demand - unmet
    for e in G.out_edges(SRC):
        row[idx[e]] = 1
    row[-1] = 1
    A_eq.append(row)
    b_eq.append(DEMAND)

    for n in G.nodes:
        if n in (SRC, DST):
            continue
        row = np.zeros(n_e + 1)           # parcels do not vanish at a hub: in = out
        for e in G.in_edges(n):
            row[idx[e]] += 1
        for e in G.out_edges(n):
            row[idx[e]] -= 1
        A_eq.append(row)
        b_eq.append(0)

        row = np.zeros(n_e + 1)           # a hub can only handle so many per day
        for e in G.in_edges(n):
            row[idx[e]] = 1
        A_ub.append(row)
        b_ub.append(G.nodes[n]["cap"])

    bounds = [(0, G.edges[e]["cap"]) for e in edges] + [(0, DEMAND)]
    res = linprog(cost, A_ub=np.array(A_ub), b_ub=b_ub, A_eq=np.array(A_eq), b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    flows = {e: float(res.x[idx[e]]) for e in edges}
    return flows, DEMAND - float(res.x[-1])


# ---------------------------------------------------------------- baselines
def do_nothing(G_before, G_after):
    """Keep using the cheapest ORIGINAL route. If it goes through a dead hub, parcels are lost."""
    path = nx.shortest_path(G_before, SRC, DST, weight="cost")
    cap = min(G_after.nodes[n]["cap"] for n in path[1:-1])
    sent = min(DEMAND, cap)
    flows = {(u, v): sent for u, v in zip(path, path[1:])}
    return flows, sent


def greedy(G):
    """Cheapest surviving route first, push as much as it can carry, then the next route."""
    cap_node = {n: G.nodes[n]["cap"] for n in G.nodes}
    cap_edge = {e: G.edges[e]["cap"] for e in G.edges}
    flows, delivered = {}, 0.0
    while delivered < DEMAND - 1e-9:
        H = nx.DiGraph()
        for (u, v) in G.edges:
            ok = cap_edge[(u, v)] > 1e-9 and cap_node[u] > 1e-9 and cap_node[v] > 1e-9
            if ok:
                H.add_edge(u, v, cost=G.edges[(u, v)]["cost"])
        if SRC not in H or DST not in H or not nx.has_path(H, SRC, DST):
            break
        path = nx.shortest_path(H, SRC, DST, weight="cost")
        edges = list(zip(path, path[1:]))
        push = min([DEMAND - delivered]
                   + [cap_edge[e] for e in edges]
                   + [cap_node[n] for n in path[1:-1]])
        for e in edges:
            cap_edge[e] -= push
            flows[e] = flows.get(e, 0) + push
        for n in path[1:-1]:
            cap_node[n] -= push
        delivered += push
    return flows, delivered


# ---------------------------------------------------------------- experiment
if __name__ == "__main__":
    G0 = build_toy_graph()
    rows = []
    for node in ["A", "B", "C", "D", "E", "F"]:
        G1 = fail_node(G0, node, remaining=0.0)
        for name, (flows, delivered) in {
            "do nothing": do_nothing(G0, G1),
            "greedy": greedy(G1),
            "optimizer": solve_lp(G1),
        }.items():
            r = evaluate(G1, flows, delivered)
            rows.append({"failed hub": node, "plan": name, **r})
    table = pd.DataFrame(rows)
    print(table.pivot(index="failed hub", columns="plan", values="total_cost"))
    print("\nAverage total cost per plan:")
    print(table.groupby("plan")["total_cost"].mean().round(1).sort_values())
    Path("experiments").mkdir(exist_ok=True)
    table.to_csv("experiments/c_toy_results.csv", index=False)
    print("\nSaved experiments/c_toy_results.csv")
