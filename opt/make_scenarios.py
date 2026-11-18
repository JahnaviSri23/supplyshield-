"""
SupplyShield - Person C, Day 8: the scenario list for the core graph, in the agreed format.
Run from the project root:  python opt/make_scenarios.py        (needs opt/c_real_graph.py)
Writes experiments/scenarios_core.csv with one row per scenario:
    id, failed_hubs (JSON: hub -> remaining capacity fraction), closed_lanes (JSON list of [u, v]),
    days, seed, penalty
  L01..L10 : the 10 busiest lanes closed, one at a time (the same ones as c_real_graph.py)
  H01..H10 : the 10 hubs with the largest capacity, each fully down (0%) and at half capacity (50%)
Person A's simulate() and Person B's risk table are both tested on this one list.
"""
import json
from pathlib import Path

import pandas as pd

import c_real_graph as rg

G = rg.load_core_graph()
lanes = sorted(G.edges, key=lambda e: -G.edges[e]["trips"])[:10]
hubs = sorted(G.nodes, key=lambda n: -G.nodes[n]["cap"])[:10]

rows = []
for i, (u, v) in enumerate(lanes, 1):
    rows.append({"id": f"L{i:02d}", "failed_hubs": "{}", "closed_lanes": json.dumps([[u, v]]),
                 "days": 1, "seed": i, "penalty": rg.PENALTY_HOURS})
for i, h in enumerate(hubs, 1):
    for frac in (0.0, 0.5):
        rows.append({"id": f"H{i:02d}_{int(frac * 100)}", "failed_hubs": json.dumps({h: frac}),
                     "closed_lanes": "[]", "days": 1, "seed": 100 + i, "penalty": rg.PENALTY_HOURS})
table = pd.DataFrame(rows)
Path("experiments").mkdir(exist_ok=True)
table.to_csv("experiments/scenarios_core.csv", index=False)
print(table.head(12).to_string(index=False))
print(f"\n{len(table)} scenarios saved to experiments/scenarios_core.csv")
