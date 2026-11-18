"""Person B Day 6 demand, optimizer-result, and queue integration adapters."""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Mapping

import numpy as np
import pandas as pd
from sim.simulator import simulate


WINDOW_DAYS = 14
RISK_COLUMNS = {
    "baseline_ratio", "pred_ratio", "lo90", "hi90", "pred_excess_h"
}
RISK_MULTIPLIER_COLUMNS = {
    "mult_pred", "mult_lo50", "mult_hi50", "mult_lo90", "mult_hi90",
}


@dataclass(frozen=True)
class DemandInputs:
    """Validated inputs and leg-count reconciliation for the frozen core."""

    demands: dict[tuple[str, str], float]
    lane_counts: dict[tuple[str, str], int]
    reconciliation: dict[str, int | float | str]
    node_capacities: dict[str, float]


def build_demand_inputs(
    legs_path: str | Path,
    edges_path: str | Path,
    nodes_path: str | Path,
    split_path: str | Path | None = None,
) -> DemandInputs:
    """Build per-OD daily demand from the complete master-split training cohort.

    Each input row is a leg. The approved cohort is every row in
    ``core_train_legs.csv`` whose trip is labelled train in the master split,
    divided by the 14-day observation period. Departure timestamps do not
    filter this population; the strict in-window count is recorded separately.
    """
    legs = pd.read_csv(legs_path)
    edges = pd.read_csv(edges_path)
    nodes = pd.read_csv(nodes_path)
    required_legs = {"trip_uuid", "trip_creation_time", "od_start_time",
                     "source_center", "destination_center"}
    if missing := required_legs - set(legs.columns):
        raise ValueError(f"Leg input is missing columns: {sorted(missing)}")
    if not {"source", "destination"} <= set(edges.columns):
        raise ValueError("Core edges require source and destination columns")
    if not {"hub", "capacity_est"} <= set(nodes.columns):
        raise ValueError("Core nodes require hub and capacity_est columns")
    if edges.duplicated(["source", "destination"]).any():
        raise ValueError("Core edges contain duplicate directed lanes")
    if nodes["hub"].duplicated().any():
        raise ValueError("Core nodes contain duplicate hub IDs")

    if split_path is None:
        raise ValueError("The authoritative master split is required for demand construction")
    split = pd.read_csv(split_path)
    if not {"trip_uuid", "split"} <= set(split.columns):
        raise ValueError("Master split requires trip_uuid and split columns")
    if split["trip_uuid"].duplicated().any():
        raise ValueError("Master split contains duplicate trip IDs")
    split_map = split.set_index("trip_uuid")["split"]
    labels = legs["trip_uuid"].map(split_map)
    if labels.isna().any() or labels.ne("train").any():
        raise ValueError("core_train_legs contains trip IDs not labelled train in the master split")
    split_check = {"checked": int(labels.notna().sum()), "non_train_trip_ids": 0}

    created = pd.to_datetime(legs["trip_creation_time"], errors="coerce")
    departed = pd.to_datetime(legs["od_start_time"], errors="coerce")
    strict_window = (
        created.ge(pd.Timestamp("2018-09-12"))
        & created.lt(pd.Timestamp("2018-09-26"))
        & departed.ge(pd.Timestamp("2018-09-12"))
        & departed.lt(pd.Timestamp("2018-09-26"))
    )

    core_lanes = set(zip(edges["source"].astype(str), edges["destination"].astype(str)))
    row_lanes = list(zip(legs["source_center"].astype(str), legs["destination_center"].astype(str)))
    is_core_lane = pd.Series([lane in core_lanes for lane in row_lanes], index=legs.index)
    if not is_core_lane.all():
        bad = sorted(set(lane for lane, is_core in zip(row_lanes, is_core_lane) if not is_core))
        raise ValueError(f"Training legs contain directed ODs outside core_edges: {bad[:10]}")
    counts = legs.groupby(
        ["source_center", "destination_center"], sort=True
    ).size()

    # Include every frozen directed lane, even if its current demand is zero.
    lane_counts = {lane: int(counts.get(lane, 0)) for lane in sorted(core_lanes)}
    demands = {lane: count / WINDOW_DAYS for lane, count in lane_counts.items()}
    capacities = pd.to_numeric(nodes.set_index("hub")["capacity_est"], errors="coerce")
    if capacities.isna().any() or (~np.isfinite(capacities)).any() or capacities.lt(0).any():
        raise ValueError("Core node capacities must be finite and nonnegative")

    edge_trip_counts = {
        (str(row.source), str(row.destination)): int(row.trips)
        for row in edges.itertuples(index=False)
    } if "trips" in edges.columns else {}
    if edge_trip_counts and any(edge_trip_counts[lane] != lane_counts[lane] for lane in core_lanes):
        raise ValueError("core_edges trips counts differ from master-split training leg counts")
    reconciliation: dict[str, int | float | str] = {
        "population": "all core_train_legs rows labelled train in split_trip_ids.csv",
        "initial_core_train_leg_rows": int(len(legs)),
        "master_split_train_leg_rows": int(labels.eq("train").sum()),
        "strict_created_and_departed_window_rows_informational": int(strict_window.sum()),
        "strict_window_rows_excluded_from_authoritative_population": 0,
        "invalid_or_noncore_od_rows": 0,
        "unique_core_od_pairs_with_training_legs": int(len(counts)),
        "frozen_directed_lanes": int(len(core_lanes)),
        "observation_days": WINDOW_DAYS,
        "requested_legs_per_day": float(sum(demands.values())),
        "optimizer_current_core_edges_trips_sum": int(pd.to_numeric(edges["trips"]).sum())
        if "trips" in edges.columns else -1,
        "master_split_rows_checked": split_check["checked"],
        "non_train_or_unmapped_trip_rows": split_check["non_train_trip_ids"],
    }
    if int(labels.eq("train").sum()) != len(legs) or sum(lane_counts.values()) != len(legs):
        raise AssertionError("Training demand rows do not reconcile to all core training legs")
    return DemandInputs(demands, lane_counts, reconciliation, capacities.to_dict())


