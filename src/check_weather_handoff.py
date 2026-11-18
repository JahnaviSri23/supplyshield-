from pathlib import Path

import pandas as pd


DATA = Path(__file__).resolve().parents[1] / "data"

KEYS = [
    "trip_uuid",
    "source_center",
    "destination_center",
    "od_start_time",
    "od_end_time",
]
RAIN = ["source_rain_mm", "destination_rain_mm"]


def read_legs(path, columns):
    data = pd.read_csv(path, usecols=columns)

    for column in ["od_start_time", "od_end_time"]:
        data[column] = pd.to_datetime(
            data[column], format="mixed", errors="raise"
        )

    if data[KEYS].isna().any().any():
        raise ValueError(f"Missing leg identifiers: {path.name}")

    if data.duplicated(KEYS).any():
        raise ValueError(f"Duplicate leg identifiers: {path.name}")

    return data


def main():
    legs = read_legs(
        DATA / "processed/legs.csv",
        KEYS,
    )
    weather = read_legs(
        DATA / "processed/legs_enriched.csv",
        KEYS + RAIN,
    )
    splits = pd.read_csv(
        DATA / "processed/split_trip_ids.csv",
        usecols=["trip_uuid", "split"],
    )

    if splits["trip_uuid"].isna().any():
        raise ValueError("Missing trip IDs in master split.")

    if not splits["trip_uuid"].is_unique:
        raise ValueError("Duplicate trip IDs in master split.")

    if not splits["split"].isin(
        ["train", "calibration", "test"]
    ).all():
        raise ValueError("Invalid or missing master split labels.")

    if set(legs["trip_uuid"]) != set(splits["trip_uuid"]):
        raise ValueError("Legs and master split contain different trips.")

    assigned = legs.merge(
        splits,
        on="trip_uuid",
        how="left",
        validate="many_to_one",
    )

    # Verify every weather-export leg belongs to the original dataset.
    weather_check = weather[KEYS].merge(
        legs[KEYS],
        on=KEYS,
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not weather_check["_merge"].eq("both").all():
        raise ValueError("Some weather-export legs do not match legs.csv.")

    joined = assigned.merge(
        weather,
        on=KEYS,
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    assert len(joined) == len(legs)

    rows = []

    for split in ["train", "calibration", "test"]:
        subset = joined.loc[joined["split"].eq(split)]

        source = subset["source_rain_mm"].notna()
        destination = subset["destination_rain_mm"].notna()
        both = source & destination

        rows.append({
            "split": split,
            "trips": subset["trip_uuid"].nunique(),
            "total_legs": len(subset),
            "matched_to_weather_file": int(
                subset["_merge"].eq("both").sum()
            ),
            "source_rain_available": int(source.sum()),
            "destination_rain_available": int(destination.sum()),
            "both_endpoints_available": int(both.sum()),
            "both_endpoints_pct": (
                round(100 * both.mean(), 2)
                if len(subset) else float("nan")
            ),
        })

    summary = pd.DataFrame(rows)

    output = DATA / "processed/weather_master_split_coverage.csv"
    summary.to_csv(output, index=False)

    print(summary.to_string(index=False))
    print("\nPASS: Master split used; all original legs retained.")
    print("Saved:", output)
    print("Missing weather was not replaced with zero.")
    print("This is a coverage audit, not a prediction-feature export.")


if __name__ == "__main__":
    main()