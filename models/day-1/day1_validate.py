
import pandas as pd

df = pd.read_csv("data/processed/legs.csv")

df["od_start_time"] = pd.to_datetime(df["od_start_time"])
df["od_end_time"] = pd.to_datetime(df["od_end_time"])

print("DATE RANGE")
print("Start:", df["od_start_time"].min())
print("End:", df["od_start_time"].max())

print("\nDUPLICATE CHECK")
print("Duplicate rows:", df.duplicated().sum())
print("Duplicate trip UUIDs:", df["trip_uuid"].duplicated().sum())

print("\nDURATION CHECK")
print("Zero OSRM times:", (df["osrm_time_min"] == 0).sum())
print("Zero actual times:", (df["actual_time_min"] == 0).sum())
print("Negative actual times:", (df["actual_time_min"] < 0).sum())

print("\nDELAY RATIO CHECK")
calculated_ratio = df["actual_time_min"] / df["osrm_time_min"]
print("Maximum ratio difference:",
      (calculated_ratio - df["delay_ratio"]).abs().max())
