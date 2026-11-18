#!/usr/bin/env python
# coding: utf-8

# In[6]:


import json
from pathlib import Path
import pandas as pd

# Correct path pointing directly to experiments/day3/
json_path = Path("../experiments/day3/conformal_params_v2.json")

with open(json_path, "r") as f:
  conformal_params = json.load(f)

print("Conformal parameters loaded successfully from:", json_path)
print("Keys available:", list(conformal_params.keys()))


# In[8]:


import json
from pathlib import Path
import pandas as pd

# Load the saved XGBoost residual model artifact from models/
model_path = Path("../models/residual_xgb_plain_v1.json")

with open(model_path, "r") as f:
  model_data = json.load(f)

print("XGBoost residual model artifact loaded successfully from:", model_path)


# In[9]:


# Load conformal parameters from experiments/day3/
with open("../experiments/day3/conformal_params_v2.json", "r") as f:
  conformal_params = json.load(f)

# Load core network edges
core_edges = pd.read_csv("../data/processed/core_edges.csv")

print("Conformal parameters and core edges loaded successfully!")
print("Core edges shape:", core_edges.shape)
print("Core edges columns:", core_edges.columns.tolist())


# In[10]:


import numpy as np

# Prepare a list to store risk table rows
risk_rows = []

# Iterate through each core edge to compute predictions & conformal bounds
for idx, row in core_edges.iterrows():
  dist = row["distance_km"]
  median_time = row["median_actual_time"]
  trip_count = row["trip_count"]
  leg_count = row["leg_count"]

  # Use core_edges median_ratio as our baseline prediction
  pred_ratio = row["median_ratio"]

  # Apply conformal margins from your loaded conformal_params
  margin_50 = conformal_params.get("levels", {}).get("0.5", 0.05)
  margin_90 = conformal_params.get("levels", {}).get("0.9", 0.15)

  lo50 = max(0.0, pred_ratio - margin_50)
  hi50 = pred_ratio + margin_50
  lo90 = max(0.0, pred_ratio - margin_90)
  hi90 = pred_ratio + margin_90

  pred_excess_h = (pred_ratio - 1.0) * median_time
  excess_lo90_h = (lo90 - 1.0) * median_time
  excess_hi90_h = (hi90 - 1.0) * median_time

  risk_rows.append(
      {
          "source": row["source"],
          "destination": row["destination"],
          "source_center": row["source_center"],
          "destination_center": row["destination_center"],
          "leg_count": leg_count,
          "trip_count": trip_count,
          "distance_km": dist,
          "median_actual_time": median_time,
          "pred_ratio": round(pred_ratio, 4),
          "lo50": round(lo50, 4),
          "hi50": round(hi50, 4),
          "lo90": round(lo90, 4),
          "hi90": round(hi90, 4),
          "pred_excess_h": round(pred_excess_h, 4),
          "excess_lo90_h": round(excess_lo90_h, 4),
          "excess_hi90_h": round(excess_hi90_h, 4),
      }
  )

risk_table = pd.DataFrame(risk_rows)
print("Risk table generated successfully! Shape:", risk_table.shape)
display(risk_table.head())


# In[11]:


from pathlib import Path

# Ensure the day5 experiment directory exists
out_dir = Path("../experiments/day5")
out_dir.mkdir(parents=True, exist_ok=True)

# Save the risk table
out_path = out_dir / "risk_table.csv"
risk_table.to_csv(out_path, index=False)

print(f"Risk table successfully saved to: {out_path}")


# In[12]:


import pandas as pd

# Reload the risk table for verification
risk_df = pd.read_csv("../experiments/day5/risk_table.csv")

print("Risk Ratio Statistics Summary (Pred Ratio vs Median Actual):")
print(
    risk_df[["pred_ratio", "median_actual_time", "distance_km"]]
    .describe()
    .round(4)
)


# In[13]:


import pandas as pd
from pathlib import Path

# 1. Load core train legs and weather daily data
core_train_legs = pd.read_csv("../data/processed/core_train_legs.csv")
weather_daily = pd.read_csv("../data/processed/weather_daily.csv")

print("Core train legs shape:", core_train_legs.shape)
print("Weather daily shape:", weather_daily.shape)

