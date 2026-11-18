"""
SupplyShield Data Loader Module
Cached loader functions with column and file validation.
All numbers come strictly from precomputed experiment and processed data files.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Any
import json
import time
import numpy as np
import networkx as nx
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
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
def load_risk_table_lane() -> pd.DataFrame:
    """
    Loads models/outputs/risk_table_lane.csv.
    Required columns: source_center, destination_center, mult_pred (or pred_multiplier).
    """
    root = get_repo_root()
    path = root / "models" / "outputs" / "risk_table_lane.csv"
    _validate_file_exists(path)
    df = pd.read_csv(path)
    _validate_columns(df, ["source_center", "destination_center"], "risk_table_lane.csv")
    if "pred_multiplier" not in df.columns:
        if "mult_pred" in df.columns:
            df["pred_multiplier"] = df["mult_pred"]
        else:
            df["pred_multiplier"] = 1.0
    return df


def solve_live_reroute(
    lane: Tuple[str, str],
    penalty: float = 96.0,
    risk_adjusted: bool = False,
) -> Dict[str, Any]:
    """
    Solves the multi-commodity flow LP (scipy.optimize.linprog method='highs')
    for the affected OD demand across the 100-hub network.
    """
    t0 = time.perf_counter()
    nodes_df = load_core_nodes()
    edges_df = load_core_edges()

    hub_names = dict(zip(nodes_df["hub"], nodes_df["name"]))

    risk_map: Dict[Tuple[str, str], float] = {}
    if risk_adjusted:
        try:
            risk_df = load_risk_table_lane()
            for _, r in risk_df.iterrows():
                mult = r.get("pred_multiplier", r.get("mult_pred", 1.0))
                risk_map[(str(r["source_center"]), str(r["destination_center"]))] = float(mult)
        except Exception:
            risk_map = {}

    nodes = list(nodes_df["hub"])
    nidx = {n: i for i, n in enumerate(nodes)}
    caps = {r["hub"]: float(r["capacity_est"]) for _, r in nodes_df.iterrows()}
    N = len(nodes)

    edges = []
    edge_costs = []
    edge_trips = []

    for _, r in edges_df.iterrows():
        u = str(r["source_center"]) if "source_center" in r and pd.notna(r["source_center"]) else str(r["source"])
        v = str(r["destination_center"]) if "destination_center" in r and pd.notna(r["destination_center"]) else str(r["destination"])
        if u in nidx and v in nidx:
            edges.append((u, v))
            time_hrs = float(r["median_actual_time"]) / 60.0 if "median_actual_time" in r else float(r.get("median_time", 60.0)) / 60.0
            if risk_adjusted:
                time_hrs *= risk_map.get((u, v), 1.0)
            edge_costs.append(time_hrs)
            edge_trips.append(float(r["trips"]))

    E = len(edges)
    eidx = {e: i for i, e in enumerate(edges)}
    closed_u, closed_v = lane

    if lane not in eidx:
        raise ValueError(f"Lane {lane} not found in active core network edges.")

    closed_idx = eidx[lane]
    q = edge_trips[closed_idx] / 14.0  # Daily demand (14-day training period)

    # Compute residual hub outgoing capacity from unaffected flows
    load = {n: 0.0 for n in nodes}
    for i, (u, v) in enumerate(edges):
        if (u, v) != lane:
            load[u] += edge_trips[i] / 14.0
    residual = {n: max(0.0, caps[n] - load[n]) for n in nodes}

    # LP formulation:
    nvar = E + 1
    src = np.array([nidx[u] for u, _ in edges])
    dst = np.array([nidx[v] for _, v in edges])

    rows = np.concatenate([src, dst, [nidx[closed_u], nidx[closed_v]]])
    cols = np.concatenate([np.arange(E), np.arange(E), [E, E]])
    vals = np.concatenate([np.ones(E), -np.ones(E), [1.0, -1.0]])
    A_eq = coo_matrix((vals, (rows, cols)), shape=(N, nvar)).tocsr()
    b_eq = np.zeros(N)
    b_eq[nidx[closed_u]] = q
    b_eq[nidx[closed_v]] = -q

    A_ub = coo_matrix((np.ones(E), (src, np.arange(E))), shape=(N, nvar)).tocsr()
    b_ub = np.array([residual[n] for n in nodes])

    bounds_hi = np.full(nvar, np.inf)
    bounds_hi[closed_idx] = 0.0  # Disrupted lane is closed
    bounds_hi[E] = q             # Cannot lose more than demanded
    bounds = np.column_stack([np.zeros(nvar), bounds_hi])

    cost_arr = np.array(edge_costs)
    obj = np.concatenate([cost_arr, [penalty]])

    res = linprog(obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    t1 = time.perf_counter()
    runtime_ms = (t1 - t0) * 1000.0

    if not res.success:
        raise RuntimeError(f"LP optimization failed: {res.message}")

    unmet = float(res.x[E])
    detour_cost = float(np.dot(cost_arr, res.x[:E]))
    total_reroute_cost = detour_cost + penalty * unmet
    do_nothing_cost = penalty * q
    cost_saved = do_nothing_cost - total_reroute_cost
    pct_saved = (cost_saved / do_nothing_cost * 100.0) if do_nothing_cost > 0 else 0.0

    detour_records = []
    for e in range(E):
        flow_val = float(res.x[e])
        if flow_val > 1e-5:
            u_e, v_e = edges[e]
            detour_records.append({
                "source": u_e,
                "source_name": hub_names.get(u_e, u_e),
                "destination": v_e,
                "destination_name": hub_names.get(v_e, v_e),
                "flow": flow_val,
                "unit_cost_hours": cost_arr[e],
                "flow_cost": flow_val * cost_arr[e],
            })

    detour_df = pd.DataFrame(detour_records)

    return {
        "runtime_ms": runtime_ms,
        "demand_legs": q,
        "unmet_legs": unmet,
        "detour_cost": detour_cost,
        "total_reroute_cost": total_reroute_cost,
        "do_nothing_cost": do_nothing_cost,
        "cost_saved": cost_saved,
        "pct_saved": pct_saved,
        "detour_df": detour_df,
        "multiplier_used": risk_map.get(lane, 1.0) if risk_adjusted else 1.0,
    }


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


@st.cache_data
def get_hub_coordinates() -> Tuple[Dict[str, Tuple[float, float]], Dict[str, bool]]:
    """
    Computes coordinates (lon, lat) for all 100 core hubs:
    - Uses real lat/lon where present (95 hubs).
    - For hubs without coordinates (5 hubs), uses a networkx spring layout with fixed seed (seed=42)
      anchored to the connected core network.
    Returns:
    - coords: Dict[hub, (lon, lat)]
    - is_approx: Dict[hub, bool] True if position was approximated via spring layout
    """
    nodes_df = load_core_nodes()
    edges_df = load_core_edges()

    G = nx.Graph()
    for _, r in nodes_df.iterrows():
        G.add_node(r["hub"])

    for _, r in edges_df.iterrows():
        u = r["source_center"] if "source_center" in r and pd.notna(r["source_center"]) else r["source"]
        v = r["destination_center"] if "destination_center" in r and pd.notna(r["destination_center"]) else r["destination"]
        G.add_edge(u, v)

    known_nodes = [r["hub"] for _, r in nodes_df.iterrows() if pd.notna(r["lat"]) and pd.notna(r["lon"])]
    lons = np.array([float(r["lon"]) for _, r in nodes_df.iterrows() if pd.notna(r["lat"]) and pd.notna(r["lon"])])
    lats = np.array([float(r["lat"]) for _, r in nodes_df.iterrows() if pd.notna(r["lat"]) and pd.notna(r["lon"])])

    min_lon, max_lon = float(lons.min()), float(lons.max())
    min_lat, max_lat = float(lats.min()), float(lats.max())

    # Normalize known coordinates to [-1, 1]
    norm_pos = {}
    for _, r in nodes_df.iterrows():
        if pd.notna(r["lat"]) and pd.notna(r["lon"]):
            x = 2 * (float(r["lon"]) - min_lon) / (max_lon - min_lon) - 1
            y = 2 * (float(r["lat"]) - min_lat) / (max_lat - min_lat) - 1
            norm_pos[r["hub"]] = np.array([x, y])

    # Initialize missing nodes near their network neighbors
    for m in G.nodes():
        if m not in norm_pos:
            nbrs = [norm_pos[nbr] for nbr in G.neighbors(m) if nbr in norm_pos]
            norm_pos[m] = np.mean(nbrs, axis=0) if nbrs else np.array([0.0, 0.0])

    # Run spring layout keeping known hubs fixed
    spring_norm = nx.spring_layout(G, pos=norm_pos, fixed=known_nodes, seed=42)

    coords: Dict[str, Tuple[float, float]] = {}
    is_approx: Dict[str, bool] = {}

    for _, r in nodes_df.iterrows():
        h = r["hub"]
        if pd.notna(r["lat"]) and pd.notna(r["lon"]):
            coords[h] = (float(r["lon"]), float(r["lat"]))
            is_approx[h] = False
        else:
            x, y = spring_norm[h]
            lon = min_lon + (x + 1) / 2 * (max_lon - min_lon)
            lat = min_lat + (y + 1) / 2 * (max_lat - min_lat)
            coords[h] = (float(lon), float(lat))
            is_approx[h] = True

    return coords, is_approx
