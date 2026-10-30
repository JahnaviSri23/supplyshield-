"""
SupplyShield - Person C, step 2: a plan chosen BEFORE we know how bad tomorrow is.
Hub D usually handles 60 parcels a day, but some days only 30 (or 0). We must decide today how many
parcels to send through each route. Parcels sent to D beyond its real capacity that day are lost
(each costs PENALTY).

Two ways to choose the plan:
  expected-cost plan : cheapest on an AVERAGE day
  CVaR plan          : cheapest on the WORST days (CVaR = average cost of the worst (1 - ALPHA) share of days)

Run from the project root:  python opt/c_cvar_toy.py      (needs scipy numpy networkx pandas)
Put this file next to c_toy_recovery.py in opt/.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog

import c_toy_recovery as c

HUB = "D"                                   # the hub whose capacity is uncertain
SCENARIOS = [(0.7, 60), (0.2, 30), (0.1, 0)]  # (probability, capacity of hub D that day)
ALPHA = 0.8                                 # CVaR looks at the worst 20% of days


def build_graph():
    G = c.build_toy_graph()
    # make the safe route (via E and F) pricier, so playing safe really costs something
    G.edges[("E", "F")]["cost"] = 6
    return G


def solve(G, lam):
    """lam = 0 -> minimise the average cost; lam = 1 -> minimise CVaR; in between = a mix."""
    edges = list(G.edges)
    n_e, n_s = len(edges), len(SCENARIOS)
    idx = {e: i for i, e in enumerate(edges)}
    # variables: [edge flows ..., overflow_s ..., z_s ..., t]
    n = n_e + 2 * n_s + 1
    o0, z0, t = n_e, n_e + n_s, n - 1
    p = np.array([s[0] for s in SCENARIOS])
    ship = np.array([G.edges[e]["cost"] for e in edges])

    cost = np.zeros(n)
    cost[:n_e] = (1 - lam) * ship                          # shipping cost, averaged
    cost[o0:o0 + n_s] = (1 - lam) * c.PENALTY * p          # expected loss from overflow
    cost[z0:z0 + n_s] = lam * p / (1 - ALPHA)              # CVaR part
    cost[t] = lam
    # (for lam > 0 the CVaR term also needs the shipping cost: it sits inside z_s via the constraint below)

    A_ub, b_ub, A_eq, b_eq = [], [], [], []
    row = np.zeros(n)
    for e in G.out_edges(c.SRC):
        row[idx[e]] = 1
    A_eq.append(row); b_eq.append(c.DEMAND)                # every parcel gets a route

    for node in G.nodes:
        if node in (c.SRC, c.DST):
            continue
        row = np.zeros(n)
        for e in G.in_edges(node):
            row[idx[e]] += 1
        for e in G.out_edges(node):
            row[idx[e]] -= 1
        A_eq.append(row); b_eq.append(0)
        row = np.zeros(n)
        for e in G.in_edges(node):
            row[idx[e]] = 1
        cap = max(cap_s for _, cap_s in SCENARIOS) if node == HUB else G.nodes[node]["cap"]
        A_ub.append(row); b_ub.append(cap)

    for s, (_, cap_s) in enumerate(SCENARIOS):
        row = np.zeros(n)                                  # overflow_s >= inflow_D - cap_s
        for e in G.in_edges(HUB):
            row[idx[e]] = 1
        row[o0 + s] = -1
        A_ub.append(row); b_ub.append(cap_s)
        row = np.zeros(n)                                  # z_s >= scenario_cost_s - t
        row[:n_e] = ship
        row[o0 + s] = c.PENALTY
        row[z0 + s] = -1
        row[t] = -1
        A_ub.append(row); b_ub.append(0)

    bounds = [(0, G.edges[e]["cap"]) for e in edges] + [(0, None)] * (2 * n_s) + [(None, None)]
    res = linprog(cost, A_ub=np.array(A_ub), b_ub=b_ub, A_eq=np.array(A_eq), b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    return {e: float(res.x[idx[e]]) for e in edges}


def report(G, flows):
    ship = sum(G.edges[e]["cost"] * f for e, f in flows.items())
    into_d = sum(f for (u, v), f in flows.items() if v == HUB)
    day_costs = [ship + c.PENALTY * max(0.0, into_d - cap_s) for _, cap_s in SCENARIOS]
    p = np.array([s[0] for s in SCENARIOS])
    order = np.argsort(day_costs)[::-1]                    # worst days first
    left, tail = 1 - ALPHA, 0.0
    for i in order:                                        # average of the worst (1-ALPHA) share
        take = min(p[i], left)
        tail += take * day_costs[i]
        left -= take
        if left <= 1e-12:
            break
    return {"parcels via D": round(into_d, 1), "shipping": round(ship, 1),
            **{f"cost if D={cap}": round(d, 1) for (_, cap), d in zip(SCENARIOS, day_costs)},
            "average cost": round(float(np.dot(p, day_costs)), 1),
            f"CVaR {ALPHA:.0%}": round(tail / (1 - ALPHA), 1)}


if __name__ == "__main__":
    G = build_graph()
    rows = []
    for name, lam in [("expected-cost plan", 0.0), ("mixed plan", 0.5), ("CVaR plan", 1.0)]:
        rows.append({"plan": name, **report(G, solve(G, lam))})
    table = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(table.to_string(index=False))
    Path("experiments").mkdir(exist_ok=True)
    table.to_csv("experiments/c_cvar_toy.csv", index=False)
    print("\nSaved experiments/c_cvar_toy.csv")
