"""
SupplyShield Data Loader Module
Cached loader functions with column and file validation.
All numbers come strictly from precomputed experiment and processed data files.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any
import json
import pandas as pd
import streamlit as st

BANNER_TEXT = (
    "Real network and transit times (Delhivery, 3 weeks, 2018). "
    "Closures are simulated. Capacity = 95th percentile of outgoing legs per day. "
    "Results apply only to the 100-hub core."
)


def get_repo_root() -> Path:
    """
    Finds repo root whether running from repo root or inside app/ directory.
    """
    cwd = Path.cwd().resolve()
    if (cwd / "experiments").is_dir() and (cwd / "data").is_dir():
        return cwd
    app_dir = Path(__file__).resolve().parent
    if (app_dir.parent / "experiments").is_dir() and (app_dir.parent / "data").is_dir():
        return app_dir.parent
    return cwd


def render_banner() -> None:
    """Renders the required project banner at the top of a page."""
    st.info(f"ℹ️ **{BANNER_TEXT}**")


def _validate_file_exists(file_path: Path) -> None:
    if not file_path.is_file():
        err_msg = f"Data file not found: {file_path}. Please check repository structure."
        st.error(err_msg)
        raise FileNotFoundError(err_msg)


def _validate_columns(df: pd.DataFrame, required_cols: List[str], file_name: str) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        err_msg = f"Data validation error in {file_name}: Missing expected columns: {missing}"
        st.error(err_msg)
        raise ValueError(err_msg)


@st.cache_data
def load_core_nodes() -> pd.DataFrame:
    """
    Loads data/processed/core_nodes.csv.
    Required columns: hub, name, state, lat, lon, capacity_est
    """
    root = get_repo_root()
    path = root / "data" / "processed" / "core_nodes.csv"
    _validate_file_exists(path)
    df = pd.read_csv(path)
    required_cols = ["hub", "name", "state", "lat", "lon", "capacity_est"]
    _validate_columns(df, required_cols, "core_nodes.csv")
    return df


@st.cache_data
def load_core_edges() -> pd.DataFrame:
    """
    Loads data/processed/core_edges.csv.
    Required columns: source_center, destination_center, leg_count, trip_count
    """
    root = get_repo_root()
    path = root / "data" / "processed" / "core_edges.csv"
    _validate_file_exists(path)
    df = pd.read_csv(path)
    required_cols = ["source_center", "destination_center", "leg_count", "trip_count"]
    _validate_columns(df, required_cols, "core_edges.csv")
    return df


@st.cache_data
def load_multiflow_closures() -> pd.DataFrame:
    """
    Loads experiments/c_multiflow_closures.csv.
    Required columns: lane, closed_lane_legs_per_day, plan, total_cost, extra_cost, extra_vs_best_normal, unmet, lp_seconds
    """
    root = get_repo_root()
    path = root / "experiments" / "c_multiflow_closures.csv"
    _validate_file_exists(path)
    df = pd.read_csv(path)
    required_cols = [
        "lane",
        "closed_lane_legs_per_day",
        "plan",
        "total_cost",
        "extra_cost",
        "extra_vs_best_normal",
        "unmet",
        "lp_seconds",
    ]
    _validate_columns(df, required_cols, "c_multiflow_closures.csv")
    return df


@st.cache_data
def load_real_lane_closures() -> pd.DataFrame:
    """
    Loads experiments/c_real_lane_closures.csv.
    Required columns: lane, daily_legs, normal_cost, plan, shipping, unmet, total_cost, seconds
    """
    root = get_repo_root()
    path = root / "experiments" / "c_real_lane_closures.csv"
    _validate_file_exists(path)
    df = pd.read_csv(path)
    required_cols = [
        "lane",
        "daily_legs",
        "normal_cost",
        "plan",
        "shipping",
        "unmet",
        "total_cost",
        "seconds",
    ]
    _validate_columns(df, required_cols, "c_real_lane_closures.csv")
    return df


@st.cache_data
def load_multiflow_plans() -> List[Dict[str, Any]]:
    """
    Loads experiments/c_multiflow_plans.json.
    Validates structure: list of dicts with id, closed_lanes, penalty, demand, plans, expected
    """
    root = get_repo_root()
    path = root / "experiments" / "c_multiflow_plans.json"
    _validate_file_exists(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        err_msg = "experiments/c_multiflow_plans.json must be a non-empty list of scenario dicts."
        st.error(err_msg)
        raise ValueError(err_msg)

    required_keys = ["id", "closed_lanes", "penalty", "demand", "plans", "expected"]
    for idx, item in enumerate(data):
        missing = [k for k in required_keys if k not in item]
        if missing:
            err_msg = f"Scenario {idx} in c_multiflow_plans.json missing keys: {missing}"
            st.error(err_msg)
            raise ValueError(err_msg)

    return data


@st.cache_data
def load_uncertainty_summary() -> pd.DataFrame:
    """
    Loads experiments/c_uncertainty_summary.csv.
    Required columns: plan, eval_mean, eval_cvar, eval_worst, unmet, plan_change_vs_det,
                      realized_primary, realized_sens_pred, realized_sens_5legs
    """
    root = get_repo_root()
    path = root / "experiments" / "c_uncertainty_summary.csv"
    _validate_file_exists(path)
    df = pd.read_csv(path)
    required_cols = [
        "plan",
        "eval_mean",
        "eval_cvar",
        "eval_worst",
        "unmet",
        "plan_change_vs_det",
        "realized_primary",
        "realized_sens_pred",
        "realized_sens_5legs",
    ]
    _validate_columns(df, required_cols, "c_uncertainty_summary.csv")
    return df


@st.cache_data
def load_uncertainty_intervals() -> pd.DataFrame:
    """
    Loads experiments/c_uncertainty_intervals.csv.
    Required columns: population, interval, lanes, test_legs, coverage_of_realized,
                      mean_width, share_of_samples_inside
    """
    root = get_repo_root()
    path = root / "experiments" / "c_uncertainty_intervals.csv"
    _validate_file_exists(path)
    df = pd.read_csv(path)
    required_cols = [
        "population",
        "interval",
        "lanes",
        "test_legs",
        "coverage_of_realized",
        "mean_width",
        "share_of_samples_inside",
    ]
    _validate_columns(df, required_cols, "c_uncertainty_intervals.csv")
    return df


@st.cache_data
def load_uncertainty_results() -> pd.DataFrame:
    """
    Loads experiments/c_uncertainty_results.csv.
    Required columns: closure, lane, seed, plan, eval_mean, eval_cvar, eval_worst, unmet,
                      plan_change_vs_det, imputed_lanes_used, realized_primary,
                      realized_sens_pred, realized_sens_5legs
    """
    root = get_repo_root()
    path = root / "experiments" / "c_uncertainty_results.csv"
    _validate_file_exists(path)
    df = pd.read_csv(path)
    required_cols = [
        "closure",
        "lane",
        "seed",
        "plan",
        "eval_mean",
        "eval_cvar",
        "eval_worst",
        "unmet",
        "plan_change_vs_det",
        "imputed_lanes_used",
        "realized_primary",
        "realized_sens_pred",
        "realized_sens_5legs",
    ]
    _validate_columns(df, required_cols, "c_uncertainty_results.csv")
    return df


@st.cache_data
def get_overview_metrics() -> Tuple[int, int, int]:
    """
    Returns 3 metric cards computed from the data:
    1. Number of hubs
    2. Number of lanes
    3. Number of closures tested
    """
    nodes_df = load_core_nodes()
    edges_df = load_core_edges()
    closures_df = load_multiflow_closures()

    num_hubs = len(nodes_df["hub"].unique())
    num_lanes = len(edges_df)
    num_closures = len(closures_df["lane"].unique())

    return num_hubs, num_lanes, num_closures


@st.cache_data
def get_overview_summary_table() -> pd.DataFrame:
    """
    Clean summary table of average total_cost, extra_vs_best_normal, and unmet per plan
    from experiments/c_multiflow_closures.csv.
    """
    df = load_multiflow_closures()
    agg = (
        df.groupby("plan")[["total_cost", "extra_vs_best_normal", "unmet", "lp_seconds"]]
        .mean()
        .reset_index()
    )
    # Maintain consistent plan ordering
    plan_order = ["do nothing", "greedy", "preserve (affected flows only)", "LP (all flows)"]
    agg["order"] = agg["plan"].apply(lambda p: plan_order.index(p) if p in plan_order else 99)
    agg = agg.sort_values("order").drop(columns=["order"]).reset_index(drop=True)
    return agg

