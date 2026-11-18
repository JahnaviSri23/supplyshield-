"""Person B orchestration for a privacy-conscious, live SupplyShield demo.

This module adapts existing prediction, conformal, uncertainty, optimizer, and
simulator contracts. It writes no files and returns aggregate-only results.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any, Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_COLUMNS = (
    "source_center",
    "destination_center",
    "route_type",
    "od_start_time",
    "osrm_time_min",
    "osrm_distance_km",
)
RISK_COLUMNS = (
    "source_center",
    "destination_center",
    "lane_base",
    "n_train_legs",
    "mult_pred",
    "mult_lo90",
    "mult_hi90",
)
STAGE_NAMES = (
    "Input validation",
    "Data and model preparation",
    "Live prediction",
    "Conformal uncertainty",
    "Risk and CVaR",
    "Disruption simulation",
    "Recovery optimization",
    "Post-recovery evaluation",
    "Explainability",
)
ID_PATTERN = re.compile(r"IND[0-9A-Z]{6,}|[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}")
Z90 = 1.6448536269514722
ALPHA = 0.8
PLAN_SCENARIOS = 200
EVALUATION_SCENARIOS = 1000


@dataclass(frozen=True)
class _Catalog:
    samples: pd.DataFrame
    closures: tuple[tuple[str, str], ...]
    risk: pd.DataFrame


def redact_sensitive_text(value: Any) -> str:
    """Redact common route/trip identifier patterns from user-facing errors."""
    return ID_PATTERN.sub("[identifier withheld]", str(value))


def _load_catalog(root: Path) -> _Catalog:
    processed = root / "data" / "processed"
    edge_path = processed / "core_edges.csv"
    later_path = processed / "core_later_legs.csv"
    risk_path = root / "models" / "outputs" / "risk_table_lane.csv"
    required = (edge_path, later_path, risk_path)
    missing = [path.relative_to(root).as_posix() for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing demo inputs: {', '.join(missing)}")

    edges = pd.read_csv(edge_path, usecols=["source", "destination"])
    if edges.duplicated(["source", "destination"]).any():
        raise ValueError("Core network contains duplicate directed edges")
    closures = tuple(
        sorted(
            (str(row.source), str(row.destination))
            for row in edges.itertuples(index=False)
        )
    )
    edge_set = set(closures)

    risk = pd.read_csv(risk_path, usecols=list(RISK_COLUMNS))
    if risk.duplicated(["source_center", "destination_center"]).any():
        raise ValueError("Tracked risk reference contains duplicate directed edges")
    risk_keys = set(
        map(tuple, risk[["source_center", "destination_center"]].astype(str).to_numpy())
    )
    if risk_keys != edge_set:
        raise ValueError("Tracked risk reference does not exactly cover the core network")
    risk_numeric = risk[list(RISK_COLUMNS[2:])].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(risk_numeric.to_numpy(dtype=float)).all():
        raise ValueError("Tracked risk reference has non-finite required values")
    if (risk_numeric[["lane_base", "mult_pred", "mult_lo90", "mult_hi90"]] <= 0).any().any():
        raise ValueError("Tracked risk reference must contain positive ratios/multipliers")
    if not (
        risk_numeric["mult_lo90"].le(risk_numeric["mult_pred"])
        & risk_numeric["mult_pred"].le(risk_numeric["mult_hi90"])
    ).all():
        raise ValueError("Tracked risk reference has invalid 90% multiplier bounds")

    # Only model-request columns are read. Outcome, trip, and customer-like
    # fields from the held-out later-period source are excluded at I/O time.
    samples = pd.read_csv(later_path, usecols=list(SAMPLE_COLUMNS))
    samples = samples.dropna(subset=list(SAMPLE_COLUMNS)).copy()
    samples = samples[samples["route_type"].isin({"FTL", "Carting"})]
    samples["source_center"] = samples["source_center"].astype(str)
    samples["destination_center"] = samples["destination_center"].astype(str)
    samples = samples[
        [tuple(pair) in edge_set for pair in samples[["source_center", "destination_center"]].to_numpy()]
    ]
    samples = samples.sort_values(
        ["source_center", "destination_center", "od_start_time"], kind="mergesort"
    ).merge(
        risk,
        on=["source_center", "destination_center"],
        how="inner",
        validate="many_to_one",
    )
    samples["lane_history_count"] = samples["n_train_legs"]
    from models.prediction_api import validate_prediction_rows

    prediction_columns = (
        "source_center",
        "destination_center",
        "route_type",
        "od_start_time",
        "osrm_time_min",
        "osrm_distance_km",
        "lane_base",
        "lane_history_count",
    )
    try:
        validate_prediction_rows(samples[list(prediction_columns)])
    except (TypeError, ValueError):
        # Exclude only rows that fail the model's own request contract. This
        # fallback is row-wise so one bad record cannot hide valid choices.
        eligible = []
        for index, row in samples.iterrows():
            try:
                validate_prediction_rows(pd.DataFrame([row[list(prediction_columns)].to_dict()]))
            except (TypeError, ValueError):
                continue
            eligible.append(index)
        samples = samples.loc[eligible].copy()
    samples = samples.reset_index(drop=True)
    if samples.empty:
        raise ValueError("No valid later-period model feature samples match the core network")
    return _Catalog(samples=samples, closures=closures, risk=risk)


def get_demo_catalog_summary(root: str | Path = ROOT) -> dict[str, int]:
    """Return counts only; never expose the underlying route/sample identifiers."""
    catalog = _load_catalog(Path(root).resolve())
    return {"sample_count": len(catalog.samples), "closure_count": len(catalog.closures)}


def _validate_scenario(scenario: dict[str, Any], catalog: _Catalog) -> dict[str, Any]:
    if not isinstance(scenario, dict):
        raise TypeError("Scenario must be a mapping")
    sample_index = scenario.get("sample_index")
    closure_index = scenario.get("closure_index")
    if isinstance(sample_index, bool) or not isinstance(sample_index, int):
        raise ValueError("sample_index must be an integer choice")
    if not 0 <= sample_index < len(catalog.samples):
        raise ValueError("sample_index is outside the available feature samples")
    if isinstance(closure_index, bool) or not isinstance(closure_index, int):
        raise ValueError("closure_index must be an integer choice")
    if not 0 <= closure_index < len(catalog.closures):
        raise ValueError("closure_index is outside the available core edges")
    demand_days = scenario.get("demand_days", 14)
    horizon = scenario.get("horizon", 40)
    failure_days = scenario.get("failure_days", 3)
    for name, value, low, high in (
        ("demand_days", demand_days, 1, 30),
        ("horizon", horizon, 2, 120),
        ("failure_days", failure_days, 1, 30),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"{name} must be an integer from {low} through {high}")
    if horizon <= demand_days:
        raise ValueError("horizon must exceed demand_days so the simulator can drain traffic")
    return {
        "sample_index": sample_index,
        "closure_index": closure_index,
        "demand_days": demand_days,
        "horizon": horizon,
        "failure_days": failure_days,
    }


def _load_optimizer_modules(root: Path):
    opt_dir = str(root / "opt")
    inserted = opt_dir not in sys.path
    if inserted:
        sys.path.insert(0, opt_dir)
    try:
        import c_multiflow
        import c_uncertainty
    finally:
        if inserted and sys.path and sys.path[0] == opt_dir:
            sys.path.pop(0)
    return c_multiflow, c_uncertainty


def _simulation_summary(result: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "generated",
        "delivered",
        "unmet",
        "shipping_cost",
        "waiting_cost",
        "total_cost",
        "recovery_days",
        "recovery_censored",
    )
    return {key: result[key] for key in keys}


def run_supplyshield(
    scenario: dict[str, Any],
    *,
    root: str | Path = ROOT,
    progress: Callable[[str, str, str], None] | None = None,
) -> dict[str, Any]:
    """Run live inference, uncertainty, risk, optimization, and simulation.

    Scenario indices map to anonymized options from tracked later-period model
    inputs and the tracked core network. The return value contains aggregate
    metrics only and no route, shipment, trip, or OD identifiers.
    """
    root = Path(root).resolve()
    states = {name: {"status": "Pending", "message": "Not started"} for name in STAGE_NAMES}
    output: dict[str, Any] = {"status": "RUNNING", "stages": states, "result": {}}
    active_stage = STAGE_NAMES[0]

    def set_stage(name: str, status: str, message: str) -> None:
        safe = redact_sensitive_text(message)
        states[name] = {"status": status, "message": safe}
        if progress is not None:
            progress(name, status, safe)

    def begin(name: str, message: str) -> None:
        nonlocal active_stage
        active_stage = name
        set_stage(name, "Running", message)

    try:
        begin(STAGE_NAMES[0], "Checking selected sample, closure, and supported simulator settings.")
        catalog = _load_catalog(root)
        settings = _validate_scenario(scenario, catalog)
        sample = catalog.samples.iloc[settings["sample_index"]]
        closure = catalog.closures[settings["closure_index"]]
        set_stage(STAGE_NAMES[0], "Completed", "Scenario inputs are valid and map to tracked project data.")

        begin(STAGE_NAMES[1], "Loading authoritative training demand and the existing core graph.")
        processed = root / "data" / "processed"
        input_paths = {
            "core_train_legs": processed / "core_train_legs.csv",
            "core_edges": processed / "core_edges.csv",
            "core_nodes": processed / "core_nodes.csv",
            "split_trip_ids": processed / "split_trip_ids.csv",
        }
        for path in input_paths.values():
            if not path.is_file():
                raise FileNotFoundError(f"Required tracked input missing: {path.relative_to(root)}")

        from models import day6_integration as day6

        demand_inputs = day6.build_demand_inputs(
            input_paths["core_train_legs"],
            input_paths["core_edges"],
            input_paths["core_nodes"],
            input_paths["split_trip_ids"],
        )
        graph = day6._load_c_graph(root, input_paths)
        demands = {tuple(map(str, key)): float(value) for key, value in demand_inputs.demands.items()}
        graph_edges = {tuple(map(str, edge)) for edge in graph.edges}
        if graph_edges != set(demands):
            raise ValueError("Simulator graph and authoritative training demand do not match")
        graph.graph["demands"] = demands
        graph.graph["unmet_penalty"] = 96.0
        optimizer_graph = day6.optimizer_graph_with_authoritative_demand(graph, demands)
        optimizer_graph.graph["demands"] = demands
        multiflow, uncertainty = _load_optimizer_modules(root)
        from sim.simulator import simulate
        from models import prediction_api as api
        from models.shap_explainability import calculate_native_contributions

        set_stage(STAGE_NAMES[1], "Completed", "Tracked network and split-verified demand are ready.")

        begin(STAGE_NAMES[2], "Loading the frozen XGBoost model and scoring the selected feature sample.")
        model = api.load_model()
        request = {
            "source_center": str(sample["source_center"]),
            "destination_center": str(sample["destination_center"]),
            "route_type": str(sample["route_type"]),
            "od_start_time": sample["od_start_time"],
            "osrm_time_min": float(sample["osrm_time_min"]),
            "osrm_distance_km": float(sample["osrm_distance_km"]),
            "lane_base": float(sample["lane_base"]),
            "lane_history_count": int(sample["n_train_legs"]),
        }
        feature_matrix = api.build_feature_matrix(request)
        prediction = api.predict_single(request, model=model, include_intervals=False)
        if isinstance(prediction, pd.DataFrame):
            prediction_row = prediction.iloc[0].to_dict()
        elif isinstance(prediction, pd.Series):
            prediction_row = prediction.to_dict()
        else:
            prediction_row = dict(prediction)
        pred_ratio = float(prediction_row["pred_ratio"])
        lane_base = float(request["lane_base"])
        if not np.isfinite(pred_ratio) or pred_ratio <= 0 or lane_base <= 0:
            raise ValueError("Live model returned a nonpositive or non-finite travel ratio")
        set_stage(STAGE_NAMES[2], "Completed", "Current model inference completed on the selected feature sample.")

        begin(STAGE_NAMES[3], "Applying the saved Method C conformal calibration to the live prediction.")
        conformal_parameters = api.load_conformal_parameters()
        prediction_with_intervals = api.apply_conformal_intervals(
            pd.DataFrame([prediction_row]), parameters=conformal_parameters
        )
        interval_row = prediction_with_intervals.iloc[0].to_dict()
        for key in ("lower_50", "upper_50", "lower_80", "upper_80", "lower_90", "upper_90"):
            if key not in interval_row or not np.isfinite(float(interval_row[key])):
                raise ValueError(f"Conformal output is missing a finite {key} bound")
        set_stage(STAGE_NAMES[3], "Completed", "Live 50%, 80%, and 90% Method C ratio intervals were calculated.")

        begin(STAGE_NAMES[4], "Combining the live point risk with the existing C uncertainty LP.")
        edges = list(optimizer_graph.edges)
        edge_index = {tuple(map(str, edge)): i for i, edge in enumerate(edges)}
        risk_lookup = catalog.risk.set_index(["source_center", "destination_center"])
        point = np.asarray(
            [float(risk_lookup.loc[(str(u), str(v)), "mult_pred"]) for u, v in edges],
            dtype=float,
        )
        lower90 = np.asarray(
            [float(risk_lookup.loc[(str(u), str(v)), "mult_lo90"]) for u, v in edges],
            dtype=float,
        )
        upper90 = np.asarray(
            [float(risk_lookup.loc[(str(u), str(v)), "mult_hi90"]) for u, v in edges],
            dtype=float,
        )
        sample_edge = (str(request["source_center"]), str(request["destination_center"]))
        sample_edge_idx = edge_index.get(sample_edge)
        if sample_edge_idx is None:
            raise ValueError("Selected model sample is not a directed edge in the optimizer graph")
        live_multiplier = pred_ratio / lane_base
        live_lower90 = float(interval_row["lower_90"]) / lane_base
        live_upper90 = float(interval_row["upper_90"]) / lane_base
        point[sample_edge_idx] = live_multiplier
        lower90[sample_edge_idx] = live_lower90
        upper90[sample_edge_idx] = live_upper90
        if not np.isfinite(point).all() or (point <= 0).any():
            raise ValueError("Risk multipliers must be positive and finite")
        if not ((lower90 <= point) & (point <= upper90)).all():
            raise ValueError("Risk point estimates must lie within the 90% multiplier bounds")
        cost = np.asarray([float(optimizer_graph.edges[edge]["cost"]) for edge in edges])
        cvar_summary: dict[str, Any] = {
            "available": False,
            "reason": "The selected live conformal bound cannot be represented by the existing lognormal multiplier method.",
            "route_plan_used_by_simulator": False,
        }
        cvar_warning = cvar_summary["reason"]
        if (lower90 > 0).all() and (upper90 > 0).all():
            try:
                sd = np.maximum(np.log(upper90) - np.log(lower90), 0.0) / (2 * Z90)
                plan_scenarios = np.exp(
                    np.log(point)[None, :]
                    + sd[None, :] * np.random.default_rng(0).standard_normal((PLAN_SCENARIOS, len(edges)))
                )
                cvar_flow, cvar_unmet = uncertainty.solve(
                    optimizer_graph, closure, scen=plan_scenarios, alpha=ALPHA
                )
                eval_scenarios = np.exp(
                    np.log(point)[None, :]
                    + sd[None, :] * np.random.default_rng(1000).standard_normal(
                        (EVALUATION_SCENARIOS, len(edges))
                    )
                )
                penalty = float(multiflow.rg.PENALTY_HOURS)
                cvar_cost_samples = (eval_scenarios * cost) @ cvar_flow + penalty * cvar_unmet
                cvar_summary = {
                    "available": True,
                    "alpha": ALPHA,
                    "planning_scenarios": PLAN_SCENARIOS,
                    "evaluation_scenarios": EVALUATION_SCENARIOS,
                    "planning_seed": 0,
                    "evaluation_seed": 1000,
                    "expected_cost_leg_hours_per_day": float(cvar_cost_samples.mean()),
                    "cvar_cost_leg_hours_per_day": float(uncertainty.cvar(cvar_cost_samples, ALPHA)),
                    "worst_evaluation_cost_leg_hours_per_day": float(cvar_cost_samples.max()),
                    "undelivered_legs_per_day": float(cvar_unmet),
                    "method": "Person C lognormal multiplier scenarios and CVaR LP; seeded scenario draws",
                    "route_plan_used_by_simulator": False,
                }
                cvar_warning = (
                    "Live point risk and C CVaR were calculated. C CVaR returns aggregate edge totals, not simulator OD routes; the simulator will receive the point-risk-weighted multi-flow plan."
                )
            except (ValueError, RuntimeError, FloatingPointError, np.linalg.LinAlgError) as exc:
                cvar_warning = f"CVaR unavailable for this scenario: {type(exc).__name__}: {exc}"
                cvar_summary["reason"] = redact_sensitive_text(cvar_warning)
        else:
            cvar_warning = "CVaR unavailable: the existing lognormal multiplier method requires strictly positive interval bounds."
        point_multipliers = {tuple(map(str, edge)): float(point[i]) for i, edge in enumerate(edges)}
        risk_graph = optimizer_graph.copy()
        for edge, multiplier in point_multipliers.items():
            risk_graph.edges[edge]["cost"] = float(risk_graph.edges[edge]["cost"]) * multiplier
        set_stage(
            STAGE_NAMES[4],
            "Warning",
            cvar_warning,
        )

        begin(STAGE_NAMES[5], "Simulating baseline and disrupted direct-flow operations with the selected closure.")
        direct_plan = [
            {"od": [u, v], "edge": [u, v], "flow": amount}
            for (u, v), amount in sorted(demands.items())
            if amount > 1e-9
        ]
        base_scenario = {
            "demand_days": settings["demand_days"],
            "horizon": settings["horizon"],
            "failure_start": 0,
            "failure_days": settings["failure_days"],
            "closed_lanes": [],
            "travel_time_multipliers": point_multipliers,
        }
        baseline_simulation = simulate(graph.copy(), dict(base_scenario), plan=direct_plan)
        disrupted_scenario = dict(base_scenario)
        disrupted_scenario["closed_lanes"] = [list(closure)]
        disrupted_simulation = simulate(graph.copy(), disrupted_scenario, plan=direct_plan)
        set_stage(STAGE_NAMES[5], "Completed", "Baseline and no-reroute disruption simulations completed.")

        begin(STAGE_NAMES[6], "Running Person C multi-flow LP on the disrupted, point-risk-weighted graph.")
        optimizer_return = multiflow.solve_multiflow(
            risk_graph, closed=closure, return_plan=True
        )
        normalized = day6.normalize_optimizer_return(
            optimizer_return,
            demands,
            risk_graph,
            penalty_value=float(multiflow.rg.PENALTY_HOURS),
            closed_lanes={closure},
            demand_provenance=demand_inputs.reconciliation,
        )
        recovered_plan = normalized["edge_flow_records"]
        set_stage(STAGE_NAMES[6], "Completed", "The live closure-specific multi-flow LP returned a reconciled OD route plan.")

        begin(STAGE_NAMES[7], "Passing the actual optimized plan to the simulator and reconciling aggregate outcomes.")
        recovered_simulation = simulate(graph.copy(), disrupted_scenario, plan=recovered_plan)
        simulations = {
            "baseline": _simulation_summary(baseline_simulation),
            "disrupted_no_reroute": _simulation_summary(disrupted_simulation),
            "recovered": _simulation_summary(recovered_simulation),
        }
        for name, value in simulations.items():
            if abs(value["generated"] - value["delivered"] - value["unmet"]) > 1e-6:
                raise AssertionError(f"{name} aggregate demand does not reconcile")
        if abs(simulations["baseline"]["generated"] - simulations["recovered"]["generated"]) > 1e-6:
            raise AssertionError("Simulation scenarios generated different total demand")
        evaluation = {
            "delivered_gain_vs_disruption": simulations["recovered"]["delivered"]
            - simulations["disrupted_no_reroute"]["delivered"],
            "unmet_change_vs_disruption": simulations["recovered"]["unmet"]
            - simulations["disrupted_no_reroute"]["unmet"],
            "total_cost_change_vs_disruption": simulations["recovered"]["total_cost"]
            - simulations["disrupted_no_reroute"]["total_cost"],
            "demand_reconciliation": "PASS",
            "horizon_censoring_present": any(
                bool(value["recovery_censored"]) for value in simulations.values()
            ),
        }
        set_stage(STAGE_NAMES[7], "Completed", "Generated, delivered, unmet, cost, recovery, and censoring are summarized from simulator outputs.")

        begin(STAGE_NAMES[8], "Calculating native TreeSHAP contributions for the same live model input.")
        residuals, contributions, bias, shap_validation = calculate_native_contributions(
            feature_matrix, model
        )
        if not np.isclose(float(residuals[0]), float(prediction_row["predicted_residual"]), rtol=0, atol=shap_validation["additivity_atol"]):
            raise AssertionError("Native TreeSHAP prediction does not match the live API prediction")
        shap_row = contributions.iloc[0]
        top_features = [
            {"feature": str(name), "contribution_to_residual": float(shap_row[name])}
            for name in shap_row.abs().sort_values(ascending=False).head(5).index
        ]
        set_stage(STAGE_NAMES[8], "Completed", "Native contributions passed the model additivity check.")

        output["status"] = "COMPLETE_WITH_WARNINGS"
        output["result"] = {
            "scenario": {
                "sample_option": settings["sample_index"] + 1,
                "closure_option": settings["closure_index"] + 1,
                "demand_days": settings["demand_days"],
                "horizon_days": settings["horizon"],
                "closure_days": settings["failure_days"],
                "prediction_sample_source": "tracked core_later_legs.csv, model-input columns only",
            },
            "prediction": {
                "predicted_residual": float(prediction_row["predicted_residual"]),
                "pred_ratio": pred_ratio,
                "predicted_travel_time_min": float(prediction_row["predicted_travel_time_min"]),
                "lane_base": lane_base,
                "lane_history_count": int(request["lane_history_count"]),
                "model_artifact": "models/residual_xgb_plain_master_split_v1.json",
            },
            "uncertainty": {
                "method": "Saved Method C split-conformal calibration, live application",
                "ratio_intervals": {
                    str(level): [float(interval_row[f"lower_{level}"]), float(interval_row[f"upper_{level}"])]
                    for level in ("50", "80", "90")
                },
            },
            "risk_cvar": {
                "selected_sample_multiplier": live_multiplier,
                "other_edge_multipliers": "tracked Person C/B lane risk reference values",
                "cvar": cvar_summary,
                "optimizer_uses": "point-risk weighted edge costs",
                "cvar_limitation": "CVaR LP result is not simulator-compatible because its public return omits per-OD route records.",
            },
            "optimizer": {
                "implementation": "Person C opt/c_multiflow.py solve_multiflow",
                "status": normalized["status"],
                "objective_leg_hours_per_day": normalized["objective_value"],
                "total_unmet_legs_per_day": normalized["total_unmet_flow"],
                "plan_records": len(recovered_plan),
                "plan_passed_to_simulator": True,
            },
            "simulations": simulations,
            "evaluation": evaluation,
            "explainability": {
                "method": "Native XGBoost TreeSHAP contributions to predicted residual",
                "top_features": top_features,
                "max_abs_additivity_error": shap_validation["max_abs_additivity_error"],
            },
            "weather": {
                "status": "OPTIONAL_NOT_CONNECTED",
                "reason": "The frozen prediction feature schema has no weather feature; the existing weather pipeline downloads external historical weather.",
            },
            "privacy": "Aggregate outputs only; no route, shipment, trip, or OD identifiers are returned.",
        }
    except Exception as exc:
        set_stage(active_stage, "Failed", f"{type(exc).__name__}: {exc}")
        output["status"] = "FAILED"
        output["error"] = redact_sensitive_text(f"{type(exc).__name__}: {exc}")
    return output
