"""
SupplyShield - Person C, Day 6-7: the toy optimizer on the REAL core graph.

What it does
  1. Loads Person A's core_nodes.csv and core_edges.csv into a directed graph.
       node 'cap'  = hub capacity in truck legs per day   (A's capacity_est)
       edge 'cost' = median travel time of the lane in hours
       edge 'cap'  = unlimited (hub capacities are what limit the flow)
  2. Takes the 10 busiest lanes. For each one, pretend the lane is CLOSED (flood, strike) and
     reroute that lane's daily traffic through other hubs. Compare three plans:
       do nothing (the traffic is lost)  |  greedy  |  optimizer (LP)
  3. Saves experiments/c_real_lane_closures.csv and prints the run time of the optimizer.

Run from the project root:
    python opt/c_real_graph.py            # hubs are assumed EMPTY apart from the rerouted flow (optimistic)
    python opt/c_real_graph.py --spare    # hubs keep only their SPARE capacity = capacity_est - normal daily traffic (pessimistic)
Needs: opt/c_toy_recovery.py (it reuses its solver), pandas numpy scipy networkx.

ASSUMPTIONS (write them in docs/c_notes.md):
  - cost unit = hours of travel; penalty for a leg that is never delivered = PENALTY_HOURS (a guess; test 24/48/96)
  - each closure is tested ALONE: other traffic in the network is ignored, so capacities are optimistic.
    The multi-commodity version (several flows sharing hub capacity) is the next step.
"""
import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

import c_toy_recovery as c

NODES_CSV = "data/processed/core_nodes.csv"
EDGES_CSV = "data/processed/core_edges.csv"
# used only if core_edges.csv has no travel-time column (Person A's file currently does not)
LEGS_CANDIDATES = ["data/processed/core_train_legs.csv", "data/processed/legs.csv"]
TRAIN_CUTOFF = "2018-09-26"   # same training cut as Person A's core and Person B's split
TIME_DIVISOR = 60.0        # Delhivery times are in minutes -> hours
TRAIN_DAYS = 14            # days the 'trips' column was counted over
PENALTY_HOURS = 96.0       # cost of one undelivered leg, in hours of travel
BIG = 10 ** 9


def find(df, candidates, what, substrings=(), required=True):
    for name in candidates:
        if name in df.columns:
            return name
    for col in df.columns:
        if substrings and all(sub in col.lower() for sub in substrings):
            return col
    if required:
        raise SystemExit(f"Could not find the {what} column. Columns are: {df.columns.tolist()}")
    return None


def lane_times_from_legs():
    """Median travel time (minutes) of every lane, computed from the leg table, training days only."""
    path = next((p for p in LEGS_CANDIDATES if Path(p).exists()), None)
    if path is None:
        raise SystemExit("core_edges.csv has no travel-time column and no legs file was found in "
                         f"{LEGS_CANDIDATES}. Ask Person A to add median_actual_time to core_edges.csv.")
    legs = pd.read_csv(path)
    l_src = find(legs, ["source_center"], "legs source")
    l_dst = find(legs, ["destination_center"], "legs destination")
    l_time = find(legs, ["actual_time"], "actual travel time", ("actual", "time"))
    if "core_train_legs" not in path and "od_start_time" in legs.columns:
        legs = legs[pd.to_datetime(legs["od_start_time"], errors="coerce") < pd.Timestamp(TRAIN_CUTOFF)]
    print(f"lane travel times computed from {path} (column '{l_time}', {len(legs):,} training legs)")
    med = legs.groupby([l_src, l_dst])[l_time].median().rename("median_time").reset_index()
    return med.rename(columns={l_src: "src_key", l_dst: "dst_key"})


def mean_daily_outgoing():
    """Normal traffic: average legs per day leaving each hub during the training days."""
    path = next((p for p in LEGS_CANDIDATES if Path(p).exists()), None)
    if path is None:
        raise SystemExit("--spare needs a legs file (core_train_legs.csv or legs.csv) in data/processed")
    legs = pd.read_csv(path)
    src = find(legs, ["source_center"], "legs source")
    if "core_train_legs" not in path and "od_start_time" in legs.columns:
        legs = legs[pd.to_datetime(legs["od_start_time"], errors="coerce") < pd.Timestamp(TRAIN_CUTOFF)]
    return legs[src].value_counts() / TRAIN_DAYS


