"""
SupplyShield - Person C, Day 4-5: compare 5 plans over many sampled 'tomorrows'.

Every plan is decided TODAY, before we know how much hub D can handle tomorrow.
Plans 1-3 assume D is fine (capacity 60). Plans 4-5 know the odds of a bad day.
  1. do nothing        : keep using the single cheapest original road
  2. greedy            : fill the cheapest open roads first
  3. deterministic LP  : best split of parcels assuming D = 60
  4. expected-cost LP  : best on an average day (knows the odds)
  5. CVaR LP           : best on the worst days (knows the odds)

Then we sample 1000 tomorrows (D handles 60 / 30 / 0 with the probabilities in SCENARIOS) and
measure each plan. Cost of a day = shipping + PENALTY for each parcel never planned
+ PENALTY for each parcel sent to D beyond what D can handle that day.
CVaR80 = average cost of the worst 20% of days.

Run from the project root:  python opt/c_policy_comparison.py
Needs c_toy_recovery.py and c_cvar_toy.py in the same folder (opt/).
"""
from pathlib import Path

import numpy as np
import pandas as pd

import c_cvar_toy as cv
import c_toy_recovery as c

N_DAYS = 1000
SEEDS = [0, 1, 2, 3, 4]
ALPHA = 0.8


def plans():
    G = cv.build_graph()
    out = {}
    out["1 do nothing"] = c.do_nothing(G, G)             # (flows, delivered)
    out["2 greedy"] = c.greedy(G)
    out["3 deterministic LP"] = c.solve_lp(G)
    out["4 expected-cost LP"] = (cv.solve(G, lam=0.0), c.DEMAND)
    out["5 CVaR LP"] = (cv.solve(G, lam=1.0), c.DEMAND)
    return G, out


def day_costs(G, flows, delivered, caps_d):
    ship = sum(G.edges[e]["cost"] * f for e, f in flows.items())
    into_d = sum(f for (u, v), f in flows.items() if v == cv.HUB)
    never_planned = c.PENALTY * (c.DEMAND - delivered)
    return ship + never_planned + c.PENALTY * np.maximum(0.0, into_d - caps_d)


def cvar(costs, alpha=ALPHA):
    k = int(round(len(costs) * (1 - alpha)))
    return float(np.sort(costs)[::-1][:k].mean())


if __name__ == "__main__":
    G, all_plans = plans()
    probs = [p for p, _ in cv.SCENARIOS]
    levels = [cap for _, cap in cv.SCENARIOS]
    rows = []
    for seed in SEEDS:
        caps_d = np.random.default_rng(seed).choice(levels, size=N_DAYS, p=probs)
        for name, (flows, delivered) in all_plans.items():
            d = day_costs(G, flows, delivered, caps_d)
            rows.append({"policy": name, "seed": seed, "mean_cost": d.mean(),
                         "cvar80": cvar(d), "worst_day": d.max()})
    res = pd.DataFrame(rows)
    summary = res.groupby("policy")[["mean_cost", "cvar80", "worst_day"]].agg(["mean", "std"]).round(1)
    pd.set_option("display.width", 200)
    print(summary.to_string())
    Path("experiments").mkdir(exist_ok=True)
    res.to_csv("experiments/c_toy_policy_comparison.csv", index=False)
    print("\nSaved experiments/c_toy_policy_comparison.csv")
