"""Reusable inference helpers for the frozen SupplyShield B02 model.

The request adapter accepts caller-computed, as-of lane history.  The feature
matrix scorer only sees the ordered model features and has no dependency on
the upstream source of lane history.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "residual_xgb_plain_master_split_v1.json"
CONFORMAL_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "day3"
    / "master_split_v2"
    / "final"
    / "conformal_params_method_c_master_split_v2.json"
)
REQUIRED_INPUTS = (
    "source_center",
    "destination_center",
    "route_type",
    "od_start_time",
    "osrm_time_min",
    "osrm_distance_km",
    "lane_base",
    "lane_history_count",
)
FEATURE_COLUMNS = (
    "osrm_time_min",
    "osrm_distance_km",
    "osrm_speed_kmh",
    "log_osrm_time",
    "start_hour",
    "start_dow",
    "is_weekend",
    "is_ftl",
    "lane_base",
    "lane_history_count",
)
FEATURE_TYPES = ("float", "float", "float", "float", "int", "int", "int", "int", "float", "int")
SUPPORTED_ROUTE_TYPES = frozenset({"FTL", "Carting"})
ZERO_HISTORY_BASE = 2.0
PINNED_XGBOOST_VERSION = "3.2.0"
_TARGET_FIELDS = frozenset(
    {
        "delay_ratio",
        "y_ratio",
        "travel_ratio",
        "target_ratio",
        "actual_ratio",
        "actual_time_ratio",
        "actual_time",
        "actual_time_min",
        "actual_travel_time",
        "actual_travel_time_min",
    }
)
_INTERVAL_LEVELS = ("50%", "80%", "90%")


def _resolve_path(path: str | Path | None, default: Path) -> Path:
    """Resolve an override or the repository-relative default artifact path."""
    return Path(path).expanduser().resolve() if path is not None else default.resolve()


def _as_records(rows: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        frame = rows.copy()
    elif isinstance(rows, Mapping):
        frame = pd.DataFrame([dict(rows)])
    else:
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            raise TypeError("rows must be a mapping, a DataFrame, or a sequence of mappings")
        if not rows:
            raise ValueError("At least one prediction row is required")
        if any(not isinstance(row, Mapping) for row in rows):
            raise TypeError("Every prediction row must be a mapping")
        frame = pd.DataFrame([dict(row) for row in rows])

    if frame.empty:
        raise ValueError("At least one prediction row is required")
    forbidden = sorted(
        name for name in map(str, frame.columns) if name.lower() in _TARGET_FIELDS
    )
    if forbidden:
        raise ValueError(f"Target/outcome columns cannot be prediction inputs: {forbidden}")
    missing = [name for name in REQUIRED_INPUTS if name not in frame.columns]
    if missing:
        raise ValueError(f"Missing required prediction fields: {missing}")
    # Preserve non-target identifiers/metadata for row matching and caller
    # traceability. Feature construction uses only REQUIRED_INPUTS.
    passthrough = [name for name in frame.columns if name not in REQUIRED_INPUTS]
    return frame.loc[:, list(REQUIRED_INPUTS) + passthrough].reset_index(drop=True)


def _finite_number(value: Any, field: str, row: int) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"Row {row}: {field} must be a numeric value, not {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Row {row}: {field} must be finite")
    return result


def validate_prediction_rows(
    rows: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    """Validate and normalize caller rows without reading lane history or targets.

    Timestamps are parsed with pandas, as in B02, without UTC conversion.
    Time features therefore use the timestamp's represented wall-clock time.
    """
    frame = _as_records(rows)
    raw_timestamps = frame["od_start_time"]
    if raw_timestamps.map(lambda value: isinstance(value, (bool, np.bool_, int, float, np.number))).any():
        raise ValueError("od_start_time values must be timestamps, not numbers")
    try:
        parsed_times = pd.to_datetime(raw_timestamps, errors="raise")
        # B02 uses the pandas .dt accessor on the parsed column.  Reject mixed
        # timezone/object results rather than guessing a timezone conversion.
        parsed_times.dt.hour
    except (TypeError, ValueError, OverflowError, AttributeError) as exc:
        raise ValueError("od_start_time values must parse as a B02-compatible timestamp column") from exc
    if parsed_times.isna().any():
        raise ValueError("od_start_time values must not be missing")
    normalized: list[dict[str, Any]] = []
    for i, (_, row) in enumerate(frame.iterrows()):
        item = row.to_dict()
        for key in ("source_center", "destination_center"):
            value = item[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Row {i}: {key} must be a non-empty string")
        route = item["route_type"]
        if not isinstance(route, str) or route not in SUPPORTED_ROUTE_TYPES:
            raise ValueError(
                f"Row {i}: route_type must be one of {sorted(SUPPORTED_ROUTE_TYPES)}"
            )
        parsed = parsed_times.iloc[i]

        numeric = {
            field: _finite_number(item[field], field, i)
            for field in ("osrm_time_min", "osrm_distance_km", "lane_base", "lane_history_count")
        }
        if numeric["osrm_time_min"] <= 0:
            raise ValueError(f"Row {i}: osrm_time_min must be greater than zero")
        if numeric["osrm_distance_km"] <= 0:
            raise ValueError(f"Row {i}: osrm_distance_km must be greater than zero")
        count_float = numeric["lane_history_count"]
        if count_float < 0 or not count_float.is_integer():
            raise ValueError(f"Row {i}: lane_history_count must be a non-negative integer")
        count = int(count_float)
        if count == 0 and numeric["lane_base"] != ZERO_HISTORY_BASE:
            raise ValueError(
                f"Row {i}: lane_base must be {ZERO_HISTORY_BASE} when lane_history_count is zero"
            )
        normalized.append(
            {
                "source_center": item["source_center"],
                "destination_center": item["destination_center"],
                "route_type": route,
                "od_start_time": parsed,
                "osrm_time_min": numeric["osrm_time_min"],
                "osrm_distance_km": numeric["osrm_distance_km"],
                "lane_base": numeric["lane_base"],
                "lane_history_count": count,
                **{
                    name: item[name]
                    for name in frame.columns
                    if name not in REQUIRED_INPUTS
                },
            }
        )
    return pd.DataFrame.from_records(normalized, columns=list(frame.columns))


def build_feature_matrix(
    rows: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    """Adapt and validate requests, then build B02's exact ordered features."""
    return _build_features_from_validated(validate_prediction_rows(rows))


