import pandas as pd

df = pd.read_csv("data/processed/legs.csv")

df["trip_creation_time"] = pd.to_datetime(df["trip_creation_time"])

trip_times = df.groupby("trip_uuid")["trip_creation_time"].nunique()

print("Trips with one creation time:", (trip_times == 1).sum())
print("Trips with multiple creation times:", (trip_times > 1).sum())
print("Maximum creation times per trip:", trip_times.max())