import pandas as pd
import numpy as np

df = pd.read_csv("data/processed/legs.csv")

target = df["delay_ratio"]

baseline_prediction = target.median()

errors = np.abs(target - baseline_prediction)

mae = errors.mean()

print("Baseline Prediction:", baseline_prediction)
print("Mean Absolute Error:", mae)