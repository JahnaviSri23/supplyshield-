import pandas as pd
import json
from pathlib import Path

df = pd.read_csv("data/processed/legs.csv")

df["trip_creation_time"] = pd.to_datetime(df["trip_creation_time"])

trips = (
    df[["trip_uuid", "trip_creation_time"]]
    .drop_duplicates()
    .sort_values("trip_creation_time")
    .reset_index(drop=True)
)

total = len(trips)

train_end = int(total * 0.60)
cal_end = int(total * 0.80)

train = trips.iloc[:train_end]
calibration = trips.iloc[train_end:cal_end]
test = trips.iloc[cal_end:]

summary = {
    "total_trips": total,
    "total_legs": len(df),
    "train": {
        "trips": len(train),
        "first_date": str(train["trip_creation_time"].min()),
        "last_date": str(train["trip_creation_time"].max())
    },
    "calibration": {
        "trips": len(calibration),
        "first_date": str(calibration["trip_creation_time"].min()),
        "last_date": str(calibration["trip_creation_time"].max())
    },
    "test": {
        "trips": len(test),
        "first_date": str(test["trip_creation_time"].min()),
        "last_date": str(test["trip_creation_time"].max())
    }
}

print(json.dumps(summary, indent=4))

output_dir = Path("experiments/day1")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "split_preview_v1.json"

if output_file.exists():
    raise FileExistsError(
        f"{output_file} already exists. Choose a new filename."
    )

with open(output_file, "x") as file:
    json.dump(summary, file, indent=4)

print("\nSplit preview saved successfully:", output_file)