def load_model(path: str | Path | None = None) -> xgb.Booster:
    """Load the frozen B02 JSON model and verify runtime and feature metadata."""
    if xgb.__version__ != PINNED_XGBOOST_VERSION:
        raise RuntimeError(
            f"This model requires xgboost=={PINNED_XGBOOST_VERSION}; "
            f"installed version is {xgb.__version__}"
        )
    model_path = _resolve_path(path, MODEL_PATH)
    if not model_path.is_file():
        raise FileNotFoundError(f"B02 model file not found: {model_path}")
    model = xgb.Booster()
    model.load_model(str(model_path))
    if tuple(model.feature_names or ()) != FEATURE_COLUMNS:
        raise ValueError("Saved model feature names/order do not match the B02 contract")
    if tuple(model.feature_types or ()) != FEATURE_TYPES:
        raise ValueError("Saved model feature types do not match the B02 contract")
    return model


def predict_residuals(feature_matrix: pd.DataFrame, model: xgb.Booster | None = None) -> np.ndarray:
    """Score a validated ten-feature matrix; return residual predictions only."""
    if not isinstance(feature_matrix, pd.DataFrame):
        raise TypeError("feature_matrix must be a pandas DataFrame")
    if tuple(feature_matrix.columns) != FEATURE_COLUMNS:
        raise ValueError("feature_matrix columns must exactly match the saved model order")
    if feature_matrix.empty:
        raise ValueError("feature_matrix must contain at least one row")
    values = feature_matrix.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("feature_matrix values must all be finite")
    active_model = model if model is not None else load_model()
    if tuple(active_model.feature_names or ()) != FEATURE_COLUMNS:
        raise ValueError("model feature names/order do not match the B02 contract")
    matrix = xgb.DMatrix(
        feature_matrix,
        feature_names=list(FEATURE_COLUMNS),
        feature_types=list(FEATURE_TYPES),
    )
    # B02's sklearn estimator honors early stopping by predicting only through
    # best_iteration.  Booster.predict defaults to all trees, so mirror it.
    best_iteration = active_model.attributes().get("best_iteration")
    iteration_range = (0, int(best_iteration) + 1) if best_iteration is not None else (0, 0)
    residuals = np.asarray(
        active_model.predict(matrix, iteration_range=iteration_range), dtype=float
    ).reshape(-1)
    if len(residuals) != len(feature_matrix) or not np.isfinite(residuals).all():
        raise ValueError("Model returned invalid residual predictions")
    return residuals


