from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

TRAIN_START = pd.Timestamp("2018-09-12")
TRAIN_CUTOFF = pd.Timestamp("2018-09-26")

KEYS = ["source_center", "destination_center"]


def main():
    nodes = pd.read_csv(PROCESSED / "core_nodes.csv")
    edges = pd.read_csv(PROCESSED / "core_edges.csv")
    legs = pd.read_csv(PROCESSED / "core_train_legs.csv")

    assert nodes["hub"].is_unique
    assert not edges.duplicated(KEYS).any()

    created = pd.to_datetime(
        legs["trip_creation_time"], format="mixed", errors="raise"
    )
    starts = pd.to_datetime(
        legs["od_start_time"], format="mixed", errors="raise"
    )
    ends = pd.to_datetime(
        legs["od_end_time"], format="mixed", errors="coerce"
    )

    assert (
        created.ge(TRAIN_START) & created.lt(TRAIN_CUTOFF)
    ).all(), "Non-training trips found."

    # Dispatch counts use departure events within the training window.
    departure_mask = (
        starts.ge(TRAIN_START) & starts.lt(TRAIN_CUTOFF)
    )
    observed = legs.loc[departure_mask].copy()
    observed["departure_date"] = starts.loc[
        departure_mask
    ].dt.normalize()

    days = pd.date_range(
        TRAIN_START,
        TRAIN_CUTOFF - pd.Timedelta(days=1),
        freq="D",
    )

    full_index = pd.MultiIndex.from_product(
        [nodes["hub"], days], names=["hub", "date"]
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
            active_days=(
                "outgoing_legs",
                lambda values: int(values.gt(0).sum()),
            ),
            legs_per_day_p95=(
                "outgoing_legs",
                lambda values: values.quantile(
                    0.95, interpolation="linear"
                ),
            ),
        )
    )

    capacity["capacity_est"] = np.ceil(
        capacity["legs_per_day_p95"]
    ).astype(int)
    capacity["capacity_unit"] = "outgoing_legs_per_day"
    capacity["capacity_method"] = "ceil_training_daily_outgoing_p95"

    replacement = [c for c in capacity if c != "hub"]
    nodes = nodes.drop(columns=replacement, errors="ignore")
    nodes = nodes.merge(
        capacity, on="hub", how="left", validate="one_to_one"
    )

    if "state" not in nodes:
        nodes["state"] = nodes["name"].str.extract(
            r"\(([^()]*)\)\s*$", expand=False
        )

    nodes["lat"] = pd.to_numeric(
        nodes["latitude"], errors="coerce"
    )
    nodes["lon"] = pd.to_numeric(
        nodes["longitude"], errors="coerce"
    )

    valid_coordinates = (
        np.isfinite(nodes["lat"])
        & np.isfinite(nodes["lon"])
        & nodes["lat"].between(-90, 90)
        & nodes["lon"].between(-180, 180)
    )

    # Preserve coordinate_method and review_evidence as provenance.
    # Do not claim independent validation or exact warehouse accuracy.
    nodes["location_quality"] = np.where(
        valid_coordinates,
        "approximate_location_not_independently_validated",
        "unresolved",
    )
    nodes["warehouse_location_verified"] = False
    nodes["located"] = valid_coordinates

    if not valid_coordinates.all():
        nodes.loc[~valid_coordinates, ["lat", "lon"]] = np.nan

    # Historical membership counts remain separate from completed
    # training observations used to calculate travel statistics.
    membership = (
        legs.groupby(KEYS, as_index=False)
        .agg(trips=("trip_uuid", "nunique"))
    )

    actual = pd.to_numeric(
        legs["actual_time_min"], errors="coerce"
    )
    estimated = pd.to_numeric(
        legs["osrm_time_min"], errors="coerce"
    )
    distance = pd.to_numeric(
        legs["osrm_distance_km"], errors="coerce"
    )

    # Travel outcomes must have been observed before the cutoff.
    valid_statistics = (
        departure_mask
        & ends.ge(starts)
        & ends.lt(TRAIN_CUTOFF)
        & np.isfinite(actual)
        & actual.ge(0)
        & np.isfinite(estimated)
        & estimated.gt(0)
        & np.isfinite(distance)
        & distance.ge(0)
    )

    reference = legs.loc[valid_statistics, KEYS].copy()
    reference["actual_minutes"] = actual.loc[valid_statistics]
    reference["ratio"] = (
        actual.loc[valid_statistics]
        / estimated.loc[valid_statistics]
    )
    reference["distance"] = distance.loc[valid_statistics]

    statistics = (
        reference.groupby(KEYS, as_index=False)
        .agg(
            stats_legs=("ratio", "size"),
            median_actual_time=("actual_minutes", "median"),
            median_ratio=("ratio", "median"),
            p90_ratio=(
                "ratio",
                lambda values: values.quantile(
                    0.90, interpolation="linear"
                ),
            ),
            distance_km=("distance", "median"),
        )
    )

    calculated = [
        "source", "destination", "trips", "stats_legs",
        "median_actual_time", "median_ratio", "p90_ratio",
        "distance_km", "stats_cutoff_exclusive",
    ]

    edges = edges.drop(columns=calculated, errors="ignore")
    edges = edges.merge(
        membership, on=KEYS, how="left", validate="one_to_one"
    )
    edges = edges.merge(
        statistics, on=KEYS, how="left", validate="one_to_one"
    )

    edges["source"] = edges["source_center"]
    edges["destination"] = edges["destination_center"]
    edges["stats_legs"] = edges["stats_legs"].fillna(0).astype(int)
    edges["stats_cutoff_exclusive"] = str(TRAIN_CUTOFF.date())

    assert edges["trips"].notna().all()
    assert edges["trips"].eq(edges["trip_count"]).all()
    assert edges["trips"].ge(3).all()
    assert set(edges["source"]).issubset(set(nodes["hub"]))
    assert set(edges["destination"]).issubset(set(nodes["hub"]))

    node_first = [
        "hub", "name", "state", "lat", "lon",
        "location_quality", "warehouse_location_verified",
        "legs_per_day_p95", "capacity_est",
    ]
    edge_first = [
        "source", "destination", "trips",
        "median_actual_time", "median_ratio",
        "p90_ratio", "distance_km", "stats_legs",
        "stats_cutoff_exclusive",
    ]

    nodes = nodes[
        node_first + [c for c in nodes if c not in node_first]
    ]
    edges = edges[
        edge_first + [c for c in edges if c not in edge_first]
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
    print(
        "Training-trip departures outside window:",
        int((~departure_mask).sum()),
    )
    print(
        "Completed valid training legs for statistics:",
        len(reference),
    )
    print(
        "Edges without completed training statistics:",
        int(edges["stats_legs"].eq(0).sum()),
    )
    print(
        "Zero dispatch-capacity hubs:",
        int(nodes["capacity_est"].eq(0).sum()),
    )

    print("\nLocation quality:")
    print(nodes["location_quality"].value_counts().to_string())

    print("\nEdge preview:")
    print(edges[edge_first].head(3).to_string(index=False))


if __name__ == "__main__":
    main()