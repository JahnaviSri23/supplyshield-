# Person B Prediction API

## Purpose and architecture

`models/prediction_api.py` scores rows with the frozen B02 residual XGBoost model and can optionally attach the saved B03 Method C conformal interval bounds. It does not train or recalibrate a model.

The module has four layers:

1. `validate_prediction_rows` is the input adapter. It validates caller-supplied rows and normalizes the approved request fields.
2. `build_feature_matrix` maps those fields to B02's exact ten-feature order.
3. `predict_residuals` accepts only that validated, ordered feature matrix and a loaded Booster. `predict_batch` adds the residual to `lane_base`; `predict_single` is a one-row convenience wrapper.
4. `apply_conformal_intervals` optionally applies saved Method C offsets and remains separate from point scoring.

## Approved lane-history contract

The current API accepts precomputed as-of lane history. The core prediction engine is independent of the history source. Any future change to the upstream history integration should be handled through the input adapter and reviewed against the model's existing feature contract.

Each request row supplies `source_center`, `destination_center`, `route_type`, `od_start_time`, `osrm_time_min`, `osrm_distance_km`, `lane_base`, and `lane_history_count`. The caller is responsible for calculating directed-lane history as of departure. Only historical outcomes satisfying `historical od_end_time <= prediction od_start_time` may contribute. The API does not read historical outcome files, calculate lane medians, or calculate lane counts.

When `lane_history_count == 0`, `lane_base` must be exactly `2.0`. This is B02's fit-only median `g_fit`, established from 14,073 chronological fit legs. It is not derived from calibration or test targets. For positive history count, supply the caller's as-of lane median.

The scored row's target (`delay_ratio`, `y_ratio`, or equivalent) is forbidden as an input.

## Feature order and point prediction

The model file is `models/residual_xgb_plain_master_split_v1.json`. The feature matrix is built in this exact order:

1. `osrm_time_min`
2. `osrm_distance_km`
3. `osrm_speed_kmh` = `osrm_distance_km / (osrm_time_min / 60)`
4. `log_osrm_time` = `log1p(osrm_time_min)`
5. `start_hour` from `od_start_time`
6. `start_dow` from pandas day-of-week numbering (Monday = 0)
7. `is_weekend` = 1 when day of week is at least 5, otherwise 0
8. `is_ftl` = 1 for `FTL`, 0 for `Carting`
9. `lane_base` supplied by the caller
10. `lane_history_count` supplied by the caller

The point estimate is `pred_ratio = lane_base + predicted_residual`. Estimated travel time is `predicted_travel_time_min = pred_ratio * osrm_time_min`.

B02 calls `pandas.to_datetime` without UTC conversion. This API likewise does not normalize timestamps to UTC; hour and weekday use the timestamp's represented wall-clock time. Supply timestamps in the same time basis used for the model's source data.

## Request and response example

```python
from models.prediction_api import predict_batch, predict_single

row = {
    "source_center": "IND500008AAF",
    "destination_center": "IND500039AAC",
    "route_type": "FTL",
    "od_start_time": "2018-09-29 20:41:18.098697",
    "osrm_time_min": 120.0,
    "osrm_distance_km": 80.0,
    "lane_base": 2.0,
    "lane_history_count": 0,
}

one = predict_single(row, include_intervals=True)
many = predict_batch([row], include_intervals=True)
print(one["pred_ratio"], one["predicted_travel_time_min"])
print(many[["pred_ratio", "lower_90", "upper_90"]])
```

`predict_single` returns a dictionary. `predict_batch` returns a DataFrame in request order. Both include the eight normalized request fields, `predicted_residual`, `pred_ratio`, and `predicted_travel_time_min`. With `include_intervals=True`, they also include `lower_50`, `upper_50`, `lower_80`, `upper_80`, `lower_90`, and `upper_90`, all in delay-ratio units.

## Validation

The adapter rejects missing required fields, empty/non-string lane identifiers, route types other than `FTL` and `Carting`, invalid timestamps, nonfinite numeric fields, nonpositive OSRM time or distance, negative or fractional history counts, booleans as numeric values, target/outcome columns, and a zero-history baseline other than 2.0. It does not impute or substitute values.

## Conformal intervals and limitations

Intervals load from `experiments/day3/master_split_v2/final/conformal_params_method_c_master_split_v2.json`; the module does not hardcode offsets or refit calibration. The group is `route_type|distance_bucket`, using the saved calibration distance edges. A group-specific signed-residual offset pair is used when its saved calibration count is at least 200; otherwise the global offset pair is used, including for unseen groups.

For each saved level, `lower = max(0, pred_ratio + lower_offset)` and `upper = pred_ratio + upper_offset`; the upper endpoint is not clipped. Endpoints are ratios, not hours. These are the saved Method C split-conformal intervals; they are not lane-level guarantees or online coverage guarantees.

The prediction export includes a target column for historical evaluation, but the API does not load that file and rejects target fields in request rows. The caller must maintain the as-of history correctly. The frozen model and calibration parameters are specific to their recorded training/calibration workflow and should be reviewed if the feature or split process changes.

## Future adaptability

The current API accepts precomputed as-of lane history. The core prediction engine is independent of the history source. Any future change to the upstream history integration should be handled through the input adapter and reviewed against the model's existing feature contract.
