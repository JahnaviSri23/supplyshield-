"""
SupplyShield - consistency check between Person A's core files and Person B's prediction files.
Finds the usual team mistakes: different hub sets, mismatched locations, test days leaking into training.

Run from the project root:  python opt/check_consistency.py
It reads whatever exists in data/processed/ and says PASS or CHECK for each test (it never changes files).
"""
from pathlib import Path

import numpy as np
import pandas as pd

P = Path("data/processed")
CUT = pd.Timestamp("2018-09-26")         # training ends here (first 14 days of data)
TEST_FROM = pd.Timestamp("2018-09-30")   # B's test days start here (4 calibration days after the cut)


def load(name):
    f = P / name
    return pd.read_csv(f) if f.exists() else None


def col(df, candidates):
    return next((c for c in candidates if c in df.columns), None)


def say(ok, text):
    print(("PASS   " if ok else "CHECK  ") + text)


nodes, edges = load("core_nodes.csv"), load("core_edges.csv")
if nodes is None or edges is None:
    raise SystemExit("core_nodes.csv or core_edges.csv is missing in data/processed (pull from main first)")
hub = col(nodes, ["hub", "hub_id"])
src, dst = col(edges, ["source_center", "source"]), col(edges, ["destination_center", "destination"])
core = set(nodes[hub])
ends = set(edges[src]) | set(edges[dst])

print("=== 1. The core graph itself ===")
say(len(core) == nodes[hub].nunique(), f"core_nodes: {len(core)} hubs, no duplicate ids")
say(ends <= core, f"core_edges: {len(edges)} lanes touch {len(ends)} hubs; {len(ends - core)} are not in core_nodes")
print(f"       hubs with no lane at all: {len(core - ends)}")

print("\n=== 2. Locations ===")
la, lo = col(nodes, ["lat", "latitude"]), col(nodes, ["lon", "longitude"])
if la and lo:
    have = nodes[la].notna() & nodes[lo].notna()
    say(True, f"core_nodes: {int(have.sum())} of {len(nodes)} hubs have coordinates")
for fname in ["hubs.csv", "hubs_threshold3.csv", "weather_hubs.csv"]:
    other = load(fname)
    if other is None:
        continue
    h2 = col(other, ["hub", "hub_id"])
    la2, lo2 = col(other, ["lat", "latitude"]), col(other, ["lon", "longitude"])
    if not (h2 and la2 and lo2 and la and lo):
        print(f"       {fname}: could not find hub/lat/lon columns ({other.columns.tolist()[:8]}...)")
        continue
    m = nodes[[hub, la, lo]].merge(other[[h2, la2, lo2]].drop_duplicates(h2), left_on=hub, right_on=h2,
                                   suffixes=("", "_o"))
    m = m.dropna(subset=[la, lo, la2 if la2 != la else la + "_o", lo2 if lo2 != lo else lo + "_o"])
    a2, o2 = (la2 if la2 != la else la + "_o"), (lo2 if lo2 != lo else lo + "_o")
    bad = ((m[la] - m[a2]).abs() > 0.01) | ((m[lo] - m[o2]).abs() > 0.01)
    missing = len(core - set(other[h2]))
    say(int(bad.sum()) == 0 and missing == 0,
        f"{fname}: {len(m)} core hubs compared, {int(bad.sum())} with DIFFERENT coordinates, "
        f"{missing} core hubs missing from this file")

print("\n=== 3. Training and test days (no leakage) ===")
for fname, kind in [("core_train_legs.csv", "train"), ("core_later_legs.csv", "later")]:
    d = load(fname)
    if d is None:
        continue
    t = pd.to_datetime(d[col(d, ["od_start_time", "start"])], errors="coerce")
    ok = (t.max() < CUT) if kind == "train" else (t.min() >= CUT)
    say(ok, f"{fname}: {t.min()} to {t.max()}  (training must end before {CUT.date()})")

print("\n=== 4. Person B's files against the core ===")
preds = load("preds_test.csv")
if preds is None:
    print("       preds_test.csv not found (B has not pushed it)")
else:
    ps, pd_ = col(preds, ["source_center", "source"]), col(preds, ["destination_center", "destination"])
    if ps and pd_:
        core_lanes = set(zip(edges[src], edges[dst]))
        in_core = pd.Series(list(zip(preds[ps], preds[pd_]))).isin(core_lanes)
        say(in_core.mean() > 0.99, f"preds_test.csv: {len(preds):,} rows, {in_core.mean():.1%} are on core lanes "
                                   "(if B trained on ALL hubs, the rest are fine to ignore, but evaluate on the core)")
        print(f"       core lanes with no test-day prediction: {len(core_lanes - set(zip(preds[ps], preds[pd_])))} "
              "(normal if a lane had no trips on the test days)")
    tcol = col(preds, ["start", "od_start_time"])
    if tcol:
        t = pd.to_datetime(preds[tcol], errors="coerce")
        say(t.min() >= TEST_FROM, f"preds_test.csv days: {t.min()} to {t.max()} "
                                  f"(test days should start on or after {TEST_FROM.date()})")
risk = load("risk_table.csv")
if risk is None:
    print("       risk_table.csv not found (B has not pushed it)")
else:
    rs, rd = col(risk, ["source_center", "source"]), col(risk, ["destination_center", "destination"])
    rh = col(risk, ["hub", "hub_id"])
    if rs and rd:
        lanes_r = set(zip(risk[rs], risk[rd]))
        core_lanes = set(zip(edges[src], edges[dst]))
        say(core_lanes <= lanes_r, f"risk_table.csv: covers {len(core_lanes & lanes_r)} of {len(core_lanes)} core lanes; "
                                   f"{len(lanes_r - core_lanes)} lanes outside the core")
    elif rh:
        say(core <= set(risk[rh]), f"risk_table.csv: covers {len(core & set(risk[rh]))} of {len(core)} core hubs; "
                                   f"{len(set(risk[rh]) - core)} hubs outside the core")
    else:
        print(f"       risk_table.csv: no lane or hub columns found: {risk.columns.tolist()}")
print("\n=== 5. One shared split (src/make_split.py -> split_trip_ids.csv) ===")
sp = load("split_trip_ids.csv")
if sp is None:
    print("       split_trip_ids.csv not found: Person A should run src/make_split.py and push it")
else:
    groups = {g: set(sp.loc[sp["split"] == g, "trip_uuid"]) for g in ["train", "calibration", "test"]}
    print("       trips per group:", {g: len(v) for g, v in groups.items()})
    for fname, want in [("core_train_legs.csv", "train"), ("core_later_legs.csv", None),
                        ("preds_test.csv", "test")]:
        d = load(fname)
        if d is None:
            continue
        tc = col(d, ["trip_uuid", "trip_id"])
        if tc is None:
            print(f"       {fname}: has no trip_uuid column, so its split cannot be checked "
                  "(ask the owner to add trip_uuid)")
            continue
        ids = set(d[tc])
        if want:
            say(ids <= groups[want], f"{fname}: {len(ids - groups[want])} of {len(ids)} trips are NOT in the '{want}' group")
        else:
            say(not (ids & groups["train"]), f"{fname}: {len(ids & groups['train'])} of {len(ids)} trips belong to the TRAIN group")
print("\nDone. Every CHECK line is something to ask Person A or Person B about.")
