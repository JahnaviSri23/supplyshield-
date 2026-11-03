import pandas as pd

df = pd.read_csv("data/processed/legs.csv")

for col in ["od_start_time", "od_end_time", "trip_creation_time"]:
    df[col] = pd.to_datetime(df[col])

trip = df[df["trip_uuid"] == "trip-153671066826362165"]

print("Trip creation time:")
print(trip["trip_creation_time"].to_string(index=False))

print("\nLeg start times:")
print(trip["od_start_time"].to_string(index=False))

print("\nLeg end times:")
print(trip["od_end_time"].to_string(index=False))

print("\nTotal trip duration (hours):")
print(
    (trip["od_end_time"].max() - trip["od_start_time"].min()).total_seconds() / 3600
)