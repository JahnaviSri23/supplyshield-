import pandas as pd

CUT = pd.Timestamp("2018-09-26")

legs = pd.read_csv("data/processed/legs.csv", usecols=["trip_uuid", "trip_creation_time"])
legs["trip_creation_time"] = pd.to_datetime(legs["trip_creation_time"], errors="coerce")
trips = legs.groupby("trip_uuid", as_index=False)["trip_creation_time"].min().dropna()
trips = trips.sort_values(["trip_creation_time", "trip_uuid"]).reset_index(drop=True)

trips["split"] = "train"
rest = trips.index[trips["trip_creation_time"] >= CUT]
half = len(rest) // 2
trips.loc[rest[:half], "split"] = "calibration"
trips.loc[rest[half:], "split"] = "test"

legs_per_trip = legs.groupby("trip_uuid").size().rename("legs")
summary = (trips.join(legs_per_trip, on="trip_uuid").groupby("split")
           .agg(trips=("trip_uuid", "size"), legs=("legs", "sum"),
                first=("trip_creation_time", "min"), last=("trip_creation_time", "max")))
print(summary.reindex(["train", "calibration", "test"]).to_string())
trips.to_csv("data/processed/split_trip_ids.csv", index=False)
print("\nSaved data/processed/split_trip_ids.csv")
print("Expected: the train row should have about 17,674 legs (Person A's current training legs).")