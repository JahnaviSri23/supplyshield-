"""Build and validate Person B's versioned Day 5 handoff artifacts.

Run from the repository root with ``python models/day5_final_pipeline.py --write``
once. Later runs use ``--check`` to reproduce calculations in memory and compare
the existing artifacts byte-for-byte. ``--refresh-generated`` is only allowed
when every existing output still matches this script's prior manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EDGE_KEYS = ["source_center", "destination_center"]
LEG_KEYS = ["trip_uuid", "source_center", "destination_center", "od_start_time"]
OUTPUTS = {
    "test_predictions": ROOT / "data/processed/preds_test_master_split_v1.csv",
    "risk_table": ROOT / "models/outputs/risk_table.csv",
    "realized_lanes": ROOT / "models/outputs/realized_test_lane_master_split_v2.csv",
    "interval_coverage": ROOT / "models/outputs/day5_test_interval_coverage_master_split_v1.csv",
    "lane_metrics": ROOT / "models/outputs/day5_lane_test_metrics_master_split_v1.csv",
    "model_comparison": ROOT / "models/outputs/day5_model_vs_baseline_master_split_v1.json",
    "manifest": ROOT / "models/outputs/day5_final_manifest_master_split_v1.json",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n", na_rep="").encode("utf-8")


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def q_signed(residuals: np.ndarray, alpha: float) -> tuple[float, float]:
    values = np.asarray(residuals, dtype=float)
    values = np.sort(values[np.isfinite(values)])
    if len(values) == 0:
        raise ValueError("Cannot calibrate an interval with no finite residuals")
    n = len(values)
    k_hi = min(int(np.ceil((n + 1) * (1 - alpha / 2))), n)
    k_lo = max(int(np.floor((n + 1) * alpha / 2)), 1)
    return float(values[k_lo - 1]), float(values[k_hi - 1])


def distance_bucket(values: pd.Series, edges: np.ndarray) -> pd.Series:
    return pd.cut(
        values,
        [-np.inf, float(edges[0]), float(edges[1]), np.inf],
        labels=["short", "medium", "long"],
        include_lowest=True,
    ).astype("object")


def add_method_c_group(frame: pd.DataFrame, edges: np.ndarray) -> pd.DataFrame:
    out = frame.copy()
    out["dist_bucket"] = distance_bucket(out["osrm_distance_km"], edges)
    out["grp"] = out["route_type"].astype(str) + "|" + out["dist_bucket"].astype(str)
    return out


def assert_equal_float(left: pd.Series, right: pd.Series, label: str, atol: float = 1e-12) -> None:
    a = left.to_numpy(dtype=float)
    b = right.to_numpy(dtype=float)
    if len(a) != len(b) or not np.allclose(a, b, rtol=0, atol=atol, equal_nan=False):
        raise AssertionError(f"{label} differs (max abs diff={np.max(np.abs(a-b)) if len(a) else 0})")


def metric_row(actual: pd.Series, predicted: pd.Series) -> dict[str, float | int]:
    y = actual.to_numpy(dtype=float)
    p = predicted.to_numpy(dtype=float)
    err = p - y
    return {
        "n_legs": int(len(y)),
        "missing_prediction_count": int(np.isnan(p).sum()),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
    }


def calculate() -> tuple[dict[str, bytes], dict[str, Any]]:
    data = ROOT / "data/processed"
    day3 = ROOT / "experiments/day3/master_split_v2"
    day5 = ROOT / "experiments/day5"
    inputs = {
        "split": data / "split_trip_ids.csv",
        "legs": data / "legs.csv",
        "core_edges": data / "core_edges.csv",
        "core_train_legs": data / "core_train_legs.csv",
        "predictions": data / "preds_cal_test_master_split_v1.csv",
        "legacy_predictions": data / "preds_test.csv",
        "legacy_lane_risk": ROOT / "models/outputs/risk_table_lane.csv",
        "legacy_realized_lanes": ROOT / "models/outputs/realized_test_lane.csv",
        "representatives": day5 / "risk_table_master_split_v1.csv",
        "day5_manifest": day5 / "risk_table_master_split_v1_manifest.json",
        "conformal_params": day3 / "final/conformal_params_method_c_master_split_v2.json",
        "test_intervals": day3 / "final/test_intervals_method_c_master_split_v2.csv",
        "day3_manifest": day3 / "run_manifest.json",
        "day3_success": day3 / "_SUCCESS.json",
        "model_card": ROOT / "experiments/day2/master_split/final_model_card_master_split_v1.json",
        "model": ROOT / "models/residual_xgb_plain_master_split_v1.json",
    }
    for path in inputs.values():
        if not path.is_file():
            raise FileNotFoundError(path)

    split = pd.read_csv(inputs["split"])
    legs = pd.read_csv(inputs["legs"], parse_dates=["od_start_time", "trip_creation_time", "od_end_time"])
    edges = pd.read_csv(inputs["core_edges"])
    core_train = pd.read_csv(inputs["core_train_legs"])
    predictions = pd.read_csv(inputs["predictions"], parse_dates=["od_start_time"])
    old_predictions = pd.read_csv(inputs["legacy_predictions"], parse_dates=["od_start_time"])
    legacy_lane_risk = pd.read_csv(inputs["legacy_lane_risk"])
    legacy_realized_lanes = pd.read_csv(inputs["legacy_realized_lanes"])
    representatives = pd.read_csv(inputs["representatives"])
    day5_manifest = json.loads(inputs["day5_manifest"].read_text(encoding="utf-8"))
    params = json.loads(inputs["conformal_params"].read_text(encoding="utf-8"))
    test_intervals = pd.read_csv(inputs["test_intervals"], parse_dates=["od_start_time"])
    day3_manifest = json.loads(inputs["day3_manifest"].read_text(encoding="utf-8"))
    day3_success = json.loads(inputs["day3_success"].read_text(encoding="utf-8"))
    model_card = json.loads(inputs["model_card"].read_text(encoding="utf-8"))

    if split["trip_uuid"].duplicated().any():
        raise AssertionError("Authoritative split contains duplicate trip IDs")
    if set(split["split"].unique()) != {"train", "calibration", "test"}:
        raise AssertionError("Authoritative split labels differ from train/calibration/test")
    split_map = split.set_index("trip_uuid")["split"]
    legs["split"] = legs["trip_uuid"].map(split_map)
    if legs["split"].isna().any():
        raise AssertionError("Some leg trip IDs are absent from the authoritative split")
    if day3_manifest.get("status") != "complete" or day3_success.get("status") != "complete":
        raise AssertionError("B03 conformal package is not marked complete")
    if model_card.get("split_source", "").replace("\\", "/") != "data/processed/split_trip_ids.csv":
        raise AssertionError("B02 model card does not name the authoritative split")
    if day5_manifest.get("artifact_sha256", "").lower() != sha256_file(inputs["representatives"]):
        raise AssertionError("B05 representative artifact hash does not match its manifest")

    train = legs.loc[legs["split"].eq("train")].copy()
    train_trip_dates = train.groupby("trip_uuid")["trip_creation_time"].min().sort_values()
    fit_trip_ids = set(train_trip_dates.index[: int(len(train_trip_dates) * 0.8)])
    fit_legs = train.loc[train["trip_uuid"].isin(fit_trip_ids)]
    validation_legs = train.loc[~train["trip_uuid"].isin(fit_trip_ids)]
    cal = predictions.loc[predictions["pile"].eq("cal")].copy()
    test = predictions.loc[predictions["pile"].eq("test")].copy()
    official_cal_ids = set(split.loc[split["split"].eq("calibration"), "trip_uuid"])
    official_test_ids = set(split.loc[split["split"].eq("test"), "trip_uuid"])
    train_ids = set(split.loc[split["split"].eq("train"), "trip_uuid"])
    if official_cal_ids & official_test_ids or train_ids & official_test_ids or train_ids & official_cal_ids:
        raise AssertionError("Official trip split partitions overlap")
    for pile, frame, expected in [("calibration", cal, official_cal_ids), ("test", test, official_test_ids)]:
        labels = frame["trip_uuid"].map(split_map)
        required_label = pile
        if labels.isna().any() or not labels.eq(required_label).all():
            raise AssertionError(f"{pile} prediction rows contain non-{pile} IDs")
        if set(frame["trip_uuid"]) != expected:
            raise AssertionError(f"{pile} prediction trip-ID set is incomplete or contains extras")
        if frame.duplicated(LEG_KEYS).any():
            raise AssertionError(f"{pile} predictions contain duplicate leg keys")

    official_test_legs = legs.loc[legs["split"].eq("test")].copy()
    official_cal_legs = legs.loc[legs["split"].eq("calibration")].copy()
    if len(test) != len(official_test_legs):
        raise AssertionError("Test prediction row count differs from official test legs")
    leg_join = official_test_legs[LEG_KEYS + ["delay_ratio", "route_type", "osrm_distance_km", "osrm_time_min", "trip_creation_time"]].merge(
        test[LEG_KEYS + ["pred_ratio", "base_pred", "y_ratio"]],
        on=LEG_KEYS,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not leg_join["_merge"].eq("both").all():
        raise AssertionError("B02 test predictions do not exactly cover official test legs")
    assert_equal_float(leg_join["delay_ratio"], leg_join["y_ratio"], "B02 test labels vs legs")

    # The legacy file is diagnosed, not used to train, calibrate or evaluate.
    legacy_ids = set(old_predictions["trip_uuid"])
    legacy_reconciliation = {
        "rows": int(len(old_predictions)),
        "unique_trip_ids": int(old_predictions["trip_uuid"].nunique()),
        "official_test_trip_ids": int(len(official_test_ids)),
        "prediction_trip_ids_in_official_test": int(len(legacy_ids & official_test_ids)),
        "non_test_trip_ids": int(len(legacy_ids - official_test_ids)),
        "missing_official_test_trip_ids": int(len(official_test_ids - legacy_ids)),
        "duplicate_trip_id_rows": int(old_predictions["trip_uuid"].duplicated(keep=False).sum()),
        "duplicate_trip_id_extra_rows": int(len(old_predictions) - old_predictions["trip_uuid"].nunique()),
        "duplicate_leg_key_rows": int(old_predictions.duplicated(LEG_KEYS).sum()),
        "rows_labelled_calibration_by_authoritative_split": int(old_predictions["trip_uuid"].map(split_map).eq("calibration").sum()),
        "rows_labelled_test_by_authoritative_split": int(old_predictions["trip_uuid"].map(split_map).eq("test").sum()),
        "date_min": str(old_predictions["od_start_time"].min()),
        "date_max": str(old_predictions["od_start_time"].max()),
        "interpretation": "superseded legacy export; not used as official current test predictions",
    }

    # Independently reproduce Method C calibration offsets using calibration rows only.
    params_edges = np.asarray(params["distance_edges_km"], dtype=float)
    cal_edges = cal["osrm_distance_km"].quantile([1 / 3, 2 / 3]).to_numpy(dtype=float)
    if not np.allclose(params_edges, cal_edges, rtol=0, atol=1e-12):
        raise AssertionError("Method C distance buckets are not reproduced from calibration features")
    if set(cal["trip_uuid"]) & set(test["trip_uuid"]):
        raise AssertionError("Calibration and test trip IDs overlap")
    cal["resid"] = cal["y_ratio"] - cal["pred_ratio"]
    cal_grouped = add_method_c_group(cal, params_edges)
    reconstructed_offsets: dict[str, dict[str, tuple[float, float]]] = {}
    reconstructed_global: dict[str, tuple[float, float]] = {}
    for level, info in params["levels"].items():
        alpha = float(info["alpha"])
        global_pair = q_signed(cal["resid"].to_numpy(dtype=float), alpha)
        if not np.allclose(global_pair, info["global_offsets"], rtol=0, atol=1e-12):
            raise AssertionError(f"Saved {level} global offsets do not reproduce from calibration residuals")
        group_pairs: dict[str, tuple[float, float]] = {}
        for group, group_frame in cal_grouped.groupby("grp", sort=False):
            pair = q_signed(group_frame["resid"].to_numpy(dtype=float), alpha) if len(group_frame) >= int(params["min_group_size"]) else global_pair
            group_pairs[str(group)] = pair
        if set(info["group_offsets"]) != set(group_pairs):
            raise AssertionError(f"Saved {level} group definitions differ from calibration groups")
        for group, pair in group_pairs.items():
            if not np.allclose(pair, info["group_offsets"][group], rtol=0, atol=1e-12):
                raise AssertionError(f"Saved {level} offset for {group} does not reproduce from calibration")
        reconstructed_offsets[level] = group_pairs
        reconstructed_global[level] = global_pair

    # Reapply calibration-only offsets to test predictions and compare the saved B03 artifact.
    test_grouped = add_method_c_group(test, params_edges)
    interval_columns: list[str] = []
    for level, info in params["levels"].items():
        tag = level.replace("%", "")
        pairs = [reconstructed_offsets[level].get(group, reconstructed_global[level]) for group in test_grouped["grp"]]
        lower_offset = np.asarray([pair[0] for pair in pairs], dtype=float)
        upper_offset = np.asarray([pair[1] for pair in pairs], dtype=float)
        test_grouped[f"lower_{tag}"] = np.clip(test_grouped["pred_ratio"].to_numpy(dtype=float) + lower_offset, 0, None)
        test_grouped[f"upper_{tag}"] = test_grouped["pred_ratio"].to_numpy(dtype=float) + upper_offset
        interval_columns.extend([f"lower_{tag}", f"upper_{tag}"])
    saved_intervals = test_intervals[LEG_KEYS + interval_columns + ["grp"]]
    intervals_join = test_grouped[LEG_KEYS + interval_columns + ["grp"]].merge(
        saved_intervals,
        on=LEG_KEYS,
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=("_reproduced", "_saved"),
    )
    if not intervals_join["_merge"].eq("both").all():
        raise AssertionError("Reconstructed Method C intervals do not match saved test interval rows")
    if not intervals_join["grp_reproduced"].eq(intervals_join["grp_saved"]).all():
        raise AssertionError("Saved Method C test groups differ from reconstructed groups")
    for column in interval_columns:
        assert_equal_float(intervals_join[f"{column}_reproduced"], intervals_join[f"{column}_saved"], f"saved B03 {column}")

    # Training-only baseline: lane median if n >= 3; otherwise route×train-distance group,
    # then global training median. All output risk-table lanes have sufficient history.
    # Validate the core training source is exactly training-labelled and contains no other split.
    core_train_source = pd.read_csv(ROOT / "data/processed/core_train_legs.csv")
    if not core_train_source["trip_uuid"].map(split_map).eq("train").all():
        raise AssertionError("core_train_legs contains non-training trips")
    edge_keys = set(map(tuple, edges[EDGE_KEYS].to_numpy()))
    if len(edge_keys) != 292 or edges.duplicated(EDGE_KEYS).any():
        raise AssertionError("Expected 292 unique directed core lanes")
    train_core = train.loc[
        [tuple(row) in edge_keys for row in train[EDGE_KEYS].to_numpy()]
    ].copy()
    if len(train_core) != len(core_train_source):
        raise AssertionError("Filtered master training legs differ from core_train_legs")
    source_keys = set(map(tuple, core_train_source[LEG_KEYS].astype(str).to_numpy()))
    master_core_keys = set(map(tuple, train_core[LEG_KEYS].astype(str).to_numpy()))
    if source_keys != master_core_keys:
        raise AssertionError("core_train_legs keys differ from authoritative master training legs")
    train_edges = train_core["osrm_distance_km"].quantile([1 / 3, 2 / 3]).to_numpy(dtype=float)
    train_core["__bucket"] = distance_bucket(train_core["osrm_distance_km"], train_edges)
    global_train_median = float(train_core["delay_ratio"].median())
    group_medians = train_core.groupby(["route_type", "__bucket"], observed=True)["delay_ratio"].median()
    lane_stats = train_core.groupby(EDGE_KEYS, sort=False).agg(
        n_train_legs=("delay_ratio", "size"), lane_median=("delay_ratio", "median"),
        lane_distance=("osrm_distance_km", "median"),
    )
    lane_routes = train_core.groupby(EDGE_KEYS, sort=False)["route_type"].agg(
        lambda s: sorted(s.dropna().value_counts().items(), key=lambda item: (-item[1], str(item[0])))[0][0]
    )

    rep_lanes = set(map(tuple, representatives[EDGE_KEYS].drop_duplicates().to_numpy()))
    if len(representatives) != 296 or representatives.duplicated(EDGE_KEYS + ["route_type"]).any() or rep_lanes != edge_keys:
        raise AssertionError("B05 representative source must contain 296 rows across all 292 core lanes")
    if not representatives["prediction_timestamp"].eq("2018-09-29 00:00:00").all():
        raise AssertionError("Representative predictions do not use the documented cutoff")
    if not representatives["representative_training_legs"].gt(0).all():
        raise AssertionError("Representative training weights must be positive")
    if day5_manifest.get("artifact_sha256", "").lower() != sha256_file(inputs["representatives"]):
        raise AssertionError("Representative predictions are not the manifested artifact")

    base_records = []
    for lane in sorted(edge_keys):
        n = int(lane_stats.loc[lane, "n_train_legs"]) if lane in lane_stats.index else 0
        lane_median = float(lane_stats.loc[lane, "lane_median"]) if lane in lane_stats.index else np.nan
        if n >= 3:
            base, source = lane_median, "lane"
        else:
            route = lane_routes.get(lane, None)
            dist = float(lane_stats.loc[lane, "lane_distance"]) if lane in lane_stats.index else np.nan
            if route is not None and np.isfinite(dist):
                bucket = distance_bucket(pd.Series([dist]), train_edges).iloc[0]
                group = (route, bucket)
                if group in group_medians.index and pd.notna(group_medians.loc[group]):
                    base, source = float(group_medians.loc[group]), "route_distance_group"
                else:
                    base, source = global_train_median, "global"
            else:
                base, source = global_train_median, "global"
        if not np.isfinite(base) or base <= 0:
            raise AssertionError(f"Invalid training baseline for {lane}: {base}")
        base_records.append({"source_center": lane[0], "destination_center": lane[1],
                             "baseline_ratio": base, "baseline_source": source,
                             "n_train_legs": n})
    baselines = pd.DataFrame(base_records)

    weighted_fields = ["pred_ratio", "lo50", "hi50", "lo90", "hi90", "pred_excess_h"]
    for col in weighted_fields:
        if col not in representatives or not np.isfinite(representatives[col].to_numpy(dtype=float)).all():
            raise AssertionError(f"Representative source has missing or non-finite {col}")
    if not np.allclose(
        representatives["pred_excess_h"],
        (representatives["pred_ratio"] - 1) * representatives["osrm_time_h"],
        rtol=0,
        atol=1e-12,
    ):
        raise AssertionError("pred_excess_h does not equal excess over OSRM time in hours")
    aggregate_rows = []
    for lane, frame in representatives.groupby(EDGE_KEYS, sort=False):
        weights = frame["representative_training_legs"].to_numpy(dtype=float)
        row = {key: lane[i] for i, key in enumerate(EDGE_KEYS)}
        for col in weighted_fields:
            row[col] = float(np.average(frame[col].to_numpy(dtype=float), weights=weights))
        row["representative_route_rows"] = int(len(frame))
        row["representative_training_legs"] = int(weights.sum())
        aggregate_rows.append(row)
    risk = baselines.merge(pd.DataFrame(aggregate_rows), on=EDGE_KEYS, how="inner", validate="one_to_one")
    risk["pred_multiplier"] = risk["pred_ratio"] / risk["baseline_ratio"]
    for tag in ["50", "90"]:
        risk[f"lo{tag}_multiplier"] = risk[f"lo{tag}"] / risk["baseline_ratio"]
        risk[f"hi{tag}_multiplier"] = risk[f"hi{tag}"] / risk["baseline_ratio"]
    # Backward-compatible columns from risk_table_lane.csv remain available.
    risk["lane_base"] = risk["baseline_ratio"]
    risk["base_source"] = risk["baseline_source"]
    risk["mult_pred"] = risk["pred_multiplier"]
    risk["mult_lo90"] = risk["lo90_multiplier"]
    risk["mult_hi90"] = risk["hi90_multiplier"]
    risk["mult_lo50"] = risk["lo50_multiplier"]
    risk["mult_hi50"] = risk["hi50_multiplier"]
    risk = risk.sort_values(EDGE_KEYS, kind="mergesort").reset_index(drop=True)
    if len(risk) != 292 or set(map(tuple, risk[EDGE_KEYS].to_numpy())) != edge_keys:
        raise AssertionError("Canonical risk table does not cover the 292 core lanes")
    if not risk[["baseline_ratio", "pred_ratio", "lo50", "hi50", "lo90", "hi90"]].apply(np.isfinite).all().all():
        raise AssertionError("Canonical risk table has non-finite values")
    if risk.isna().any().any() or (risk["baseline_ratio"] <= 0).any():
        raise AssertionError("Canonical risk table has missing values or nonpositive baselines")
    for tag in ["50", "90"]:
        if not (risk[f"lo{tag}"].ge(0) & risk[f"lo{tag}"].le(risk["pred_ratio"]) & risk["pred_ratio"].le(risk[f"hi{tag}"])).all():
            raise AssertionError(f"Canonical {tag}% representative interval bounds do not enclose point predictions")
    if not (risk["lo90"].le(risk["lo50"]) & risk["hi50"].le(risk["hi90"])).all():
        raise AssertionError("Canonical representative 50% bounds are not nested inside 90% bounds")
    legacy_risk_projection = risk.sort_values(EDGE_KEYS)[[
        "source_center", "destination_center", "lane_base", "base_source", "n_train_legs",
        "mult_pred", "mult_lo90", "mult_hi90", "mult_lo50", "mult_hi50",
    ]].reset_index(drop=True)
    legacy_risk_sorted = legacy_lane_risk.sort_values(EDGE_KEYS).reset_index(drop=True)
    if not legacy_risk_projection[EDGE_KEYS].equals(legacy_risk_sorted[EDGE_KEYS]):
        raise AssertionError("Expanded canonical table does not preserve legacy lane keys")
    for col in ["n_train_legs", "mult_pred", "mult_lo90", "mult_hi90", "mult_lo50", "mult_hi50"]:
        assert_equal_float(legacy_risk_projection[col], legacy_risk_sorted[col], f"legacy risk table projection {col}")
    if not legacy_risk_projection[["base_source"]].equals(legacy_risk_sorted[["base_source"]]):
        raise AssertionError("Expanded canonical table base_source differs from preserved legacy output")

    # Same official test legs for the model and fixed training-only lane-history baseline.
    eval_frame = leg_join.drop(columns="_merge").copy()
    evaluation_train_edges = train["osrm_distance_km"].quantile([1 / 3, 2 / 3]).to_numpy(dtype=float)
    eval_frame["__bucket"] = distance_bucket(eval_frame["osrm_distance_km"], evaluation_train_edges)
    lane_all_stats = train.groupby(EDGE_KEYS).agg(
        n=("delay_ratio", "size"), median=("delay_ratio", "median")
    )
    all_train_group_medians = train.assign(__bucket=distance_bucket(train["osrm_distance_km"], evaluation_train_edges)).groupby(
        ["route_type", "__bucket"], observed=True
    )["delay_ratio"].median()
    global_all_train_median = float(train["delay_ratio"].median())
    baseline_values = []
    baseline_sources = []
    for _, row in eval_frame.iterrows():
        lane = (row["source_center"], row["destination_center"])
        if lane in lane_all_stats.index and int(lane_all_stats.loc[lane, "n"]) >= 3:
            value, source = float(lane_all_stats.loc[lane, "median"]), "lane"
        else:
            key = (row["route_type"], row["__bucket"])
            if key in all_train_group_medians.index and pd.notna(all_train_group_medians.loc[key]):
                value, source = float(all_train_group_medians.loc[key]), "route_distance_group"
            else:
                value, source = global_all_train_median, "global"
        baseline_values.append(value)
        baseline_sources.append(source)
    eval_frame["baseline_ratio"] = baseline_values
    eval_frame["baseline_source"] = baseline_sources
    interval_eval = eval_frame[LEG_KEYS].merge(
        intervals_join[LEG_KEYS + ["lower_50_reproduced", "upper_50_reproduced", "lower_90_reproduced", "upper_90_reproduced"]],
        on=LEG_KEYS,
        how="left",
        validate="one_to_one",
    )
    if interval_eval.isna().any().any():
        raise AssertionError("Official test rows are missing reconstructed interval bounds")
    for col in ["lower_50", "upper_50", "lower_90", "upper_90"]:
        eval_frame[col] = interval_eval[f"{col}_reproduced"].to_numpy(dtype=float)
    model_metrics = metric_row(eval_frame["delay_ratio"], eval_frame["pred_ratio"])
    baseline_metrics = metric_row(eval_frame["delay_ratio"], eval_frame["baseline_ratio"])
    lane_coverage = int(eval_frame.loc[eval_frame["pred_ratio"].notna(), EDGE_KEYS].drop_duplicates().shape[0])
    all_test_lanes = int(eval_frame[EDGE_KEYS].drop_duplicates().shape[0])
    late_calibration_ends = int((official_cal_legs["od_end_time"] > official_test_legs["od_start_time"].min()).sum())

    overall_interval_rows = []
    for level, tag in [("50%", "50"), ("90%", "90")]:
        lo, hi = eval_frame[f"lower_{tag}"], eval_frame[f"upper_{tag}"]
        covered = eval_frame["delay_ratio"].between(lo, hi, inclusive="both")
        width = hi - lo
        overall_interval_rows.append({
            "level": level,
            "nominal_coverage": float(level.rstrip("%")) / 100,
            "covered_test_legs": int(covered.sum()),
            "test_legs": int(len(eval_frame)),
            "empirical_coverage": float(covered.mean()),
            "mean_width_ratio": float(width.mean()),
            "median_width_ratio": float(width.median()),
            "mean_width_min": float((width * eval_frame["osrm_time_min"]).mean()),
            "calibration_split_rows": int(len(cal)),
            "calibration_split_trips": int(cal["trip_uuid"].nunique()),
        })
    coverage_table = pd.DataFrame(overall_interval_rows)

    eval_frame["covered50"] = eval_frame["delay_ratio"].between(eval_frame["lower_50"], eval_frame["upper_50"], inclusive="both")
    eval_frame["covered90"] = eval_frame["delay_ratio"].between(eval_frame["lower_90"], eval_frame["upper_90"], inclusive="both")
    eval_frame["width90"] = eval_frame["upper_90"] - eval_frame["lower_90"]
    eval_frame["model_abs_error"] = (eval_frame["pred_ratio"] - eval_frame["delay_ratio"]).abs()
    eval_frame["model_sq_error"] = (eval_frame["pred_ratio"] - eval_frame["delay_ratio"]) ** 2
    eval_frame["baseline_abs_error"] = (eval_frame["baseline_ratio"] - eval_frame["delay_ratio"]).abs()
    eval_frame["baseline_sq_error"] = (eval_frame["baseline_ratio"] - eval_frame["delay_ratio"]) ** 2
    lane_metrics = eval_frame.groupby(EDGE_KEYS, sort=True).agg(
        test_legs=("trip_uuid", "size"),
        test_trips=("trip_uuid", "nunique"),
        model_mae=("model_abs_error", "mean"),
        model_rmse=("model_sq_error", lambda x: float(np.sqrt(x.mean()))),
        baseline_mae=("baseline_abs_error", "mean"),
        baseline_rmse=("baseline_sq_error", lambda x: float(np.sqrt(x.mean()))),
        coverage50=("covered50", "mean"),
        coverage90=("covered90", "mean"),
        mean_width90_ratio=("width90", "mean"),
    ).reset_index()

    # Evaluation-only realization table over every core edge, including lanes with zero test legs.
    core_test_legs = official_test_legs.loc[
        [tuple(row) in edge_keys for row in official_test_legs[EDGE_KEYS].to_numpy()]
    ].copy()
    realized = core_test_legs.groupby(EDGE_KEYS, sort=True).agg(
        test_leg_count=("trip_uuid", "size"),
        test_trip_count=("trip_uuid", "nunique"),
        realized_mean_delay_ratio=("delay_ratio", "mean"),
        test_start_min=("od_start_time", "min"),
        test_start_max=("od_start_time", "max"),
    ).reset_index()
    realized = edges[EDGE_KEYS].sort_values(EDGE_KEYS).merge(realized, on=EDGE_KEYS, how="left", validate="one_to_one")
    realized["test_leg_count"] = realized["test_leg_count"].fillna(0).astype(int)
    realized["test_trip_count"] = realized["test_trip_count"].fillna(0).astype(int)
    realized = realized.merge(risk[EDGE_KEYS + ["baseline_ratio"]], on=EDGE_KEYS, validate="one_to_one")
    realized["realized_multiplier"] = realized["realized_mean_delay_ratio"] / realized["baseline_ratio"]
    realized = realized.drop(columns="baseline_ratio")
    legacy_realized_projection = realized.loc[realized["test_leg_count"].ge(5), [
        "source_center", "destination_center", "test_leg_count", "realized_mean_delay_ratio", "realized_multiplier",
    ]].rename(columns={
        "test_leg_count": "n_test_legs",
        "realized_mean_delay_ratio": "realized_ratio_mean",
        "realized_multiplier": "realized_mult",
    }).sort_values(EDGE_KEYS).reset_index(drop=True)
    legacy_realized_sorted = legacy_realized_lanes.sort_values(EDGE_KEYS).reset_index(drop=True)
    if len(legacy_realized_projection) != len(legacy_realized_sorted) or not legacy_realized_projection[EDGE_KEYS].equals(legacy_realized_sorted[EDGE_KEYS]):
        raise AssertionError("Full realization does not project to the preserved >=5-leg legacy file")
    for col in ["n_test_legs", "realized_ratio_mean", "realized_mult"]:
        assert_equal_float(legacy_realized_projection[col], legacy_realized_sorted[col], f"legacy realized output projection {col}")

    comparison = {
        "split_source": "data/processed/split_trip_ids.csv",
        "prediction_source": "data/processed/preds_cal_test_master_split_v1.csv (pile=test)",
        "model_definition": {
            "type": model_card["final_model"],
            "model_file": model_card["model_file"],
            "model_version": "XGBoost 3.2.0 per B05 runtime parity assertion",
            "best_iteration": int(model_card["best_iteration"]),
            "features": model_card["features"],
            "fit_partition": {
                "trip_count": int(fit_legs["trip_uuid"].nunique()),
                "leg_count": int(len(fit_legs)),
                "trip_creation_min": str(fit_legs["trip_creation_time"].min()),
                "trip_creation_max": str(fit_legs["trip_creation_time"].max()),
            },
            "validation_partition": {
                "trip_count": int(validation_legs["trip_uuid"].nunique()),
                "leg_count": int(len(validation_legs)),
                "trip_creation_min": str(validation_legs["trip_creation_time"].min()),
                "trip_creation_max": str(validation_legs["trip_creation_time"].max()),
            },
            "split_source": "official train partition, sorted by trip_creation_time; first 80% fit, later 20% validation",
            "prediction_granularity": "one scored leg row per unique trip_uuid, directed lane, and od_start_time",
        },
        "official_test_legs": int(len(eval_frame)),
        "official_test_trips": int(eval_frame["trip_uuid"].nunique()),
        "official_test_trip_id_extra_rows": int(len(eval_frame) - eval_frame["trip_uuid"].nunique()),
        "official_test_rows_in_repeated_trip_ids": int(eval_frame["trip_uuid"].duplicated(keep=False).sum()),
        "official_test_duplicate_leg_key_rows": int(eval_frame.duplicated(LEG_KEYS).sum()),
        "official_test_unique_lanes": all_test_lanes,
        "model_prediction_missing_count": int(eval_frame["pred_ratio"].isna().sum()),
        "model_prediction_lane_coverage": int(lane_coverage),
        "model_prediction_lane_coverage_fraction": float(lane_coverage / all_test_lanes),
        "baseline_sources": {str(k): int(v) for k, v in eval_frame["baseline_source"].value_counts().sort_index().items()},
        "model": model_metrics,
        "training_only_lane_history_baseline": baseline_metrics,
        "model_beats_training_only_baseline": bool(
            model_metrics["mae"] < baseline_metrics["mae"] and model_metrics["rmse"] < baseline_metrics["rmse"]
        ),
        "baseline_policy": "training lane median for n>=3; otherwise training route_type x training-distance-tercile median; otherwise global training median",
        "test_outcomes_used_for_model_or_baseline": False,
    }

    test_export = test.sort_values(LEG_KEYS, kind="mergesort").reset_index(drop=True)
    risk = risk[[
        "source_center", "destination_center", "baseline_ratio", "baseline_source", "n_train_legs",
        "pred_ratio", "lo50", "hi50", "lo90", "hi90",
        "pred_multiplier", "lo50_multiplier", "hi50_multiplier", "lo90_multiplier", "hi90_multiplier",
        "pred_excess_h", "representative_route_rows", "representative_training_legs",
        "lane_base", "base_source", "mult_pred", "mult_lo90", "mult_hi90", "mult_lo50", "mult_hi50",
    ]]

    frames = {
        "test_predictions": test_export,
        "risk_table": risk,
        "realized_lanes": realized,
        "interval_coverage": coverage_table,
        "lane_metrics": lane_metrics,
    }
    payloads = {name: csv_bytes(frame) for name, frame in frames.items()}
    comparison.update({
        "test_date_min": str(eval_frame["od_start_time"].min()),
        "test_date_max": str(eval_frame["od_start_time"].max()),
        "calibration_trip_creation_max": str(official_cal_legs["trip_creation_time"].max()),
        "calibration_leg_outcome_end_max": str(official_cal_legs["od_end_time"].max()),
        "calibration_legs_finishing_after_first_test_start": late_calibration_ends,
        "temporal_interpretation": f"held-out trip-partition evaluation; {late_calibration_ends} calibration leg outcomes finish after the earliest test leg start, so these static offsets are not a per-test-time online calibration guarantee",
        "interval_method": params["method"],
        "interval_calibration_source": "calibration rows from authoritative B02 master-split prediction file only",
        "interval_bounds_are_lane_level_guarantees": False,
        "realized_core_lanes_with_any_test_legs": int(realized["test_leg_count"].gt(0).sum()),
        "realized_core_lanes_with_at_least_five_test_legs": int(realized["test_leg_count"].ge(5).sum()),
        "realized_core_lanes_with_zero_test_legs": int(realized["test_leg_count"].eq(0).sum()),
        "legacy_preds_test_reconciliation": legacy_reconciliation,
    })
    payloads["model_comparison"] = json_bytes(comparison)

    input_hashes = {name: sha256_file(path) for name, path in inputs.items()}
    output_hashes = {name: sha256_bytes(payload) for name, payload in payloads.items()}
    manifest = {
        "status": "complete",
        "version": "day5_final_master_split_v1",
        "split_source": "data/processed/split_trip_ids.csv",
        "input_sha256": input_hashes,
        "outputs": {
            name: {"path": str(OUTPUTS[name].relative_to(ROOT)), "sha256": output_hashes[name],
                   "rows": int(len(frames[name])) if name in frames else None}
            for name in payloads
        },
        "risk_table_schema": list(risk.columns),
        "realized_lane_schema": list(realized.columns),
        "model_vs_baseline": comparison,
        "interval_coverage": coverage_table.to_dict(orient="records"),
    }
    payloads["manifest"] = json_bytes(manifest)

    # All semantic checks are complete before any output is written.
    if len(test_export) != 4394 or test_export["trip_uuid"].map(split_map).ne("test").any():
        raise AssertionError("Test-only export failed official split validation")
    if len(risk) != 292 or len(realized) != 292:
        raise AssertionError("Risk and realized output must each contain all 292 directed core lanes")
    if int(realized["test_leg_count"].sum()) != len(core_test_legs):
        raise AssertionError("Realized per-lane counts do not sum to official core test legs")
    if int(realized["test_leg_count"].eq(0).sum()) != 66:
        raise AssertionError("Unexpected number of core lanes with zero official test legs")
    if int(realized["test_leg_count"].ge(5).sum()) != 93:
        raise AssertionError("Unexpected number of core lanes with at least five official test legs")
    return payloads, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write versioned outputs once; refuses any overwrite")
    mode.add_argument("--refresh-generated", action="store_true", help="refresh only outputs verified against this script's existing manifest")
    mode.add_argument("--check", action="store_true", help="recompute in memory and verify saved outputs and hashes")
    args = parser.parse_args()

    payloads, manifest = calculate()
    if args.write or args.refresh_generated:
        existing = [str(path.relative_to(ROOT)) for path in OUTPUTS.values() if path.exists()]
        if args.write and existing:
            raise FileExistsError(f"Refusing to overwrite existing outputs: {existing}")
        if args.refresh_generated:
            manifest_path = OUTPUTS["manifest"]
            if not manifest_path.is_file():
                raise FileNotFoundError("Cannot refresh without the existing generated manifest")
            old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for name, path in OUTPUTS.items():
                if name == "manifest":
                    continue
                old_record = old_manifest.get("outputs", {}).get(name, {})
                if not path.is_file() or sha256_file(path) != old_record.get("sha256"):
                    raise AssertionError(f"Refusing to refresh unrecognized or changed file: {path}")
        for path in OUTPUTS.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        for name, path in OUTPUTS.items():
            open_mode = "wb" if args.refresh_generated else "xb"
            with path.open(open_mode) as stream:
                stream.write(payloads[name])
        print("WROTE versioned outputs:")
        for name, path in OUTPUTS.items():
            print(f"{path.relative_to(ROOT)} sha256={sha256_file(path)}")
    else:
        if not OUTPUTS["manifest"].is_file():
            raise FileNotFoundError("Final remediation manifest is missing; run --write once")
        for name, path in OUTPUTS.items():
            if not path.is_file():
                raise FileNotFoundError(path)
            if path.read_bytes() != payloads[name]:
                raise AssertionError(f"Saved {name} differs from the in-memory reconstruction")
        print("PASS: in-memory reconstruction matches all saved versioned outputs byte-for-byte")
        for name, path in OUTPUTS.items():
            print(f"{path.relative_to(ROOT)} sha256={sha256_file(path)}")
    print(f"official_test_rows={manifest['model_vs_baseline']['official_test_legs']}")
    print(f"official_test_trips={manifest['model_vs_baseline']['official_test_trips']}")
    print(f"model_MAE={manifest['model_vs_baseline']['model']['mae']:.12f}")
    print(f"training_only_baseline_MAE={manifest['model_vs_baseline']['training_only_lane_history_baseline']['mae']:.12f}")
    print(f"model_RMSE={manifest['model_vs_baseline']['model']['rmse']:.12f}")
    print(f"training_only_baseline_RMSE={manifest['model_vs_baseline']['training_only_lane_history_baseline']['rmse']:.12f}")
    for row in manifest["interval_coverage"]:
        print(f"coverage_{row['level']}={row['covered_test_legs']}/{row['test_legs']} ({row['empirical_coverage']:.8%}); mean_width_ratio={row['mean_width_ratio']:.12f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
