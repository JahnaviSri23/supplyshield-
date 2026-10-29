from pathlib import Path

import numpy as np
import pandas as pd


def distance_summary(legs):
    data = legs.copy()

    distance = pd.to_numeric(
        data["osrm_distance_km"], errors="coerce"
    )
    ratio = pd.to_numeric(
        data["delay_ratio"], errors="coerce"
    )

    valid = (
        np.isfinite(distance)
        & (distance >= 0)
        & np.isfinite(ratio)
        & (ratio >= 0)
    )

    print("Legs excluded for invalid distance or ratio:",
          int((~valid).sum()))

    data = data.loc[valid].copy()
    data["distance_km"] = distance.loc[valid]
    data["delay_ratio"] = ratio.loc[valid]

    data["distance_bucket"] = pd.cut(
        data["distance_km"],
        bins=[0, 50, 100, 250, 500, np.inf],
        labels=[
            "0–50 km",
            ">50–100 km",
            ">100–250 km",
            ">250–500 km",
            ">500 km"
        ],
        include_lowest=True,
        right=True
    )

    return (
        data.groupby("distance_bucket", observed=False)
        .agg(
            number_of_legs=("delay_ratio", "size"),
            median_ratio=("delay_ratio", "median"),
            mean_ratio=("delay_ratio", "mean"),
            p99_ratio=(
                "delay_ratio",
                lambda values: values.quantile(0.99)
            )
        )
        .reset_index()
    )


def main():
    root = Path(__file__).resolve().parents[1]
    processed = root / "data" / "processed"

    legs = pd.read_csv(processed / "legs.csv")
    summary = distance_summary(legs)

    output = processed / "distance_bucket_summary.csv"
    summary.to_csv(output, index=False)

    print("\nDISTANCE-BUCKET RESULTS — ALL JOURNEY LEGS")
    print(summary.round(6).to_string(index=False))
    print("\nSaved:", output)


if __name__ == "__main__":
    main()