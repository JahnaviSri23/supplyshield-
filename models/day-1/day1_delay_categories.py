import pandas as pd

df = pd.read_csv("data/processed/legs.csv")

df["delay_category"] = pd.cut(
    df["delay_ratio"],
    bins=[0, 1, 1.5, 2, 3, float("inf")],
    labels=[
        "On-time or faster",
        "Slight delay",
        "Moderate delay",
        "High delay",
        "Severe delay"
    ]
)

print("Delay category counts:")
print(df["delay_category"].value_counts().sort_index())

print("\nDelay category percentages:")
print(
    (df["delay_category"].value_counts(normalize=True).sort_index() * 100).round(2)
)