def load_core_graph(nodes_csv=NODES_CSV, edges_csv=EDGES_CSV, spare=False):
    nodes, edges = pd.read_csv(nodes_csv), pd.read_csv(edges_csv)
    n_id = find(nodes, ["hub", "hub_id", "node", "node_id", "center"], "hub id")
    n_cap = find(nodes, ["capacity_est", "capacity", "cap"], "capacity", ("cap",))
    e_src = find(edges, ["source", "source_center", "origin", "from"], "lane source")
    e_dst = find(edges, ["destination", "destination_center", "dest", "to"], "lane destination")
    e_trips = find(edges, ["trips", "trip_count"], "trips", ("trip",))
    e_time = find(edges, ["median_actual_time", "median_time", "median_travel_time"],
                  "median travel time", ("median", "time"), required=False)
    if e_time is None:                                   # fall back to the leg table
        med = lane_times_from_legs()
        edges = edges.merge(med, left_on=[e_src, e_dst], right_on=["src_key", "dst_key"], how="left")
        e_time = "median_time"
        lost = int(edges[e_time].isna().sum())
        if lost:
            print(f"WARNING: {lost} of {len(edges)} lanes have no travel time and are dropped")
        edges = edges.dropna(subset=[e_time])
    print(f"columns used -> hub:{n_id} cap:{n_cap} | source:{e_src} dest:{e_dst} trips:{e_trips} time:{e_time}")

    cap = pd.to_numeric(nodes[n_cap], errors="coerce")
    missing = int(cap.isna().sum())
    if missing:
        print(f"WARNING: {missing} hubs have no capacity; using the median ({cap.median():.0f})")
        cap = cap.fillna(cap.median())
    if spare:
        normal = nodes[n_id].map(mean_daily_outgoing()).fillna(0.0)
        cap = (cap - normal).clip(lower=0.0)
        print(f"SPARE mode: capacity = capacity_est - normal daily traffic; hubs with zero spare: {int((cap < 0.5).sum())}")
    G = nx.DiGraph()
    for hub, k in zip(nodes[n_id], cap):
        G.add_node(hub, cap=float(k))
    for r in edges.itertuples(index=False):
        s, d = getattr(r, e_src), getattr(r, e_dst)
        if s in G and d in G and s != d:
            G.add_edge(s, d, cost=float(getattr(r, e_time)) / TIME_DIVISOR,
                       cap=BIG, trips=float(getattr(r, e_trips)))
    hours = pd.Series([d["cost"] for _, _, d in G.edges(data=True)])
    print("lane travel time in HOURS (sanity check, expect a few hours):", hours.describe().round(2).to_dict())
    return G


def do_nothing_od(G_before, G_after):
    """Keep using the original cheapest path; anything that cannot pass on it is lost."""
    path = nx.shortest_path(G_before, c.SRC, c.DST, weight="cost")
    limits = [c.DEMAND]
    limits += [G_after.nodes[n]["cap"] for n in path[1:-1]]
    limits += [G_after.edges[e]["cap"] for e in zip(path, path[1:])]
    sent = max(0.0, min(limits))
    return {e: sent for e in zip(path, path[1:])}, sent


def run_closure(G, lane, demand):
    u, v = lane
    c.SRC, c.DST, c.DEMAND, c.PENALTY = u, v, demand, PENALTY_HOURS
    before = G.copy()
    before.nodes[u]["cap"] = before.nodes[v]["cap"] = BIG       # the two ends are not capacity-limited
    after = before.copy()
    after.edges[lane]["cap"] = 0.0                               # the lane is closed
    out = {}
    for name, fn in [("do nothing", lambda: do_nothing_od(before, after)),
                     ("greedy", lambda: c.greedy(after)),
                     ("optimizer", lambda: c.solve_lp(after))]:
        t0 = time.perf_counter()
        flows, delivered = fn()
        secs = time.perf_counter() - t0
        res = c.evaluate(after, flows, delivered)
        out[name] = {**res, "seconds": round(secs, 3)}
    base = demand * G.edges[lane]["cost"]
    return base, out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    SPARE = "--spare" in sys.argv
    nodes_csv = args[0] if len(args) > 0 else NODES_CSV
    edges_csv = args[1] if len(args) > 1 else EDGES_CSV
    G = load_core_graph(nodes_csv, edges_csv, spare=SPARE)
    caps = pd.Series([d["cap"] for _, d in G.nodes(data=True)])
    print(f"\ncore graph: {G.number_of_nodes()} hubs, {G.number_of_edges()} lanes")
    print("hub capacity (legs/day):", caps.describe().round(1).to_dict())
    print("weakly connected parts:", nx.number_weakly_connected_components(G),
          "| strongly connected parts:", nx.number_strongly_connected_components(G))

    lanes = sorted(G.edges(data=True), key=lambda e: -e[2]["trips"])[:10]
    rows = []
    for u, v, d in lanes:
        demand = max(1, round(d["trips"] / TRAIN_DAYS))
        base, res = run_closure(G, (u, v), demand)
        for plan, r in res.items():
            rows.append({"lane": f"{u}->{v}", "daily_legs": demand, "normal_cost": round(base, 1),
                         "plan": plan, **r})
    table = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    print("\nCOST (leg-hours) when each of the 10 busiest lanes is closed:")
    print(table.pivot(index="lane", columns="plan", values="total_cost").round(1).to_string())
    print("\nAverage total cost per plan:\n", table.groupby("plan")["total_cost"].mean().round(1).to_string())
    print("\nLegs never delivered (unmet), summed over the 10 closures:\n",
          table.groupby("plan")["unmet"].sum().round(1).to_string())
    print("\nSlowest optimizer solve (seconds):", table[table["plan"] == "optimizer"]["seconds"].max())
    out = "experiments/c_real_lane_closures_spare.csv" if SPARE else "experiments/c_real_lane_closures.csv"
    Path("experiments").mkdir(exist_ok=True)
    table.to_csv(out, index=False)
    print("Saved", out)