# 2. Preview columns to verify join keys (e.g., hub/center and date)
print("Core train columns:", core_train_legs.columns.tolist()[:6])
print("Weather daily columns:", weather_daily.columns.tolist()[:6])


# In[14]:


# Convert timestamps to datetime format for merging
core_train_legs["date"] = pd.to_datetime(
    core_train_legs["trip_creation_time"]
).dt.strftime("%Y-%m-%d")
weather_daily["date"] = pd.to_datetime(weather_daily["date"]).dt.strftime(
    "%Y-%m-%d"
)

# Merge weather data onto core train legs using source hub and date
merged_train = pd.merge(
    core_train_legs,
    weather_daily,
    left_on=["source_center", "date"],
    right_on=["hub", "date"],
    how="left",
)

print("Merged core train legs with weather shape:", merged_train.shape)
print("Missing rain_mm values:", merged_train["rain_mm"].isna().sum())
display(merged_train[["trip_uuid", "source_center", "date", "rain_mm"]].head())


# In[19]:


import numpy as np
from sklearn.metrics import root_mean_squared_error

# Fill missing rain values with 0 (dry days)
merged_train["rain_mm"] = merged_train["rain_mm"].fillna(0)

# Check if target delay ratio column exists (or compute it)
# Let's inspect available columns to ensure we use the correct target name
print(
    "Target / delay columns available:",
    [c for c in merged_train.columns if "ratio" in c or "delay" in c],
)


# In[17]:


print(merged_train.columns.tolist())


# In[18]:


from sklearn.metrics import root_mean_squared_error
from sklearn.ensemble import RandomForestRegressor

# Fill missing values for the features and target
merged_train["rain_mm"] = merged_train["rain_mm"].fillna(0)
y = merged_train["delay_ratio"].fillna(1.0)

# Define feature sets using the exact column names available
features_base = ["osrm_distance_km", "osrm_time_min"]
features_weather = ["osrm_distance_km", "osrm_time_min", "rain_mm"]

X_base = merged_train[features_base].fillna(0)
X_weather = merged_train[features_weather].fillna(0)

# Train baseline vs weather-augmented models
rf_base = RandomForestRegressor(n_estimators=50, random_state=42)
rf_weather = RandomForestRegressor(n_estimators=50, random_state=42)

rf_base.fit(X_base, y)
rf_weather.fit(X_weather, y)

pred_base = rf_base.predict(X_base)
pred_weather = rf_weather.predict(X_weather)

rmse_base = root_mean_squared_error(y, pred_base)
rmse_weather = root_mean_squared_error(y, pred_weather)

print(f"RMSE without weather: {rmse_base:.4f}")
print(f"RMSE with weather (rain_mm): {rmse_weather:.4f}")
print(
    f"Improvement: {((rmse_base - rmse_weather) / rmse_base) * 100:.2f}% drop in error"
)


# In[20]:


from sklearn.metrics import root_mean_squared_error
from sklearn.ensemble import RandomForestRegressor

# Prepare features (with and without rain)
features_base = ["distance_km", "median_actual_time"]
features_weather = ["distance_km", "median_actual_time", "rain_mm"]

X_base = merged_train[features_base].fillna(0)
X_weather = merged_train[features_weather].fillna(0)
y = merged_train["delay_ratio"].fillna(1.0)

# Quick train/eval split or out-of-fold comparison
# Let's train a quick Random Forest baseline to check RMSE impact
rf_base = RandomForestRegressor(n_estimators=50, random_state=42)
rf_weather = RandomForestRegressor(n_estimators=50, random_state=42)

rf_base.fit(X_base, y)
rf_weather.fit(X_weather, y)

pred_base = rf_base.predict(X_base)
pred_weather = rf_weather.predict(X_weather)

rmse_base = root_mean_squared_error(y, pred_base)
rmse_weather = root_mean_squared_error(y, pred_weather)

print(f"RMSE without weather: {rmse_base:.4f}")
print(f"RMSE with weather (rain_mm): {rmse_weather:.4f}")
print(
    f"Improvement: {((rmse_base - rmse_weather) / rmse_base) * 100:.2f}% drop in"
    " error"
)

