from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

TRAIN_START = pd.Timestamp("2018-09-12")
TRAIN_CUTOFF = pd.Timestamp("2018-09-26")


def main():
    nodes = pd.read_csv(PROCESSED / "core_nodes.csv")
    edges = pd.read_csv(PROCESSED / "core_edges.csv")
    legs = pd.read_csv(PROCESSED / "core_train_legs.csv")

    assert nodes["hub"].is_unique
    assert not edges.duplicated(
        ["source_center", "destination_center"]
    ).any()

    created = pd.to_datetime(
        legs["trip_creation_time"], errors="raise"
    )
    assert created.notna().all()
    assert (
        (created >= TRAIN_START) & (created < TRAIN_CUTOFF)
    ).all(), "Non-training trips found."

    starts = pd.to_datetime(legs["od_start_time"], errors="raise")
    assert starts.notna().all()
    legs["departure_date"] = starts.dt.normalize()

    # Only departures occurring within the training window.
    # Some training trips have later legs; exclude those events here.
    observed = legs.loc[
        legs["departure_date"].ge(TRAIN_START)
        & legs["departure_date"].lt(TRAIN_CUTOFF)
    ].copy()

    days = pd.date_range(
        TRAIN_START,
        TRAIN_CUTOFF - pd.Timedelta(days=1),
        freq="D",
    )

    full_index = pd.MultiIndex.from_product(
        [nodes["hub"], days],
        names=["hub", "date"],
    )

    counts = observed.groupby(
        ["source_center", "departure_date"]
    ).size()
    counts.index.names = ["hub", "date"]

    daily = (
        counts.reindex(full_index, fill_value=0)
        .rename("outgoing_legs")
        .reset_index()
    )

    capacity = (
        daily.groupby("hub", as_index=False)
        .agg(
            observed_days=("date", "size"),
            active_days=("outgoing_legs", lambda x: int(x.gt(0).sum())),
            legs_per_day_p95=(
                "outgoing_legs",
                lambda x: x.quantile(0.95, interpolation="linear"),
            ),
        )
    )

    # Baseline estimate: round p95 up; no extra headroom assumed.
    capacity["capacity_est"] = np.ceil(
        capacity["legs_per_day_p95"]
    ).astype(int)
    capacity["capacity_unit"] = "outgoing_legs_per_day"
    capacity["capacity_method"] = "ceil_training_daily_outgoing_p95"

    # Replace only fields calculated by this script.
    replacement = [c for c in capacity.columns if c != "hub"]
    nodes = nodes.drop(columns=replacement, errors="ignore")
    nodes = nodes.merge(
        capacity, on="hub", how="left", validate="one_to_one"
    )

    # Keep existing columns for compatibility with the weather pipeline.
    if "state" not in nodes:
        nodes["state"] = nodes["name"].str.extract(
            r"\(([^()]*)\)\s*$", expand=False
        )

    nodes["lat"] = pd.to_numeric(nodes["latitude"], errors="coerce")
    nodes["lon"] = pd.to_numeric(nodes["longitude"], errors="coerce")

    # Statistics from training trips only.
    statistics = (
        legs.groupby(
            ["source_center", "destination_center"], as_index=False
        )
        .agg(
            trips=("trip_uuid", "nunique"),
            median_actual_time=("actual_time_min", "median"),
            median_ratio=("delay_ratio", "median"),
            p90_ratio=("delay_ratio", lambda x: x.quantile(0.90)),
            distance_km=("osrm_distance_km", "median"),
        )
    )

    keys = ["source_center", "destination_center"]
    replacement = [c for c in statistics.columns if c not in keys]

    edges = edges.drop(columns=replacement, errors="ignore")
    edges = edges.merge(
        statistics, on=keys, how="left", validate="one_to_one"
    )

    assert edges["trips"].notna().all()
    assert edges["trips"].eq(edges["trip_count"]).all()
    assert edges["trips"].ge(3).all()

    edges["source"] = edges["source_center"]
    edges["destination"] = edges["destination_center"]

    node_columns = [
        "hub", "name", "state", "lat", "lon",
        "legs_per_day_p95", "capacity_est",
    ]
    edge_columns = [
        "source", "destination", "trips", "median_actual_time",
        "median_ratio", "p90_ratio", "distance_km",
    ]

    nodes = nodes[
        node_columns + [c for c in nodes if c not in node_columns]
    ]
    edges = edges[
        edge_columns + [c for c in edges if c not in edge_columns]
    ]

    nodes.to_csv(PROCESSED / "core_nodes.csv", index=False)
    edges.to_csv(PROCESSED / "core_edges.csv", index=False)
    daily.to_csv(
        PROCESSED / "hub_daily_departures.csv", index=False
    )

    print("Updated core nodes:", len(nodes))
    print("Updated core edges:", len(edges))
    print("Capacity observation days:", len(days))
    print("Training departures counted:", len(observed))
    print("Training-trip legs outside capacity window:",
          len(legs) - len(observed))
    print("Hubs with zero estimated dispatch capacity:",
          int(nodes["capacity_est"].eq(0).sum()))

    print("\nCapacity summary (outgoing legs/day):")
    print(nodes["capacity_est"].describe())

    print("\nTop 10:")
    print(
        nodes.sort_values("capacity_est", ascending=False)
        [["hub", "name", "legs_per_day_p95", "capacity_est"]]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()