from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

KEYS = [
    "trip_uuid",
    "source_center",
    "destination_center",
    "od_start_time",
    "od_end_time",
]


def main():
    legs = pd.read_csv(PROCESSED / "legs.csv")
    splits = pd.read_csv(
        PROCESSED / "split_trip_ids.csv",
        usecols=["trip_uuid", "split"],
    )
    weather = pd.read_csv(PROCESSED / "weather_daily.csv")

    if legs[KEYS].isna().any().any():
        raise ValueError("Missing journey identifiers.")

    if legs.duplicated(KEYS).any():
        raise ValueError("Duplicate journey identifiers.")

    if splits["trip_uuid"].isna().any():
        raise ValueError("Missing trip IDs in master split.")

    if not splits["trip_uuid"].is_unique:
        raise ValueError("Duplicate master split trip IDs.")

    if not splits["split"].isin(
        ["train", "calibration", "test"]
    ).all():
        raise ValueError("Invalid master split labels.")

    if set(legs["trip_uuid"]) != set(splits["trip_uuid"]):
        raise ValueError("Master split and legs contain different trips.")

    if not weather["weather_model"].eq("era5").all():
        raise ValueError("Unexpected weather model.")

    if not weather["timezone"].eq("Asia/Kolkata").all():
        raise ValueError("Unexpected weather timezone.")

    departure = pd.to_datetime(
        legs["od_start_time"],
        format="mixed",
        errors="raise",
    )

    # Current convention: naive journey timestamps are interpreted
    # as Asia/Kolkata local time. This remains an explicit assumption.
    if departure.dt.tz is not None:
        departure = departure.dt.tz_convert(
            "Asia/Kolkata"
        ).dt.tz_localize(None)

    legs["prediction_timestamp"] = departure
    legs["weather_reference_date"] = (
        departure.dt.normalize() - pd.Timedelta(days=1)
    )

    weather["weather_reference_date"] = pd.to_datetime(
        weather["date"], errors="raise"
    ).dt.normalize()

    if weather["hub"].isna().any():
        raise ValueError("Missing weather hub IDs.")

    if weather.duplicated(
        ["hub", "weather_reference_date"]
    ).any():
        raise ValueError("Duplicate hub/day weather records.")

    rain = pd.to_numeric(weather["rain_mm"], errors="coerce")
    valid_rain = np.isfinite(rain) & rain.ge(0)

    weather["source_rain_prev_day_mm"] = rain.where(valid_rain)
    weather["weather_row_present"] = True

    lookup = weather[
        [
            "hub",
            "weather_reference_date",
            "source_rain_prev_day_mm",
            "weather_row_present",
        ]
    ].rename(columns={"hub": "source_center"})

    # Export identifiers, split and weather only—not target labels.
    features = legs[
        KEYS + ["prediction_timestamp", "weather_reference_date"]
    ].merge(
        splits,
        on="trip_uuid",
        how="left",
        validate="many_to_one",
    )

    features = features.merge(
        lookup,
        on=["source_center", "weather_reference_date"],
        how="left",
        validate="many_to_one",
    )

    features["source_rain_prev_day_missing"] = (
        features["source_rain_prev_day_mm"].isna().astype(int)
    )

    features["weather_missing_reason"] = "available"

    missing = features["source_rain_prev_day_mm"].isna()
    row_present = features["weather_row_present"].eq(True)
    known_hub = features["source_center"].isin(weather["hub"])
    before_download = features["weather_reference_date"].lt(
        weather["weather_reference_date"].min()
    )

    features.loc[
        missing, "weather_missing_reason"
    ] = "hub_date_not_in_download"

    features.loc[
        missing & ~known_hub, "weather_missing_reason"
    ] = "source_hub_not_in_download"

    features.loc[
        missing & known_hub & before_download,
        "weather_missing_reason",
    ] = "date_before_download"

    features.loc[
        missing & row_present, "weather_missing_reason"
    ] = "invalid_or_missing_rain"

    features = features.drop(columns="weather_row_present")

    assert len(features) == len(legs)
    assert features["split"].notna().all()
    assert (
        features["weather_reference_date"]
        < features["prediction_timestamp"].dt.normalize()
    ).all()

    rows = []

    for split in ["train", "calibration", "test"]:
        subset = features.loc[features["split"].eq(split)]
        available = subset["source_rain_prev_day_mm"].notna()

        rows.append({
            "split": split,
            "legs": len(subset),
            "rain_available": int(available.sum()),
            "rain_missing": int((~available).sum()),
            "coverage_pct": round(100 * available.mean(), 2),
        })

    summary = pd.DataFrame(rows)

    features.to_csv(
        PROCESSED / "leg_weather_lag1.csv", index=False
    )
    summary.to_csv(
        PROCESSED / "weather_lag1_coverage.csv", index=False
    )

    print(summary.to_string(index=False))
    print("\nMissingness reasons:")
    print(
        features["weather_missing_reason"]
        .value_counts()
        .to_string()
    )

    print("\nPASS: All original legs and master split retained.")
    print("Lag: previous Asia/Kolkata calendar day at source hub.")
    print("Naive journey timestamps assumed to be local time.")
    print("Missing rain remains missing, not zero.")
    print("Historical reanalysis; real-time availability unverified.")
    print("\nSaved:")
    print("data/processed/leg_weather_lag1.csv")
    print("data/processed/weather_lag1_coverage.csv")


if __name__ == "__main__":
    main()