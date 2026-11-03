from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

TRAIN_START = pd.Timestamp("2018-09-12")
TRAIN_END = pd.Timestamp("2018-09-26")  # Exclusive

GROUPS = ["route_type", "distance_bucket"]
BUCKETS = [
    "0–50 km",
    ">50–100 km",
    ">100–250 km",
    ">250–500 km",
    ">500 km",
]


def training_mask(data):
    """Only journeys whose outcomes were observed before the cutoff."""
    created = pd.to_datetime(
        data["trip_creation_time"], format="mixed", errors="coerce"
    )
    departure = pd.to_datetime(
        data["od_start_time"], format="mixed", errors="coerce"
    )
    arrival = pd.to_datetime(
        data["od_end_time"], format="mixed", errors="coerce"
    )

    return (
        created.ge(TRAIN_START)
        & created.lt(TRAIN_END)
        & departure.ge(TRAIN_START)
        & departure.lt(TRAIN_END)
        & arrival.ge(departure)
        & arrival.lt(TRAIN_END)
    )


def prepare_targets(data):
    """Calculate travel ratio and assign a distance bucket."""
    result = data.copy()

    actual = pd.to_numeric(result["actual_time_min"], errors="coerce")
    estimated = pd.to_numeric(result["osrm_time_min"], errors="coerce")
    distance = pd.to_numeric(result["osrm_distance_km"], errors="coerce")

    valid = (
        np.isfinite(actual)
        & actual.ge(0)
        & np.isfinite(estimated)
        & estimated.gt(0)
        & np.isfinite(distance)
        & distance.ge(0)
        & result["route_type"].notna()
    )

    result["travel_ratio"] = (
        actual / estimated.where(estimated.gt(0))
    ).where(valid)

    result["distance_bucket"] = pd.cut(
        distance,
        bins=[0, 50, 100, 250, 500, np.inf],
        labels=BUCKETS,
        include_lowest=True,
        right=True,
    ).astype("string")

    return result


def fit_baselines(data, minimum_legs=30):
    """Fit route-type × distance baselines using training outcomes only."""
    prepared = prepare_targets(data)

    reference = prepared.loc[
        training_mask(prepared)
        & prepared["travel_ratio"].notna()
    ]

    baselines = (
        reference.groupby(GROUPS, observed=True)["travel_ratio"]
        .agg(
            baseline_legs="size",
            baseline_median="median",
            baseline_p90=lambda values: values.quantile(0.90),
        )
        .reset_index()
    )

    # Too little evidence: leave targets unknown rather than guess.
    sparse = baselines["baseline_legs"].lt(minimum_legs)
    baselines.loc[
        sparse, ["baseline_median", "baseline_p90"]
    ] = np.nan

    return baselines


def apply_targets(data, baselines):
    """Apply frozen baselines; never refit on calibration or test data."""
    result = prepare_targets(data).merge(
        baselines,
        on=GROUPS,
        how="left",
        validate="many_to_one",
    )

    result["excess"] = (
        result["travel_ratio"] - result["baseline_median"]
    )

    known = (
        result["travel_ratio"].notna()
        & result["baseline_median"].notna()
        & result["baseline_p90"].notna()
    )

    result["disrupted"] = pd.Series(
        pd.NA, index=result.index, dtype="boolean"
    )
    result.loc[known, "disrupted"] = (
        result.loc[known, "travel_ratio"]
        > result.loc[known, "baseline_p90"]
    )

    return result


def main():
    # Fit on all eligible training legs, not only weather-covered legs.
    legs = pd.read_csv(PROCESSED / "legs.csv")
    enriched = pd.read_csv(PROCESSED / "legs_enriched.csv")

    baselines = fit_baselines(legs)
    targeted = apply_targets(enriched, baselines)

    baselines.to_csv(
        PROCESSED / "target_baselines.csv", index=False
    )
    targeted.to_csv(
        PROCESSED / "legs_targeted.csv", index=False
    )

    print("Training cutoff (exclusive):", TRAIN_END.date())
    print("\nTraining baselines:")
    print(baselines.round(4).to_string(index=False))

    print("\nCore journey legs:", len(targeted))
    print("Legs with targets:", targeted["disrupted"].notna().sum())
    print("Legs with unknown targets:", targeted["disrupted"].isna().sum())
    print("\nSaved: target_baselines.csv")
    print("Saved: legs_targeted.csv")


if __name__ == "__main__":
    main()