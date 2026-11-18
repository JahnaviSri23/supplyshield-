"""
SupplyShield - Person C, Day 8: demand from TRIPS instead of single lanes.

A trip is a chain of legs (hub -> hub -> hub). Its origin is the source of its first leg and its
destination is the destination of its last leg. Flows that go through several hubs are what make
hub failures and cascades testable (a flow that is just one lane never passes THROUGH a hub).

Run from the project root:  python opt/build_od_demand.py
Reads : data/processed/legs.csv, core_nodes.csv, and split_trip_ids.csv if it exists
        (otherwise: trips created before 2018-09-26)
Writes: data/processed/core_od_demand.csv  (origin, destination, trips, usual_route, daily_legs, legs_on_route)

It prints how much of the real traffic the core covers. Read those numbers before building on this.
"""
from pathlib import Path

import pandas as pd

P = Path("data/processed")
TRAIN_DAYS = 14
CUT = pd.Timestamp("2018-09-26")

legs = pd.read_csv(P / "legs.csv", usecols=lambda c: c in {
    "trip_uuid", "source_center", "destination_center", "od_start_time", "trip_creation_time"})
core = set(pd.read_csv(P / "core_nodes.csv")["hub"])

if (P / "split_trip_ids.csv").exists():
    split = pd.read_csv(P / "split_trip_ids.csv")
    train_ids = set(split.loc[split["split"] == "train", "trip_uuid"])
    legs = legs[legs["trip_uuid"].isin(train_ids)]
    print("training trips taken from split_trip_ids.csv")
else:
    created = pd.to_datetime(legs["trip_creation_time"], errors="coerce")
    legs = legs[created < CUT]
    print(f"split_trip_ids.csv not found: training trips = created before {CUT.date()}")

legs = legs.assign(start=pd.to_datetime(legs["od_start_time"], errors="coerce")) \
           .sort_values(["trip_uuid", "start"])
g = legs.groupby("trip_uuid")
trips = pd.DataFrame({
    "origin": g["source_center"].first(),
    "destination": g["destination_center"].last(),
    "n_legs": g.size(),
    "route": g["source_center"].agg(lambda s: ">".join(s)) + ">" + g["destination_center"].last(),
}).reset_index()
trips["route_hubs"] = trips["route"].str.split(">")

n = len(trips)
moving = trips[trips["origin"] != trips["destination"]]
ends_in = moving[moving["origin"].isin(core) & moving["destination"].isin(core)]
inside = ends_in[ends_in["route_hubs"].apply(lambda hs: all(h in core for h in hs))]
print(f"\ntraining trips: {n:,}")
print(f"  origin != destination      : {len(moving):,}")
print(f"  both ends in the core      : {len(ends_in):,} ({len(ends_in) / n:.1%} of all trips)")
print(f"  whole route inside the core: {len(inside):,} ({len(inside) / n:.1%} of all trips)")
print("  legs per trip (ends in core):", ends_in["n_legs"].describe().round(2).to_dict())

od = (ends_in.groupby(["origin", "destination"])
      .agg(trips=("trip_uuid", "size"), usual_route=("route", lambda s: s.value_counts().index[0]))
      .reset_index())
od["daily_legs"] = (od["trips"] / TRAIN_DAYS).round(3)
od["legs_on_route"] = od["usual_route"].str.count(">")       # number of legs on the usual route
od = od.sort_values("trips", ascending=False)
print(f"\nOD pairs inside the core: {len(od)} | daily trips covered: {od['daily_legs'].sum():.1f}")
print("OD pairs by legs on the usual route:", od["legs_on_route"].value_counts().sort_index().to_dict())
print("\nTop 10 OD pairs:")
print(od.head(10)[["origin", "destination", "trips", "legs_on_route", "usual_route"]].to_string(index=False))
od.to_csv(P / "core_od_demand.csv", index=False)
print("\nSaved data/processed/core_od_demand.csv")
