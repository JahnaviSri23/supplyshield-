import pandas as pd

df = pd.read_csv("data/processed/legs.csv")

df["od_start_time"] = pd.to_datetime(df["od_start_time"])
df["od_end_time"] = pd.to_datetime(df["od_end_time"])

trip = df[df["trip_uuid"] == "trip-153671041653548748"]

trip = trip.sort_values("od_start_time")

print(trip[
    ["source_center", "destination_center",
     "od_start_time", "od_end_time"]
].to_string(index=False))

print("\nChecking connection between consecutive legs:")

trip = trip.reset_index(drop=True)

for i in range(len(trip) - 1):
    print(
        "Leg", i + 1,
        "ends at:", trip.loc[i, "destination_center"],
        "| Next leg starts at:", trip.loc[i + 1, "source_center"]
    )