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
CUTOFF = pd.Timestamp("2018-09-26")


def read_legs(path, columns):
    legs = pd.read_csv(path, usecols=columns)
    for col in ("od_start_time", "od_end_time"):
        legs[col] = pd.to_datetime(legs[col], format="mixed", errors="raise")

    if legs[KEYS].isna().any().any():
        raise ValueError(f"Missing leg identifiers in {path.name}")
    if legs.duplicated(KEYS).any():
        raise ValueError(f"Duplicate leg identifiers in {path.name}")

    return legs


def main():
    weather = read_legs(DATA / "processed" / "legs_enriched.csv", KEYS + RAIN)
    rows = []

    for split in ("train", "calibration", "test"):
        legs = read_legs(
            DATA / "datasplit" / f"{split}_legs_v1.csv",
            KEYS + ["trip_creation_time"],
        )
        created = pd.to_datetime(
            legs["trip_creation_time"], format="mixed", errors="raise"
        )

        joined = legs.merge(
            weather, on=KEYS, how="left", validate="one_to_one", indicator=True
        )
        matched = joined["_merge"].eq("both")
        source = joined["source_rain_mm"].notna()
        destination = joined["destination_rain_mm"].notna()
        both = source & destination

        rows.append({
            "B_split": split,
            "total_legs": len(legs),
            "matched_to_weather_file": int(matched.sum()),
            "matched_but_no_rain": int((matched & ~source & ~destination).sum()),
            "source_rain": int(source.sum()),
            "destination_rain": int(destination.sum()),
            "both_endpoints_rain": int(both.sum()),
            "both_endpoints_pct": round(100 * both.mean(), 2),
            "trip_created_before_A_cutoff": int(created.lt(CUTOFF).sum()),
        })

    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()