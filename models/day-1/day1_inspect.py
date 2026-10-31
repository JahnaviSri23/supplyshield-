
import pandas as pd

df = pd.read_csv("data/processed/legs.csv")

print("Shape (rows, columns):", df.shape)

print("\nColumns and types:\n")
print(df.dtypes)

print("\nFirst 3 rows:\n")
print(df.head(3).T)

print("\nMissing values:\n")
print(df.isna().sum())

print("\nNumber summary:\n")
print(df.describe().T)
