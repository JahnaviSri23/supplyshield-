import pandas as pd

df = pd.read_csv("data/processed/legs.csv")

df["od_start_time"] = pd.to_datetime(df["od_start_time"])

df = df.sort_values(["trip_uuid", "od_start_time"])

disconnected = 0
checked = 0

for trip_id, group in df.groupby("trip_uuid"):
    group = group.reset_index(drop=True)

    for i in range(len(group) - 1):
        checked += 1

        if group.loc[i, "destination_center"] != group.loc[i + 1, "source_center"]:
            disconnected += 1

print("Consecutive leg pairs checked:", checked)
print("Disconnected leg pairs:", disconnected)

import pandas as pd

df = pd.read_csv("data/processed/legs.csv")

df["od_start_time"] = pd.to_datetime(df["od_start_time"])

df = df.sort_values(["trip_uuid", "od_start_time"])

for trip_id, group in df.groupby("trip_uuid"):
    group = group.reset_index(drop=True)

    for i in range(len(group) - 1):
        if group.loc[i, "destination_center"] != group.loc[i + 1, "source_center"]:

            print("\nTrip:", trip_id)

            print(group.loc[
                [i, i + 1],
                ["source_center", "destination_center",
                 "od_start_time", "od_end_time"]
            ].to_string(index=False))

            break

    else:
        continue

    # Stop after five examples
    if 'examples' not in locals():
        examples = 0

    examples += 1

    if examples == 5:
        break