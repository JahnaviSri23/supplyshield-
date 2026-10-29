from pathlib import Path

import numpy as np
import pandas as pd


def build_legs(data):
    """Combine scan records into journey legs."""
    data = data.drop_duplicates().copy()

    keys = [
        "trip_uuid",
        "source_center",
        "destination_center",
        "od_start_time",
        "od_end_time",
    ]

    missing_keys = data[keys].isna().any(axis=1)
    clean = data.loc[~missing_keys].copy()

    for column in ["actual_time", "osrm_time", "osrm_distance"]:
        clean[column] = pd.to_numeric(
            clean[column], errors="coerce"
        )

    legs = (
        clean.groupby(keys, as_index=False)
        .agg(
            trip_creation_time=("trip_creation_time", "first"),
            source_name=("source_name", "first"),
            destination_name=("destination_name", "first"),
            route_type=("route_type", "first"),
            actual_time_min=("actual_time", "max"),
            osrm_time_min=("osrm_time", "max"),
            osrm_distance_km=("osrm_distance", "max"),
            scan_rows=("trip_uuid", "size"),
        )
    )

    valid = (
        np.isfinite(legs["actual_time_min"])
        & np.isfinite(legs["osrm_time_min"])
        & (legs["actual_time_min"] >= 0)
        & (legs["osrm_time_min"] > 0)
    )

    legs["delay_ratio"] = np.nan

    legs.loc[valid, "delay_ratio"] = (
        legs.loc[valid, "actual_time_min"]
        / legs.loc[valid, "osrm_time_min"]
    )

    return legs


def build_lanes(legs):
    """Summarise journey legs by directed lane."""
    return (
        legs.groupby(
            ["source_center", "destination_center"],
            as_index=False
        )
        .agg(
            source_name=("source_name", "first"),
            destination_name=("destination_name", "first"),
            leg_count=("trip_uuid", "size"),
            trip_count=("trip_uuid", "nunique"),
            valid_ratio_count=("delay_ratio", "count"),
            median_delay_ratio=("delay_ratio", "median"),
            mean_delay_ratio=("delay_ratio", "mean"),
            median_distance_km=("osrm_distance_km", "median"),
        )
        .sort_values("trip_count", ascending=False)
    )


def main():
    root = Path(__file__).resolve().parents[1]
    raw_file = root / "data" / "raw" / "delhivery_data.csv"
    output_folder = root / "data" / "processed"
    output_folder.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(raw_file)
    legs = build_legs(data)
    lanes = build_lanes(legs)

    # Check against existing results before replacing them.
    for filename, generated, keys in [
        (
            "legs.csv",
            legs,
            [
                "trip_uuid", "source_center", "destination_center",
                "od_start_time", "od_end_time"
            ]
        ),
        (
            "lanes.csv",
            lanes,
            ["source_center", "destination_center"]
        ),
    ]:
        existing_path = output_folder / filename

        if existing_path.exists():
            existing = pd.read_csv(existing_path)

            pd.testing.assert_frame_equal(
                existing.sort_values(keys).reset_index(drop=True),
                generated.sort_values(keys).reset_index(drop=True),
                check_dtype=False,
                check_exact=False,
                rtol=1e-9,
                atol=1e-9
            )

            print(f"Verified: {filename} matches existing results.")

    legs.to_csv(output_folder / "legs.csv", index=False)
    lanes.to_csv(output_folder / "lanes.csv", index=False)

    print("Raw shape:", data.shape)
    print("Legs shape:", legs.shape)
    print("Lanes shape:", lanes.shape)
    print("Saved results in:", output_folder)


if __name__ == "__main__":
    main()