def validate_risk_table(risk_path: str | Path, directed_lanes: set[tuple[str, str]]) -> pd.DataFrame:
    """Validate full directed-lane coverage and required finite prediction fields."""
    risk = pd.read_csv(risk_path)
    keys = {"source_center", "destination_center"}
    interval_columns = {"lo50", "hi50"}
    required_columns = keys | RISK_COLUMNS | interval_columns | RISK_MULTIPLIER_COLUMNS
    missing_columns = required_columns - set(risk.columns)
    if missing_columns:
        raise ValueError(f"Risk table is missing required columns: {sorted(missing_columns)}")
    if risk[list(keys)].isna().any().any():
        raise ValueError("Risk table has missing directed lane identifiers")
    if risk.duplicated(["source_center", "destination_center"]).any():
        raise ValueError("Risk table contains duplicate directed lane keys")
    risk_lanes = set(zip(risk.source_center.astype(str), risk.destination_center.astype(str)))
    missing = directed_lanes - risk_lanes
    extra = risk_lanes - directed_lanes
    if missing or extra:
        raise ValueError(f"Risk coverage mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    numeric_columns = RISK_COLUMNS | interval_columns | RISK_MULTIPLIER_COLUMNS
    values = risk[sorted(numeric_columns)].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("Risk table contains missing or non-finite required risk values")
    if values["baseline_ratio"].le(0).any():
        raise ValueError("Risk table baseline_ratio must be positive")
    if values["mult_pred"].le(0).any():
        raise ValueError("Risk table mult_pred must be positive")
    if values[["mult_lo50", "mult_hi50", "mult_lo90", "mult_hi90"]].lt(0).any().any():
        raise ValueError("Risk table interval multipliers must be nonnegative")
    if values[["lo50", "lo90"]].lt(0).any().any():
        raise ValueError("Risk table lower ratio bounds must be nonnegative")

    ratio_ordered = (
        values["lo90"].le(values["lo50"])
        & values["lo50"].le(values["pred_ratio"])
        & values["pred_ratio"].le(values["hi50"])
        & values["hi50"].le(values["hi90"])
    )
    multiplier_ordered = (
        values["mult_lo90"].le(values["mult_lo50"])
        & values["mult_lo50"].le(values["mult_pred"])
        & values["mult_pred"].le(values["mult_hi50"])
        & values["mult_hi50"].le(values["mult_hi90"])
    )
    if not ratio_ordered.all():
        raise ValueError("Risk table ratio intervals are not nested around pred_ratio")
    if not multiplier_ordered.all():
        raise ValueError("Risk table multiplier intervals are not nested around mult_pred")
    # Values are returned as read; this adapter never substitutes realized outcomes
    # or turns risk predictions into optimizer costs/capacities.
    return risk


def apply_risk_adjusted_durations(
    graph: Any,
    risk: pd.DataFrame,
) -> dict[tuple[str, str], float]:
    """Build A's directed ``travel_time_multipliers`` scenario mapping.

    The simulator reads baseline hours from the untouched graph edge ``cost``
    and applies each canonical Person B ``mult_pred`` value once. This adapter
    returns tuple-keyed multipliers only; it never changes edge costs, capacity,
    trips, or the input graph.
    """
    if graph.graph.get("risk_adjustment_applied"):
        raise ValueError("Risk adjustment has already been applied to this graph")
    if set(graph.edges) != set(zip(risk.source_center.astype(str), risk.destination_center.astype(str))):
        raise ValueError("Risk table directed lanes must exactly match graph edges")
    multiplier = {
        (str(row.source_center), str(row.destination_center)): float(row.mult_pred)
        for row in risk.itertuples(index=False)
    }
    for edge in graph.edges:
        base_hours = float(graph.edges[edge].get("cost", float("nan")))
        mult_pred = multiplier[tuple(edge)]
        if not np.isfinite(base_hours) or base_hours <= 0:
            raise ValueError(f"Baseline edge cost must be finite positive hours: {edge}")
        if not np.isfinite(mult_pred) or mult_pred <= 0:
            raise ValueError(f"Risk mult_pred must be finite positive: {edge}")
        adjusted_hours = base_hours * mult_pred
        if not np.isfinite(adjusted_hours) or adjusted_hours <= 0:
            raise ValueError(f"Adjusted edge duration must be finite positive: {edge}")
    return multiplier


def attach_travel_time_multipliers(
    scenario: dict[str, Any],
    multipliers: Mapping[tuple[str, str], float],
) -> dict[str, Any]:
    """Attach the validated directed mapping once, without changing graph costs."""
    if "travel_time_multipliers" in scenario and scenario["travel_time_multipliers"] is not None:
        raise ValueError("Risk adjustment is already present in this scenario")
    scenario["travel_time_multipliers"] = dict(multipliers)
    return scenario


def optimizer_graph_with_authoritative_demand(graph: Any, demands: Mapping[tuple[str, str], float]):
    """Copy C's graph and encode the agreed legs/day vector in its trips/14 input.

    ``solve_multiflow`` currently derives daily demand from ``edge['trips'] /
    TRAIN_DAYS``.  This adapter preserves that solver convention while ensuring
    the supplied 14-day departure counts, rather than stale edge membership
    counts, drive demand.  It does not expose the solver's result vector.
    """
    graph_lanes = set(graph.edges)
    normalized = {tuple(lane): float(amount) for lane, amount in demands.items()}
    if graph_lanes != set(normalized):
        raise ValueError(
            f"Optimizer graph/demand lane mismatch: missing={sorted(graph_lanes - set(normalized))}, "
            f"extra={sorted(set(normalized) - graph_lanes)}"
        )
    if any(not np.isfinite(value) or value < 0 for value in normalized.values()):
        raise ValueError("Authoritative daily demands must be finite and nonnegative")
    prepared = graph.copy()
    for lane, daily_rate in normalized.items():
        prepared.edges[lane]["trips"] = daily_rate * WINDOW_DAYS
    return prepared


def validate_optimizer_plan(
    result: Mapping[str, Any],
    demands: Mapping[tuple[str, str], float],
    directed_lanes: set[tuple[str, str]],
    node_capacities: Mapping[str, float],
    *,
    closed_lanes: set[tuple[str, str]] | None = None,
    tolerance: float = 1e-6,
) -> dict[tuple[str, str], dict[tuple[str, str], float]]:
    """Validate a per-OD LP result and return the nested queue-plan shape.

    Expected result keys are ``status``, ``flows`` (OD -> edge -> legs/day),
    ``unmet`` (OD -> legs/day), and objective metadata.  The current Person C
    solver does not yet return this structure; this function intentionally
    refuses aggregate-only output.
    """
    status = result.get("status")
    if status not in {"optimal", "optimal_inaccurate"} and not (
        status == "unavailable" and result.get("optimizer_returned_normally") is True
    ):
        raise ValueError("Optimizer status is unsuccessful or unavailable without a normal return")
    flows = result.get("flows")
    unmet = result.get("unmet")
    result_demands = result.get("demands")
    if not isinstance(flows, Mapping) or not isinstance(unmet, Mapping):
        raise ValueError("Optimizer result must expose per-OD flows and unmet rates")
    if not isinstance(result_demands, Mapping):
        raise ValueError("Optimizer result must include its per-OD demand vector")
    if result.get("flow_unit") != "legs/day":
        raise ValueError("Optimizer result must declare flow_unit='legs/day'")
    objective = result.get("objective")
    objective_keys = {
        "travel_leg_hours_per_day", "unmet_penalty_leg_hours_per_day",
        "total_leg_hours_per_day",
    }
    if not isinstance(objective, Mapping) or not objective_keys <= set(objective):
        raise ValueError("Optimizer result must expose daily travel, penalty, and total objective terms")
    objective_values = {key: float(objective[key]) for key in objective_keys}
    if not np.isfinite(list(objective_values.values())).all() or min(objective_values.values()) < -tolerance:
        raise ValueError("Optimizer objective terms must be finite and nonnegative")
    if abs(objective_values["total_leg_hours_per_day"] - (
        objective_values["travel_leg_hours_per_day"] + objective_values["unmet_penalty_leg_hours_per_day"]
    )) > tolerance:
        raise ValueError("Optimizer objective terms do not sum to the reported total")
    normalized_demands = {tuple(k): float(v) for k, v in demands.items()}
    reported_demands = {tuple(k): float(v) for k, v in result_demands.items()}
    if set(reported_demands) != set(normalized_demands) or any(
        not np.isfinite(reported_demands[k])
        or abs(reported_demands[k] - value) > tolerance
        for k, value in normalized_demands.items()
    ):
        raise ValueError("Optimizer's reported demand differs from authoritative demand")
    normalized_flows = {tuple(od): {tuple(e): float(v) for e, v in edges.items()}
                        for od, edges in flows.items()}
    normalized_unmet = {tuple(od): float(v) for od, v in unmet.items()}
    if set(normalized_flows) != set(normalized_demands) or set(normalized_unmet) != set(normalized_demands):
        raise ValueError("Optimizer OD keys must exactly match authoritative demand keys")
    closed = closed_lanes or set()
    aggregate_out = {node: 0.0 for node in node_capacities}
    for od, amount in normalized_demands.items():
        if not np.isfinite(amount) or amount < -tolerance:
            raise ValueError(f"Invalid demand for OD {od}")
        miss = normalized_unmet[od]
        if not np.isfinite(miss) or miss < -tolerance or miss > amount + tolerance:
            raise ValueError(f"Invalid unmet rate for OD {od}")
        balance = {n: 0.0 for n in node_capacities}
        for edge, amount_on_edge in normalized_flows[od].items():
            if edge not in directed_lanes:
                raise ValueError(f"Optimizer plan uses an unknown directed lane: {edge}")
            if edge in closed and amount_on_edge > tolerance:
                raise ValueError(f"Optimizer plan uses closed lane {edge}")
            if not np.isfinite(amount_on_edge) or amount_on_edge < -tolerance:
                raise ValueError(f"Invalid flow on lane {edge}")
            u, v = edge
            balance[u] += amount_on_edge
            balance[v] -= amount_on_edge
            aggregate_out[u] += amount_on_edge
        served = amount - miss
        for node, net_out in balance.items():
            expected = served if node == od[0] else -served if node == od[1] else 0.0
            if abs(net_out - expected) > tolerance:
                raise ValueError(f"OD flow conservation failed for {od} at {node}")
    for node, amount in aggregate_out.items():
        cap = float(node_capacities[node])
        if not np.isfinite(cap) or cap < 0 or amount > cap + tolerance:
            raise ValueError(f"Shared outgoing capacity exceeded at {node}")
    return normalized_flows


def normalize_optimizer_return(
    optimizer_return: tuple[float, float, list[dict[str, Any]]],
    demands: Mapping[tuple[str, str], float],
    graph: Any,
    *,
    penalty_value: float,
    closed_lanes: set[tuple[str, str]] | None = None,
    demand_provenance: Mapping[str, Any] | None = None,
    tolerance: float = 1e-5,
) -> dict[str, Any]:
    """Normalize Person C's actual ``(cost, unmet, flat_records)`` return.

    The current API does not return solver status or an objective breakdown.
    Status is explicitly marked unavailable. Served/unmet per OD and travel
    cost are reconstructed from the returned edge records and authoritative
    demand, then checked against the optimizer's scalar return.
    """
    if not isinstance(optimizer_return, tuple) or len(optimizer_return) != 3:
        raise ValueError("Expected solve_multiflow(..., return_plan=True) triple")
    objective_value, returned_unmet, records = optimizer_return
    objective_value, returned_unmet, penalty_value = map(
        float, (objective_value, returned_unmet, penalty_value)
    )
    if not np.isfinite([objective_value, returned_unmet, penalty_value]).all() or min(
        objective_value, returned_unmet, penalty_value
    ) < 0:
        raise ValueError("Optimizer scalar outputs and penalty must be finite and nonnegative")
    if not isinstance(records, list):
        raise ValueError("Optimizer plan must be a flat list of OD-edge-flow records")

    normalized_demands = {tuple(od): float(value) for od, value in demands.items()}
    if any(not np.isfinite(value) or value < 0 for value in normalized_demands.values()):
        raise ValueError("Authoritative demand must be finite and nonnegative")
    lanes = set(graph.edges)
    flows = {od: {} for od in normalized_demands}
    for record in records:
        try:
            od, edge, value = tuple(record["od"]), tuple(record["edge"]), float(record["flow"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Optimizer plan records require od, edge, and flow") from exc
        if od not in flows:
            raise ValueError(f"Optimizer plan contains an OD outside authoritative demand: {od}")
        if edge not in lanes:
            raise ValueError(f"Optimizer plan contains an unknown directed lane: {edge}")
        if not np.isfinite(value) or value < 0:
            raise ValueError("Optimizer plan contains a non-finite or negative flow")
        flows[od][edge] = flows[od].get(edge, 0.0) + value

    served = {
        od: sum(value for (u, _), value in edge_flows.items() if u == od[0])
        for od, edge_flows in flows.items()
    }
    unmet = {}
    for od, requested in normalized_demands.items():
        difference = requested - served[od]
        if difference < -tolerance:
            raise ValueError(f"Optimizer served more than requested for OD {od}")
        unmet[od] = max(0.0, difference)

    total_requested = float(sum(normalized_demands.values()))
    total_served = float(sum(served.values()))
    total_unmet = float(sum(unmet.values()))
    reconcile_tol = max(tolerance, total_requested * 1e-6)
    if abs(returned_unmet - total_unmet) > reconcile_tol:
        raise ValueError(
            f"Optimizer total unmet ({returned_unmet}) differs from plan-derived unmet ({total_unmet})"
        )

    closed = {tuple(edge) for edge in (closed_lanes or set())}
    travel = sum(
        amount * float(graph.edges[edge]["cost"])
        for per_od in flows.values() for edge, amount in per_od.items()
    )
    penalty_cost = penalty_value * total_unmet
    reconstructed = travel + penalty_cost
    cost_tol = max(tolerance, abs(objective_value) * 1e-6)
    if abs(objective_value - reconstructed) > cost_tol:
        raise ValueError(
            "Optimizer objective differs from returned lane flows plus penalty "
            f"(solver={objective_value}, reconstructed={reconstructed}, tol={cost_tol})"
        )

    per_od = [
        {
            "od": [od[0], od[1]],
            "requested_flow": normalized_demands[od],
            "served_flow": served[od],
            "unmet_flow": unmet[od],
            "edge_flows": [
                {"edge": [edge[0], edge[1]], "flow": amount}
                for edge, amount in flows[od].items() if amount > 0
            ],
        }
        for od in normalized_demands
    ]
    return {
        "solver_status": None,
        "solver_status_available": False,
        "optimizer_returned_normally": True,
        "objective_value": objective_value,
        "objective_value_available": True,
        "total_requested_flow": total_requested,
        "total_served_flow": total_served,
        "total_unmet_flow": total_unmet,
        "requested_flow_per_od": normalized_demands,
        "served_flow_per_od": served,
        "unmet_flow_per_od": unmet,
        "flows": flows,
        "per_od": per_od,
        "edge_flow_records": [
            {"od": row["od"], "edge": edge["edge"], "flow": edge["flow"]}
            for row in per_od for edge in row["edge_flows"]
        ],
        "travel_cost_leg_hours_per_day": travel,
        "unmet_penalty_leg_hours_per_day": penalty_cost,
        "total_objective_leg_hours_per_day": objective_value,
        "reconstructed_objective_leg_hours_per_day": reconstructed,
        "flow_unit": "legs/day",
        "cost_unit": "leg-hours/day",
        "penalty_value_hours_per_unmet_leg": penalty_value,
        "closed_lanes": [[u, v] for u, v in sorted(closed)],
        "demand_provenance": dict(demand_provenance or {}),
        "status": "unavailable",
        "demands": normalized_demands,
        "unmet": unmet,
        "objective": {
            "travel_leg_hours_per_day": travel,
            "unmet_penalty_leg_hours_per_day": penalty_cost,
            "total_leg_hours_per_day": reconstructed,
        },
    }


def queue_plan_mapping(
    flows: Mapping[tuple[str, str], Mapping[tuple[str, str], float]],
) -> dict[tuple[str, str], dict[tuple[str, str], float]]:
    """Normalize the per-OD flow contract; does not imply A's queue API accepts it."""
    return {tuple(od): {tuple(edge): float(amount) for edge, amount in lane_flows.items()}
            for od, lane_flows in flows.items()}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            (f"{key[0]}->{key[1]}" if isinstance(key, tuple) and len(key) == 2 else str(key)):
            _json_safe(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_frozen_plans(
    plan_path: str | Path,
    demands: Mapping[tuple[str, str], float],
    directed_lanes: set[tuple[str, str]],
    *,
    tolerance: float = 1e-7,
) -> list[dict[str, Any]]:
    """Validate C's frozen 10 × 4 plan export without changing its records."""
    path = Path(plan_path)
    plans = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(plans, list) or len(plans) != 10:
        raise ValueError("Frozen plan must be a list of exactly 10 scenarios")
    expected_strategies = [
        "do nothing", "greedy", "preserve (affected flows only)", "LP (all flows)"
    ]
    normalized_demands = {tuple(k): float(v) for k, v in demands.items()}
    if not np.isfinite(list(normalized_demands.values())).all() or any(v < 0 for v in normalized_demands.values()):
        raise ValueError("Authoritative demands must be finite and nonnegative")
    for scenario_index, item in enumerate(plans, 1):
        expected_id = f"L{scenario_index:02d}"
        if item.get("id") != expected_id:
            raise ValueError(f"Expected frozen scenario {expected_id}")
        if item.get("penalty") != 96.0:
            raise ValueError(f"{expected_id}: frozen penalty must be 96.0")
        if item.get("flow_unit") != "legs per day" or item.get("cost_unit") != "leg-hours":
            raise ValueError(f"{expected_id}: unsupported frozen plan units")
        if item.get("horizon") != "one steady-state day":
            raise ValueError(f"{expected_id}: expected a one-day steady-state plan")
        demand_rows = item.get("demand")
        if not isinstance(demand_rows, list) or len(demand_rows) != len(normalized_demands):
            raise ValueError(f"{expected_id}: expected one demand row per directed OD")
        scenario_demands: dict[tuple[str, str], float] = {}
        for row in demand_rows:
            try:
                od = tuple(row["od"])
                value = float(row["legs_per_day"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{expected_id}: malformed demand row") from exc
            if len(od) != 2 or od in scenario_demands or not np.isfinite(value) or value < 0:
                raise ValueError(f"{expected_id}: invalid or duplicate OD demand")
            scenario_demands[od] = value
        if set(scenario_demands) != set(normalized_demands) or any(
            abs(scenario_demands[k] - value) > tolerance for k, value in normalized_demands.items()
        ):
            raise ValueError(f"{expected_id}: frozen demand differs from authoritative demand")
        closed_raw = item.get("closed_lanes")
        if not isinstance(closed_raw, list):
            raise ValueError(f"{expected_id}: closed_lanes must be a list")
        closed = {tuple(edge) for edge in closed_raw}
        if len(closed) != len(closed_raw) or not closed <= directed_lanes:
            raise ValueError(f"{expected_id}: invalid or duplicate closed directed lane")
        scenario_plans = item.get("plans")
        expected = item.get("expected")
        if not isinstance(scenario_plans, dict) or list(scenario_plans) != expected_strategies:
            raise ValueError(f"{expected_id}: frozen strategy names/order differ from contract")
        if not isinstance(expected, dict) or list(expected) != expected_strategies:
            raise ValueError(f"{expected_id}: expected metrics do not match strategy names/order")
        for strategy in expected_strategies:
            records = scenario_plans[strategy]
            if not isinstance(records, list):
                raise ValueError(f"{expected_id}/{strategy}: plan must be a record list")
            balances: dict[tuple[str, str], dict[str, float]] = {
                od: {node: 0.0 for edge in directed_lanes for node in edge}
                for od in normalized_demands
            }
            for record in records:
                try:
                    od = tuple(record["od"])
                    edge = tuple(record["edge"])
                    flow = float(record["flow"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"{expected_id}/{strategy}: malformed flow record") from exc
                if od not in normalized_demands or edge not in directed_lanes or len(od) != 2 or len(edge) != 2:
                    raise ValueError(f"{expected_id}/{strategy}: unknown OD or directed edge")
                if not np.isfinite(flow) or flow < 0:
                    raise ValueError(f"{expected_id}/{strategy}: flow must be finite and nonnegative")
                if edge in closed and flow > tolerance:
                    raise ValueError(f"{expected_id}/{strategy}: plan sends flow on its closed lane")
                u, v = edge
                balances[od][u] += flow
                balances[od][v] -= flow
            for od, balance in balances.items():
                served = balance[od[0]]
                if served < -tolerance or served > normalized_demands[od] + tolerance:
                    raise ValueError(f"{expected_id}/{strategy}: served OD flow exceeds demand")
                for node, net in balance.items():
                    target = served if node == od[0] else -served if node == od[1] else 0.0
                    if abs(net - target) > tolerance:
                        raise ValueError(f"{expected_id}/{strategy}: OD flow conservation failed")
            metrics = expected[strategy]
            if not isinstance(metrics, dict) or not {"shipping", "unmet", "total_cost"} <= set(metrics):
                raise ValueError(f"{expected_id}/{strategy}: expected metrics are incomplete")
            metric_values = [float(metrics[k]) for k in ("shipping", "unmet", "total_cost")]
            if not np.isfinite(metric_values).all() or min(metric_values) < -tolerance:
                raise ValueError(f"{expected_id}/{strategy}: expected metrics must be finite/nonnegative")
        daily_total = sum(scenario_demands.values())
        if not np.isclose(daily_total, 5395 / WINDOW_DAYS, rtol=0.0, atol=tolerance):
            raise ValueError(f"{expected_id}: daily demand does not represent 5,395 / 14")
    return plans


def _write_json_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(_json_safe(value), stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def run_real_integration(root: Path, output_dir: Path) -> dict[str, Any]:
    """Run all frozen C plans against the requested A simulator implementation.

    C plans describe static lane closures for a steady-state day. This integration
    represents each closure throughout the 14-day demand window, then drains
    within the simulator's 40-day horizon. Outputs are aggregate-only.
    """
    root = Path(root).resolve()
    output_dir = Path(output_dir)
    if not output_dir.is_absolute():
        output_dir = (root / output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing Day 6 output directory: {output_dir}")
    processed = root / "data" / "processed"
    input_paths = {
        "core_train_legs": processed / "core_train_legs.csv",
        "core_edges": processed / "core_edges.csv",
        "core_nodes": processed / "core_nodes.csv",
        "split_trip_ids": processed / "split_trip_ids.csv",
        "risk_table": root / "models" / "outputs" / "risk_table.csv",
        "frozen_plan": root / "experiments" / "c_multiflow_plans.json",
        "graph_builder": root / "opt" / "c_real_graph.py",
        "simulator": root / "sim" / "simulator.py",
    }
    for path in input_paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    inputs = build_demand_inputs(
        input_paths["core_train_legs"], input_paths["core_edges"],
        input_paths["core_nodes"], input_paths["split_trip_ids"],
    )
    risk = validate_risk_table(input_paths["risk_table"], set(inputs.demands))
    plan_cases = validate_frozen_plans(
        input_paths["frozen_plan"], inputs.demands, set(inputs.demands)
    )
    graph = _load_c_graph(root, input_paths)
    multipliers = apply_risk_adjusted_durations(graph, risk)
    graph.graph["demands"] = dict(inputs.demands)
    graph.graph["unmet_penalty"] = 96.0
    original_edges = {edge: dict(graph.edges[edge]) for edge in graph.edges}
    if set(multipliers) != set(graph.edges):
        raise ValueError("Risk multipliers do not exactly cover simulator graph edges")

    strategy_names = [
        "do nothing", "greedy", "preserve (affected flows only)", "LP (all flows)"
    ]
    summary_rows: list[dict[str, Any]] = []
    for plan_case in plan_cases:
        for strategy in strategy_names:
            scenario = {
                "id": plan_case["id"],
                "demand_days": 14,
                "horizon": 40,
                "failure_start": 0,
                "failure_days": 14,
                "closed_lanes": plan_case["closed_lanes"],
                "travel_time_multipliers": multipliers,
            }
            run_graph = graph.copy()
            simulation = simulate(run_graph, scenario, plan=plan_case["plans"][strategy])
            expected_generated = sum(inputs.demands.values()) * 14
            if abs(simulation["generated"] - expected_generated) > 1e-6:
                raise AssertionError(f"{plan_case['id']}/{strategy}: generated demand differs from 5,395")
            if abs(simulation["generated"] - simulation["delivered"] - simulation["unmet"]) > 1e-6:
                raise AssertionError(f"{plan_case['id']}/{strategy}: generated/delivered/unmet do not reconcile")
            if any(dict(run_graph.edges[edge]) != attrs for edge, attrs in original_edges.items()):
                raise AssertionError("Simulation changed baseline graph edge attributes")
            expected = plan_case["expected"][strategy]
            summary_rows.append({
                "scenario_id": plan_case["id"],
                "strategy": strategy,
                "closed_lane_count": len(plan_case["closed_lanes"]),
                "demand_legs": int(inputs.reconciliation["master_split_train_leg_rows"]),
                "demand_days": 14,
                "simulator_horizon_days": 40,
                "simulator_generated": simulation["generated"],
                "simulator_delivered": simulation["delivered"],
                "simulator_unmet": simulation["unmet"],
                "simulator_shipping_cost_leg_hour_equivalent": simulation["shipping_cost"],
                "simulator_waiting_cost_leg_hour_equivalent": simulation["waiting_cost"],
                "simulator_total_cost_leg_hour_equivalent": simulation["total_cost"],
                "recovery_days": simulation["recovery_days"],
                "recovery_censored": simulation["recovery_censored"],
                "c_expected_shipping_leg_hours_per_day": float(expected["shipping"]),
                "c_expected_unmet_legs_per_day": float(expected["unmet"]),
                "c_expected_total_leg_hours_per_day": float(expected["total_cost"]),
                "demand_conservation": "PASS",
                "baseline_edge_attributes_preserved": "PASS",
            })
    output_dir.mkdir(parents=True, exist_ok=False)
    summary_path = output_dir / "scenario_strategy_summary.csv"
    with summary_path.open("x", encoding="utf-8", newline="") as stream:
        pd.DataFrame(summary_rows).to_csv(stream, index=False)
    manifest = {
        "manifest_version": "1.0",
        "status": "COMPLETE_WITH_LIMITATIONS",
        "privacy_classification": "INTERNAL_ONLY_AGGREGATE_SCENARIO_SUMMARY",
        "scenario_count": 10,
        "strategy_count": 4,
        "successful_runs": len(summary_rows),
        "demand": {
            "population": "all core_train_legs rows verified as train in split_trip_ids.csv",
            "legs": int(inputs.reconciliation["master_split_train_leg_rows"]),
            "days": 14,
            "legs_per_day": float(sum(inputs.demands.values())),
            "strict_window_5357_is_informational_only": True,
        },
        "simulator_configuration": {
            "horizon_days": 40,
            "closure_start_day": 0,
            "closure_days": 14,
            "unmet_penalty_leg_hours_per_leg": 96.0,
            "travel_time_multipliers": "canonical mult_pred, tuple-keyed, applied by simulator once to baseline edge cost hours",
            "expected_metric_comparison": "not asserted: C expected values are steady-state per-day; queue outputs span the 14-day demand and 40-day horizon",
        },
        "source_identity": {
            "person_a_simulator_commit": "893a82a7fa731b95d97de8486cfa8ad59a848f38",
            "person_a_simulator_sha256": _sha256(input_paths["simulator"]),
            "person_b_adapter_sha256": _sha256(root / "models" / "day6_integration.py"),
            "person_b_integration_tests_sha256": _sha256(root / "models" / "test_day6_integration.py"),
            "frozen_plan_sha256": _sha256(input_paths["frozen_plan"]),
            "execution_note": "run from an isolated copy of the local repository with sim/ replaced by git archive of the verified Person A commit",
        },
        "inputs": {name: {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}
                   for name, path in input_paths.items()},
        "output": {"path": summary_path.relative_to(root).as_posix(), "sha256": _sha256(summary_path)},
        "limitations": [
            "The C plan's static closure is represented as active for all 14 demand days; this is an explicit integration interpretation, not an event-specific duration.",
            "Simulator totals are horizon-accumulated and are not directly comparable to C's one-day steady-state expected metrics.",
            "Summary contains no OD, lane, trip, shipment, or row-level records.",
            "The optimizer was not rerun; original frozen plan records and strategy names were passed to simulate unchanged.",
        ],
    }
    manifest_path = output_dir / "execution_manifest.json"
    _write_json_new(manifest_path, manifest)
    return {"output_dir": output_dir, "summary": summary_rows, "manifest": manifest}


def _load_c_graph(root: Path, input_paths: Mapping[str, Path]):
    """Use C's existing graph loader as a read-only graph-construction dependency."""
    opt_dir = str(root / "opt")
    sys.path.insert(0, opt_dir)
    try:
        import c_real_graph
        return c_real_graph.load_core_graph(
            str(input_paths["core_nodes"]), str(input_paths["core_edges"])
        )
    finally:
        if sys.path and sys.path[0] == opt_dir:
            sys.path.pop(0)

def main() -> None:
    """Validate inputs by default; --run executes the frozen 40-case integration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="run all 10 × 4 frozen plan cases through the queue simulator")
    parser.add_argument("--output-dir", default="experiments/day6/final_integration_v1")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    processed = root / "data" / "processed"
    inputs = build_demand_inputs(
        processed / "core_train_legs.csv",
        processed / "core_edges.csv",
        processed / "core_nodes.csv",
        processed / "split_trip_ids.csv",
    )
    risk = validate_risk_table(
        root / "models" / "outputs" / "risk_table.csv",
        set(inputs.demands),
    )
    preflight = {
        "input_validation": "PASS",
        "demand_reconciliation": inputs.reconciliation,
        "risk_table": {"path": "models/outputs/risk_table.csv", "rows": int(len(risk)),
                       "directed_lanes_validated": int(risk[["source_center", "destination_center"]].drop_duplicates().shape[0]),
                       "realized_test_outcomes_used": False},
        "frozen_optimizer_plan_run": bool(args.run),
        "queue_simulator_run": bool(args.run),
    }
    if args.run:
        result = run_real_integration(root, root / args.output_dir)
        preflight["integration"] = {
            "status": result["manifest"]["status"],
            "output_dir": str(result["output_dir"]),
            "successful_runs": result["manifest"]["successful_runs"],
        }
    print(json.dumps(preflight, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
