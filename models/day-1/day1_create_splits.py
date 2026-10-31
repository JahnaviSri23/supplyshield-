import pandas as pd
import json
from pathlib import Path

df = pd.read_csv("data/processed/legs.csv")

df["trip_creation_time"] = pd.to_datetime(
    df["trip_creation_time"]
)

trips = (
    df[["trip_uuid", "trip_creation_time"]]
    .drop_duplicates()
    .sort_values("trip_creation_time")
    .reset_index(drop=True)
)

total = len(trips)

train_end = int(total * 0.60)
cal_end = int(total * 0.80)

train_ids = set(trips.iloc[:train_end]["trip_uuid"])
cal_ids = set(trips.iloc[train_end:cal_end]["trip_uuid"])
test_ids = set(trips.iloc[cal_end:]["trip_uuid"])

train_df = df[df["trip_uuid"].isin(train_ids)].copy()
cal_df = df[df["trip_uuid"].isin(cal_ids)].copy()
test_df = df[df["trip_uuid"].isin(test_ids)].copy()

output_dir = Path("data/datasplit")
output_dir.mkdir(parents=True, exist_ok=True)

files = {
    "train_legs_v1.csv": train_df,
    "calibration_legs_v1.csv": cal_df,
    "test_legs_v1.csv": test_df
}

manifest_path = output_dir / "split_manifest_v1.json"

all_paths = [output_dir / name for name in files]
all_paths.append(manifest_path)

for path in all_paths:
    if path.exists():
        raise FileExistsError(
            f"{path} already exists. No files were overwritten."
        )

for filename, data in files.items():
    data.to_csv(output_dir / filename, index=False)

manifest = {
    "method": "chronological_trip_level_split",
    "split_ratio": {
        "train": 0.60,
        "calibration": 0.20,
        "test": 0.20
    },
    "total_trips": total,
    "total_legs": len(df),
    "partitions": {
        "train": {
            "trips": len(train_ids),
            "legs": len(train_df)
        },
        "calibration": {
            "trips": len(cal_ids),
            "legs": len(cal_df)
        },
        "test": {
            "trips": len(test_ids),
            "legs": len(test_df)
        }
    }
}

with open(manifest_path, "x") as file:
    json.dump(manifest, file, indent=4)

print("DATA SPLITS CREATED SUCCESSFULLY")

print(json.dumps(manifest, indent=4))

print("\nSaved files:")
for path in all_paths:
    print(path)