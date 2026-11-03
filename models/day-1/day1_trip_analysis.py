
import pandas as pd

df = pd.read_csv("data/processed/legs.csv")

trip_counts = df.groupby("trip_uuid").size()

print("Total unique trips:", df["trip_uuid"].nunique())

print("\nLegs per trip:")
print(trip_counts.describe())

print("\nTrips with multiple legs:", (trip_counts > 1).sum())

print("\nMaximum legs in one trip:", trip_counts.max())

print("\nExample trip with multiple legs:")

example_trip = trip_counts[trip_counts > 1].index[0]

print(
    df[df["trip_uuid"] == example_trip][
        ["source_center", "destination_center",
         "od_start_time", "od_end_time"]
    ]
)