def load_conformal_parameters(path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate the saved B03 Method C calibration parameter JSON."""
    params_path = _resolve_path(path, CONFORMAL_PATH)
    if not params_path.is_file():
        raise FileNotFoundError(f"Method C parameter file not found: {params_path}")
    with params_path.open("r", encoding="utf-8") as stream:
        params = json.load(stream)
    edges = params.get("distance_edges_km")
    minimum = params.get("min_group_size")
    levels = params.get("levels")
    if (
        not isinstance(edges, list)
        or len(edges) != 2
        or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in edges)
        or edges[0] >= edges[1]
    ):
        raise ValueError("Method C parameters have invalid distance_edges_km")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("Method C parameters have invalid min_group_size")
    if not isinstance(levels, dict) or any(level not in levels for level in _INTERVAL_LEVELS):
        raise ValueError("Method C parameters must contain 50%, 80%, and 90% levels")
    for level in _INTERVAL_LEVELS:
        entry = levels[level]
        _validate_offsets(entry.get("global_offsets"), f"{level} global_offsets")
        offsets, counts = entry.get("group_offsets"), entry.get("group_counts")
        if not isinstance(offsets, dict) or not isinstance(counts, dict):
            raise ValueError(f"Method C parameters have invalid group data for {level}")
        for group, pair in offsets.items():
            _validate_offsets(pair, f"{level} group_offsets[{group!r}]")
        for group, count in counts.items():
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError(f"Method C parameters have invalid group count for {group!r}")
    return params


def _validate_offsets(offsets: Any, label: str) -> None:
    if (
        not isinstance(offsets, list)
        or len(offsets) != 2
        or any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in offsets)
    ):
        raise ValueError(f"Method C parameters have invalid {label}")


def apply_conformal_intervals(
    predictions: pd.DataFrame,
    parameters: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Add Method C ratio bounds to predictions without fitting calibration."""
    required = {"route_type", "osrm_distance_km", "pred_ratio"}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Missing fields for conformal intervals: {missing}")
    params = dict(parameters) if parameters is not None else load_conformal_parameters()
    edges = np.asarray(params["distance_edges_km"], dtype=float)
    minimum = int(params["min_group_size"])
    result = predictions.copy()
    route_types = result["route_type"].astype(str)
    distances = pd.to_numeric(result["osrm_distance_km"], errors="coerce").to_numpy(dtype=float)
    point = pd.to_numeric(result["pred_ratio"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(distances).all() or (distances <= 0).any():
        raise ValueError("osrm_distance_km must contain finite positive values")
    if not np.isfinite(point).all():
        raise ValueError("pred_ratio must contain finite values")
    buckets = np.asarray(["short", "medium", "long"], dtype=object)[
        np.searchsorted(edges, distances, side="left")
    ]
    groups = route_types.to_numpy(dtype=str) + "|" + buckets.astype(str)
    levels = params["levels"]
    for level in _INTERVAL_LEVELS:
        entry = levels[level]
        global_offsets = np.asarray(entry["global_offsets"], dtype=float)
        chosen: list[tuple[float, float]] = []
        for group in groups:
            count = entry["group_counts"].get(str(group), 0)
            pair = entry["group_offsets"].get(str(group))
            if pair is None or count < minimum:
                pair = global_offsets
            chosen.append((float(pair[0]), float(pair[1])))
        offsets = np.asarray(chosen, dtype=float)
        tag = level[:-1]
        result[f"lower_{tag}"] = np.maximum(0.0, point + offsets[:, 0])
        result[f"upper_{tag}"] = point + offsets[:, 1]
    return result


def predict_batch(
    rows: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    model: xgb.Booster | None = None,
    include_intervals: bool = False,
    conformal_parameters: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Predict one or more rows, preserving request order.

    The lane-history adapter is deliberately outside the core scorer: callers
    supply as-of ``lane_base`` and ``lane_history_count`` in each row.
    """
    normalized = validate_prediction_rows(rows)
    features = _build_features_from_validated(normalized)
    residuals = predict_residuals(features, model=model)
    result = normalized.copy()
    result["predicted_residual"] = residuals
    result["pred_ratio"] = result["lane_base"].to_numpy(dtype=float) + residuals
    result["predicted_travel_time_min"] = (
        result["pred_ratio"].to_numpy(dtype=float)
        * result["osrm_time_min"].to_numpy(dtype=float)
    )
    if include_intervals:
        result = apply_conformal_intervals(result, parameters=conformal_parameters)
    return result


def _build_features_from_validated(normalized: pd.DataFrame) -> pd.DataFrame:
    start = pd.Series(normalized["od_start_time"])
    features = pd.DataFrame(index=normalized.index)
    features["osrm_time_min"] = normalized["osrm_time_min"]
    features["osrm_distance_km"] = normalized["osrm_distance_km"]
    features["osrm_speed_kmh"] = normalized["osrm_distance_km"] / (
        normalized["osrm_time_min"] / 60.0
    )
    features["log_osrm_time"] = np.log1p(normalized["osrm_time_min"])
    features["start_hour"] = start.dt.hour.astype("int64")
    features["start_dow"] = start.dt.dayofweek.astype("int64")
    features["is_weekend"] = (start.dt.dayofweek >= 5).astype("int64")
    features["is_ftl"] = (normalized["route_type"] == "FTL").astype("int64")
    features["lane_base"] = normalized["lane_base"]
    features["lane_history_count"] = normalized["lane_history_count"].astype("int64")
    features = features.loc[:, list(FEATURE_COLUMNS)]
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("Derived feature values must all be finite")
    return features


def predict_single(
    row: Mapping[str, Any],
    *,
    model: xgb.Booster | None = None,
    include_intervals: bool = False,
    conformal_parameters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Predict one request row and return a plain dictionary."""
    result = predict_batch(
        row,
        model=model,
        include_intervals=include_intervals,
        conformal_parameters=conformal_parameters,
    )
    return result.iloc[0].to_dict()


__all__ = [
    "CONFORMAL_PATH",
    "FEATURE_COLUMNS",
    "FEATURE_TYPES",
    "MODEL_PATH",
    "REQUIRED_INPUTS",
    "ZERO_HISTORY_BASE",
    "apply_conformal_intervals",
    "build_feature_matrix",
    "load_conformal_parameters",
    "load_model",
    "predict_batch",
    "predict_residuals",
    "predict_single",
    "validate_prediction_rows",
]
