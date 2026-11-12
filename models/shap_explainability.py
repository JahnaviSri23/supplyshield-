"""Native XGBoost TreeSHAP analysis for the frozen SupplyShield model.

This module uses the saved B02 prediction API to build features and XGBoost's
``pred_contribs`` implementation to calculate attributions. It never loads a
target or actual outcome from the calibration/test prediction export.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

from models import prediction_api as api


ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS_PATH = ROOT / "data" / "processed" / "preds_cal_test_master_split_v1.csv"
SPLIT_PATH = ROOT / "data" / "processed" / "split_trip_ids.csv"
LEGS_PATH = ROOT / "data" / "processed" / "legs.csv"
DEFAULT_OUTPUT_DIR = ROOT / "experiments" / "day5" / "shap_native_v1"
ADDITIVITY_ATOL = 1e-6
EXPECTED_PREDICTION_ROWS = 4_394
EXPECTED_TEST_TRIPS = 2_424

INFERENCE_COLUMNS = (
    "trip_uuid",
    "source_center",
    "destination_center",
    "route_type",
    "od_start_time",
    "osrm_time_min",
    "osrm_distance_km",
    "lane_history_count",
    "base_pred",
    "pile",
)
SPLIT_COLUMNS = ("trip_uuid", "split")
TARGET_COLUMNS = frozenset(
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
        "predicted_residual",
    }
)
OUTPUT_FILENAMES = (
    "feature_importance.csv",
    "test_row_contributions.csv",
    "local_explanations.csv",
    "global_importance_bar.png",
    "test_beeswarm.png",
    "local_test_01.png",
    "local_test_02.png",
    "local_test_03.png",
    "run_manifest.json",
    "validation_report.md",
)


def load_test_population(
    predictions_path: str | Path = PREDICTIONS_PATH,
    split_path: str | Path = SPLIT_PATH,
) -> pd.DataFrame:
    """Load test requests with an inference-only column allowlist.

    ``split_trip_ids.csv`` is authoritative. The export's ``pile`` field is
    checked against it (with B02's ``cal`` alias normalized), then only test
    rows are returned. Target/outcome columns are not read from the export.
    """
    predictions = pd.read_csv(
        predictions_path,
        usecols=list(INFERENCE_COLUMNS),
        parse_dates=["od_start_time"],
    )
    split = pd.read_csv(split_path, usecols=list(SPLIT_COLUMNS))
    return select_test_population(predictions, split)


def select_test_population(
    predictions: pd.DataFrame,
    split: pd.DataFrame,
) -> pd.DataFrame:
    """Select authoritative test rows from already loaded inference fields."""
    missing_predictions = sorted(set(INFERENCE_COLUMNS) - set(predictions.columns))
    missing_split = sorted(set(SPLIT_COLUMNS) - set(split.columns))
    if missing_predictions or missing_split:
        raise ValueError(
            f"Missing prediction columns {missing_predictions} or split columns {missing_split}"
        )
    # Project the allowlist before joining or feature building. This makes
    # target fields in a caller-provided DataFrame unusable downstream.
    inference = predictions.loc[:, list(INFERENCE_COLUMNS)].copy()
    authoritative = split.loc[:, list(SPLIT_COLUMNS)].copy()
    if authoritative["trip_uuid"].isna().any() or authoritative["trip_uuid"].duplicated().any():
        raise ValueError("Authoritative split trip_uuid values must be present and unique")
    if not set(authoritative["split"].dropna().unique()).issubset(
        {"train", "calibration", "test"}
    ):
        raise ValueError("Authoritative split contains unsupported partition labels")
    joined = inference.merge(
        authoritative,
        on="trip_uuid",
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    if not joined["_merge"].eq("both").all():
        raise ValueError("Some prediction rows have no authoritative trip split")
    pile = joined["pile"].replace({"cal": "calibration"})
    if not pile.eq(joined["split"]).all():
        raise ValueError("Prediction export pile labels disagree with the master split")
    test = joined.loc[joined["split"].eq("test")].copy()
    if test.empty:
        raise ValueError("No held-out test rows were found")
    if test["trip_uuid"].nunique() != EXPECTED_TEST_TRIPS:
        raise ValueError(
            f"Expected {EXPECTED_TEST_TRIPS} held-out test trips; found "
            f"{test['trip_uuid'].nunique()}"
        )
    if len(test) != EXPECTED_PREDICTION_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_PREDICTION_ROWS} held-out test legs; found {len(test)}"
        )
    row_key = ["trip_uuid", "source_center", "destination_center", "od_start_time"]
    if test[row_key].isna().any().any() or test.duplicated(row_key).any():
        raise ValueError("Held-out test rows have missing or duplicated stable row keys")
    test = test.sort_values(row_key, kind="mergesort").reset_index(drop=True)
    test["explanation_id"] = [f"test_row_{i:05d}" for i in range(1, len(test) + 1)]
    test = test.rename(columns={"base_pred": "lane_base"})
    request_columns = ["explanation_id", *api.REQUIRED_INPUTS]
    requests = test.loc[:, request_columns].copy()
    requests.attrs["test_trip_count"] = int(test["trip_uuid"].nunique())
    leaked = sorted(set(requests.columns).intersection(TARGET_COLUMNS))
    if leaked:
        raise ValueError(f"Target/outcome fields entered the request: {leaked}")
    return requests


def verify_fit_history_precedes_test(
    legs_path: str | Path = LEGS_PATH,
    split_path: str | Path = SPLIT_PATH,
) -> dict[str, Any]:
    """Check B02's chronological fit-window end times against test departures.

    This reads trip/date metadata only. It does not read any target values or
    reconstruct lane features. B02 builds its lane history from the first 80%
    of master-train trips, so all fit outcomes must finish before test begins.
    """
    split = pd.read_csv(split_path, usecols=["trip_uuid", "split"])
    legs = pd.read_csv(
        legs_path,
        usecols=["trip_uuid", "trip_creation_time", "od_start_time", "od_end_time"],
        parse_dates=["trip_creation_time", "od_start_time", "od_end_time"],
    )
    train = legs.merge(
        split.loc[split["split"].eq("train"), ["trip_uuid"]],
        on="trip_uuid",
        how="inner",
        validate="many_to_one",
    )
    test = legs.loc[legs["trip_uuid"].isin(split.loc[split["split"].eq("test"), "trip_uuid"])]
    train_trip_dates = (
        train.groupby("trip_uuid")["trip_creation_time"].min().sort_values()
    )
    split_index = int(len(train_trip_dates) * 0.8)
    fit_trip_ids = train_trip_dates.index[:split_index]
    fit = train.loc[train["trip_uuid"].isin(fit_trip_ids)]
    fit_end = pd.to_datetime(fit["od_end_time"], errors="raise").max()
    test_start = pd.to_datetime(test["od_start_time"], errors="raise").min()
    if pd.isna(fit_end) or pd.isna(test_start) or fit_end > test_start:
        raise ValueError(
            "Fit-window outcomes do not all precede the earliest held-out test departure"
        )
    return {
        "fit_trip_count": int(len(fit_trip_ids)),
        "fit_leg_count": int(len(fit)),
        "fit_max_od_end_time": fit_end.isoformat(sep=" "),
        "test_min_od_start_time": test_start.isoformat(sep=" "),
        "fit_outcomes_after_first_test_departure": int(
            (pd.to_datetime(fit["od_end_time"]) > test_start).sum()
        ),
        "all_fit_outcomes_precede_all_test_departures": True,
        "targets_read": False,
    }


def build_test_features(requests: pd.DataFrame) -> pd.DataFrame:
    """Build model features only through the existing Prediction API."""
    forbidden = sorted(set(requests.columns).intersection(TARGET_COLUMNS))
    if forbidden:
        raise ValueError(f"Target/outcome fields cannot enter feature building: {forbidden}")
    feature_inputs = requests.loc[:, ["explanation_id", *api.REQUIRED_INPUTS]].copy()
    features = api.build_feature_matrix(feature_inputs)
    if tuple(features.columns) != api.FEATURE_COLUMNS:
        raise ValueError("Prediction API feature order differs from the frozen model schema")
    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("Feature matrix contains nonfinite values")
    return features


def load_model() -> xgb.Booster:
    """Load the frozen model through the Prediction API's metadata checks."""
    return api.load_model()


def calculate_native_contributions(
    features: pd.DataFrame,
    model: xgb.Booster | None = None,
    *,
    atol: float = ADDITIVITY_ATOL,
) -> tuple[np.ndarray, pd.DataFrame, np.ndarray, dict[str, Any]]:
    """Return best-iteration residual predictions, feature attributions, bias.

    B02's Prediction API uses the saved ``best_iteration``. Both prediction
    and native TreeSHAP therefore use that same iteration range; explaining
    all stored trees would not explain the API's deployed residual prediction.
    """
    if tuple(features.columns) != api.FEATURE_COLUMNS:
        raise ValueError("Feature matrix columns must match the saved model order")
    if features.empty or not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("Feature matrix must be nonempty and finite")
    active_model = model if model is not None else load_model()
    if tuple(active_model.feature_names or ()) != api.FEATURE_COLUMNS:
        raise ValueError("Booster feature names/order do not match the Prediction API")
    if tuple(active_model.feature_types or ()) != api.FEATURE_TYPES:
        raise ValueError("Booster feature types do not match the Prediction API")
    dmatrix = xgb.DMatrix(
        features,
        feature_names=list(api.FEATURE_COLUMNS),
        feature_types=list(api.FEATURE_TYPES),
    )
    best_iteration = active_model.attributes().get("best_iteration")
    iteration_range = (
        (0, int(best_iteration) + 1) if best_iteration is not None else (0, 0)
    )
    raw_residual = np.asarray(
        active_model.predict(dmatrix, iteration_range=iteration_range), dtype=float
    ).reshape(-1)
    native = np.asarray(
        active_model.predict(
            dmatrix,
            pred_contribs=True,
            iteration_range=iteration_range,
        ),
        dtype=float,
    )
    if native.shape != (len(features), len(api.FEATURE_COLUMNS) + 1):
        raise ValueError(f"Unexpected native TreeSHAP shape: {native.shape}")
    if len(raw_residual) != len(features) or not np.isfinite(raw_residual).all():
        raise ValueError("Booster returned invalid raw residual predictions")
    if not np.isfinite(native).all():
        raise ValueError("Native TreeSHAP returned nonfinite values")
    feature_values = native[:, :-1]
    bias_values = native[:, -1]
    contribution_sum = feature_values.sum(axis=1) + bias_values
    additivity_error = np.abs(contribution_sum - raw_residual)
    if not np.allclose(contribution_sum, raw_residual, rtol=0.0, atol=atol):
        raise ValueError(
            f"Native TreeSHAP additivity failed: max error {float(additivity_error.max())} "
            f"> tolerance {atol}"
        )
    contribution_frame = pd.DataFrame(feature_values, columns=list(api.FEATURE_COLUMNS))
    metadata = {
        "contribution_shape": [int(x) for x in native.shape],
        "feature_names": list(api.FEATURE_COLUMNS),
        "bias_column_index": len(api.FEATURE_COLUMNS),
        "best_iteration": int(best_iteration) if best_iteration is not None else None,
        "booster_round_count": int(active_model.num_boosted_rounds()),
        "iteration_range": list(iteration_range),
        "additivity_atol": float(atol),
        "additivity_rtol": 0.0,
        "max_abs_additivity_error": float(additivity_error.max()),
        "all_contributions_finite": bool(np.isfinite(native).all()),
    }
    return raw_residual, contribution_frame, bias_values, metadata


def global_importance(contributions: pd.DataFrame) -> pd.DataFrame:
    """Rank features by mean absolute contribution; keep bias excluded."""
    if tuple(contributions.columns) != api.FEATURE_COLUMNS:
        raise ValueError("Contribution columns must match the exact ten-feature order")
    if contributions.empty or not np.isfinite(contributions.to_numpy(dtype=float)).all():
        raise ValueError("Feature contributions must be nonempty and finite")
    rows = []
    for position, feature in enumerate(api.FEATURE_COLUMNS):
        values = contributions[feature].to_numpy(dtype=float)
        rows.append(
            {
                "feature": feature,
                "mean_abs_shap": float(np.mean(np.abs(values))),
                "mean_signed_shap": float(np.mean(values)),
                "std_shap": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "median_abs_shap": float(np.median(np.abs(values))),
                "_feature_order": position,
            }
        )
    result = pd.DataFrame(rows).sort_values(
        ["mean_abs_shap", "_feature_order"],
        ascending=[False, True],
        kind="mergesort",
    )
    result.insert(0, "rank", np.arange(1, len(result) + 1))
    return result.drop(columns="_feature_order").reset_index(drop=True)


def select_local_examples(
    explanation_ids: pd.Series,
    predictions: np.ndarray,
) -> pd.DataFrame:
    """Choose deterministic held-out rows nearest the 10th/50th/90th percentiles."""
    values = np.asarray(predictions, dtype=float).reshape(-1)
    ids = explanation_ids.astype(str).reset_index(drop=True)
    if len(ids) != len(values) or len(values) < 3 or not np.isfinite(values).all():
        raise ValueError("Local example selection requires at least three finite predictions")
    targets = np.quantile(values, [0.1, 0.5, 0.9])
    selected: list[int] = []
    selected_values: set[float] = set()
    result = []
    for label, target in zip(("p10", "p50", "p90"), targets):
        order = np.argsort(np.abs(values - target), kind="stable")
        candidate = next(
            (
                int(index)
                for index in order
                if int(index) not in selected and float(values[index]) not in selected_values
            ),
            None,
        )
        if candidate is None:
            candidate = next((int(i) for i in order if int(i) not in selected), None)
        if candidate is None:
            raise ValueError("Could not select three distinct local rows")
        selected.append(candidate)
        selected_values.add(float(values[candidate]))
        result.append(
            {
                "quantile_target": label,
                "explanation_id": ids.iloc[candidate],
                "row_index": candidate,
                "predicted_residual": float(values[candidate]),
            }
        )
    return pd.DataFrame(result)


def make_shap_explanation(
    features: pd.DataFrame,
    contributions: pd.DataFrame,
    bias: np.ndarray,
) -> Any:
    """Wrap native values in SHAP's presentation object without recalculation."""
    import shap

    return shap.Explanation(
        values=contributions.to_numpy(dtype=float),
        base_values=np.asarray(bias, dtype=float),
        data=features.to_numpy(dtype=float),
        feature_names=list(api.FEATURE_COLUMNS),
    )


def render_global_bar(importance: pd.DataFrame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ordered = importance.sort_values("mean_abs_shap", ascending=True, kind="mergesort")
    fig, ax = plt.subplots(figsize=(10, 6.5), constrained_layout=True)
    ax.barh(ordered["feature"], ordered["mean_abs_shap"], color="#31688e")
    ax.set_xlabel("Mean absolute native TreeSHAP contribution (residual-ratio units)")
    ax.set_ylabel("Model feature")
    ax.set_title("Global feature attribution on held-out test legs")
    ax.grid(axis="x", alpha=0.2)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _render_matplotlib_beeswarm(
    contributions: pd.DataFrame,
    features: pd.DataFrame,
    path: Path,
    importance: pd.DataFrame,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    names = importance["feature"].tolist()
    fig, ax = plt.subplots(figsize=(11, 7), constrained_layout=True)
    jitter_rng = np.random.default_rng(17)
    for y, name in enumerate(names):
        vals = contributions[name].to_numpy(dtype=float)
        feature_vals = features[name].to_numpy(dtype=float)
        ranks = pd.Series(feature_vals).rank(method="average", pct=True).to_numpy()
        jitter = jitter_rng.uniform(-0.28, 0.28, size=len(vals))
        ax.scatter(vals, y + jitter, c=ranks, cmap="coolwarm", vmin=0.0, vmax=1.0,
                   s=9, alpha=0.55, linewidths=0)
    ax.axvline(0.0, color="black", linewidth=0.8, alpha=0.6)
    ax.set_yticks(np.arange(len(names)), labels=names)
    ax.set_xlabel("Native TreeSHAP contribution to predicted residual (ratio units)")
    ax.set_ylabel("Model feature (ranked by mean absolute contribution)")
    ax.set_title("Native TreeSHAP contribution distribution on held-out test legs")
    sm = ScalarMappable(norm=Normalize(0.0, 1.0), cmap="coolwarm")
    sm.set_array([])
    colorbar = fig.colorbar(sm, ax=ax)
    colorbar.set_label("Feature value percentile within feature")
    ax.grid(axis="x", alpha=0.2)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def render_beeswarm(
    features: pd.DataFrame,
    contributions: pd.DataFrame,
    bias: np.ndarray,
    path: Path,
    importance: pd.DataFrame,
) -> dict[str, str]:
    """Try SHAP's beeswarm on native values; safely fall back to Matplotlib."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        import shap

        explanation = make_shap_explanation(features, contributions, bias)
        shap.plots.beeswarm(explanation, max_display=len(api.FEATURE_COLUMNS), show=False)
        fig = plt.gcf()
        ax = fig.axes[0]
        ax.set_xlabel("Native TreeSHAP contribution to predicted residual (ratio units)")
        ax.set_ylabel("Model feature")
        ax.set_title("Native TreeSHAP contributions on held-out test legs")
        fig.savefig(path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return {"method": "shap.plots.beeswarm", "fallback_reason": ""}
    except Exception as exc:  # plotting compatibility only; attribution is already complete
        plt.close("all")
        _render_matplotlib_beeswarm(contributions, features, path, importance)
        return {
            "method": "matplotlib_fallback",
            "fallback_reason": f"{type(exc).__name__}: {exc}",
        }


def render_local_plot(
    feature_values: pd.Series,
    contributions: pd.Series,
    bias: float,
    prediction: float,
    explanation_id: str,
    quantile_target: str,
    path: Path,
) -> None:
    """Render a local additive waterfall with bias and residual prediction."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = np.argsort(np.abs(contributions.to_numpy(dtype=float)), kind="stable")
    names = [api.FEATURE_COLUMNS[i] for i in order]
    labels = [f"{name} = {float(feature_values[name]):.4g}" for name in names]
    deltas = contributions.loc[names].to_numpy(dtype=float)
    starts: list[float] = []
    current = float(bias)
    for delta in deltas:
        starts.append(current)
        current += float(delta)
    reconstructed = current
    if not np.isclose(reconstructed, prediction, rtol=0.0, atol=ADDITIVITY_ATOL):
        raise ValueError(f"Local row {explanation_id} failed residual reconstruction")

    fig, ax = plt.subplots(figsize=(11, 7), constrained_layout=True)
    y_positions = np.arange(len(labels))
    colors = ["#c44e52" if value >= 0 else "#4c72b0" for value in deltas]
    ax.barh(y_positions, deltas, left=starts, color=colors, alpha=0.85)
    ax.set_yticks(y_positions, labels=labels)
    ax.axvline(float(bias), color="#555555", linestyle="--", linewidth=1.0,
               label=f"Bias contribution = {bias:.5f}")
    ax.axvline(float(prediction), color="#111111", linestyle="-", linewidth=1.2,
               label=f"Predicted residual = {prediction:.5f}")
    ax.set_xlabel("Cumulative residual prediction (ratio units)")
    ax.set_ylabel("Feature value and contribution")
    ax.set_title(f"Local residual explanation: {explanation_id} ({quantile_target})")
    ax.text(
        0.01, 0.01,
        f"bias + feature contributions = {reconstructed:.6f}; "
        f"prediction = {prediction:.6f}",
        transform=ax.transAxes, fontsize=9, va="bottom",
    )
    ax.legend(loc="best", fontsize=8)
    ax.grid(axis="x", alpha=0.2)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _assert_output_paths_available(output: Path) -> None:
    """Reject an existing run directory or any pre-existing named output."""
    if output.exists():
        raise FileExistsError(f"Output destination already exists; choose a new version: {output}")
    for name in OUTPUT_FILENAMES:
        if (output / name).exists():
            raise FileExistsError(f"Output file already exists: {output / name}")


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, default=str)
        stream.write("\n")


def _write_text_new(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def run_analysis(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Run the full test-population analysis and write only to a new directory."""
    # Check all destinations before creating the first output.
    output = Path(output_dir).expanduser().resolve()
    experiments = (ROOT / "experiments").resolve()
    try:
        output.relative_to(experiments)
    except ValueError as exc:
        raise ValueError("Outputs must be placed under the repository experiments/ directory") from exc
    _assert_output_paths_available(output)

    requests = load_test_population()
    temporal_check = verify_fit_history_precedes_test()
    features = build_test_features(requests)
    model = load_model()
    residuals, contributions, bias, validation = calculate_native_contributions(features, model)
    importance = global_importance(contributions)
    local = select_local_examples(requests["explanation_id"], residuals)
    row_sums = contributions.sum(axis=1).to_numpy() + bias
    row_errors = np.abs(row_sums - residuals)
    contribution_export = contributions.add_prefix("shap__").copy()
    contribution_export.insert(0, "explanation_id", requests["explanation_id"].to_numpy())
    contribution_export["bias_contribution"] = bias
    contribution_export["predicted_residual"] = residuals
    contribution_export["contribution_sum"] = row_sums
    contribution_export["absolute_additivity_error"] = row_errors

    local_records: list[dict[str, Any]] = []
    for example in local.itertuples(index=False):
        idx = int(example.row_index)
        record: dict[str, Any] = {
            "quantile_target": example.quantile_target,
            "explanation_id": example.explanation_id,
            "predicted_residual": float(residuals[idx]),
            "bias_contribution": float(bias[idx]),
            "reconstructed_residual": float(row_sums[idx]),
            "absolute_additivity_error": float(row_errors[idx]),
        }
        for name in api.FEATURE_COLUMNS:
            record[f"value__{name}"] = float(features.iloc[idx][name])
            record[f"contribution__{name}"] = float(contributions.iloc[idx][name])
        local_records.append(record)
    local_export = pd.DataFrame.from_records(local_records)

    output.mkdir(parents=True, exist_ok=False)
    # Check every individual destination immediately before writing it.
    for name in OUTPUT_FILENAMES:
        if (output / name).exists():
            raise FileExistsError(f"Refusing to overwrite output: {output / name}")
    importance.to_csv(output / "feature_importance.csv", index=False, mode="x")
    contribution_export.to_csv(output / "test_row_contributions.csv", index=False, mode="x")
    local_export.to_csv(output / "local_explanations.csv", index=False, mode="x")
    render_global_bar(importance, output / "global_importance_bar.png")
    beeswarm_info = render_beeswarm(
        features, contributions, bias, output / "test_beeswarm.png", importance
    )
    for plot_number, example in enumerate(local.itertuples(index=False), start=1):
        idx = int(example.row_index)
        render_local_plot(
            features.iloc[idx],
            contributions.iloc[idx],
            float(bias[idx]),
            float(residuals[idx]),
            str(example.explanation_id),
            str(example.quantile_target),
            output / f"local_test_{plot_number:02d}.png",
        )

    manifest: dict[str, Any] = {
        "analysis": "native_xgboost_treeshap_residual_explainability",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "prediction_population": "all eligible master-split held-out test legs",
        "row_count": int(len(features)),
        "test_trip_count": int(requests.attrs["test_trip_count"]),
        "sampling": {"used": False, "method": "all eligible test rows"},
        "master_split_path": SPLIT_PATH.relative_to(ROOT).as_posix(),
        "prediction_input_path": PREDICTIONS_PATH.relative_to(ROOT).as_posix(),
        "prediction_input_columns_read": list(INFERENCE_COLUMNS),
        "target_columns_read_from_prediction_input": [],
        "fit_window_temporal_check": temporal_check,
        "model_path": api.MODEL_PATH.relative_to(ROOT).as_posix(),
        "model_sha256": _sha256(api.MODEL_PATH),
        "prediction_export_sha256": _sha256(PREDICTIONS_PATH),
        "master_split_sha256": _sha256(SPLIT_PATH),
        "feature_names": list(api.FEATURE_COLUMNS),
        "feature_types": list(api.FEATURE_TYPES),
        "explanation_target": "best-iteration XGBoost residual prediction only",
        "base_prediction_note": "lane_base is added outside the residual model and is not explained",
        "xgboost_version": xgb.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "shap_version": _package_version("shap"),
        "best_iteration": validation["best_iteration"],
        "booster_round_count": validation["booster_round_count"],
        "iteration_range": validation["iteration_range"],
        "contribution_shape": validation["contribution_shape"],
        "bias_is_separate": True,
        "all_contributions_finite": validation["all_contributions_finite"],
        "additivity_atol": validation["additivity_atol"],
        "additivity_rtol": validation["additivity_rtol"],
        "max_abs_additivity_error": validation["max_abs_additivity_error"],
        "beeswarm": beeswarm_info,
        "local_example_selection": local.drop(columns="row_index").to_dict(orient="records"),
        "global_top_features": importance.head(3)["feature"].tolist(),
        "output_files": list(OUTPUT_FILENAMES),
    }
    _write_json_new(output / "run_manifest.json", manifest)
    report = _validation_report(manifest, importance, output)
    _write_text_new(output / "validation_report.md", report)
    return manifest


def _package_version(name: str) -> str:
    from importlib.metadata import version

    return version(name)


def _validation_report(
    manifest: dict[str, Any],
    importance: pd.DataFrame,
    output: Path,
) -> str:
    temporal = manifest["fit_window_temporal_check"]
    top = importance.head(10)
    rows = [
        "# Native TreeSHAP validation report",
        "",
        "## Population and safeguards",
        "",
        f"- Held-out test legs explained: {manifest['row_count']:,}.",
        f"- Held-out test trips: {manifest['test_trip_count']:,}.",
        "- Population: all eligible test rows; no sampling.",
        f"- Authoritative split: `{manifest['master_split_path']}`.",
        f"- Inference export read with allowlisted columns: `{manifest['prediction_input_path']}`.",
        "- Target/outcome columns read from the prediction export: none.",
        f"- B02 chronological fit window: {temporal['fit_trip_count']:,} trips / "
        f"{temporal['fit_leg_count']:,} legs; latest fit outcome ends "
        f"{temporal['fit_max_od_end_time']}; earliest test departure "
        f"{temporal['test_min_od_start_time']}; fit outcomes after that departure: "
        f"{temporal['fit_outcomes_after_first_test_departure']:,}.",
        "- The fit-window temporal check reads date metadata only; it reads no target values.",
        "",
        "## Attribution validation",
        "",
        f"- Model: `{manifest['model_path']}` (SHA-256 `{manifest['model_sha256']}`).",
        f"- XGBoost / NumPy / pandas / SHAP: {manifest['xgboost_version']} / "
        f"{manifest['numpy_version']} / {manifest['pandas_version']} / {manifest['shap_version']}.",
        f"- Features: {len(manifest['feature_names'])}; contribution matrix: "
        f"`{tuple(manifest['contribution_shape'])}` (10 features + bias).",
        f"- Best iteration: {manifest['best_iteration']} of "
        f"{manifest['booster_round_count']} stored rounds; iteration range "
        f"`{manifest['iteration_range']}` matches the existing Prediction API.",
        f"- All contributions finite: {manifest['all_contributions_finite']}.",
        f"- Maximum absolute additivity error: {manifest['max_abs_additivity_error']:.12g}; "
        f"tolerance: absolute {manifest['additivity_atol']}, relative {manifest['additivity_rtol']}.",
        "- Contributions explain the residual prediction. The supplied `lane_base` is "
        "added outside the model and is not explained.",
        "",
        "## Global ranking",
        "",
        "Mean absolute attribution summarizes contribution magnitude, not causal importance.",
        "",
        "| Rank | Feature | Mean absolute | Mean signed | Std. dev. | Median absolute |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in top.itertuples(index=False):
        rows.append(
            f"| {item.rank} | `{item.feature}` | {item.mean_abs_shap:.8g} | "
            f"{item.mean_signed_shap:.8g} | {item.std_shap:.8g} | {item.median_abs_shap:.8g} |"
        )
    rows.extend(
        [
            "",
            "## Plots and local examples",
            "",
            f"- Beeswarm plotting method: `{manifest['beeswarm']['method']}`.",
            f"- Local rows were selected deterministically nearest the p10/p50/p90 "
            f"predicted-residual quantiles: {', '.join(x['explanation_id'] for x in manifest['local_example_selection'])}.",
            "- Local plots show the bias separately and stack the ten feature contributions; "
            "each sum was checked against the raw residual prediction.",
            "- Feature attributions describe model behavior; they do not establish causation "
            "or explain the complete final `pred_ratio`.",
            "",
            f"Outputs: `{output.relative_to(ROOT).as_posix()}/`.",
            "",
        ]
    )
    if manifest["beeswarm"]["fallback_reason"]:
        rows.extend(
            [
                "Beeswarm fallback reason: `" + manifest["beeswarm"]["fallback_reason"] + "`.",
                "",
            ]
        )
    return "\n".join(rows)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="new, non-existing versioned directory under experiments/",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manifest = run_analysis(args.output_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
