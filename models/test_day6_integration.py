"""In-memory contract tests for Person B's Day 6 validation adapter."""

import unittest
import sys
import json
from pathlib import Path
import tempfile

import networkx as nx
import pandas as pd

from models.day6_integration import (
    apply_risk_adjusted_durations,
    attach_travel_time_multipliers,
    build_demand_inputs,
    normalize_optimizer_return,
    optimizer_graph_with_authoritative_demand,
    validate_optimizer_plan,
    validate_risk_table,
    validate_frozen_plans,
)
from sim.simulator import simulate


class RiskTableValidationTests(unittest.TestCase):
    @staticmethod
    def rows():
        common = {
            "baseline_ratio": 1.0,
            "pred_ratio": 1.2,
            "lo50": 1.1,
            "hi50": 1.3,
            "lo90": 1.0,
            "hi90": 1.4,
            "pred_excess_h": 0.2,
            "pred_multiplier": 1.2,
            "mult_pred": 1.2,
            "lo50_multiplier": 1.1,
            "hi50_multiplier": 1.3,
            "lo90_multiplier": 1.0,
            "hi90_multiplier": 1.4,
            "mult_lo50": 1.1,
            "mult_hi50": 1.3,
            "mult_lo90": 1.0,
            "mult_hi90": 1.4,
        }
        return [
            {"source_center": "A", "destination_center": "B", **common},
            {"source_center": "B", "destination_center": "A", **common},
        ]

    def validate_rows(self, rows, lanes=None):
        with tempfile.TemporaryDirectory(prefix="supplyshield-risk-validation-") as temp_dir:
            path = Path(temp_dir) / "risk.csv"
            pd.DataFrame(rows).to_csv(path, index=False)
            expected = lanes if lanes is not None else {("A", "B"), ("B", "A")}
            return validate_risk_table(path, expected)

    def test_complete_directed_lane_set_is_returned_without_direction_changes(self):
        risk = self.validate_rows(self.rows())
        self.assertEqual(list(zip(risk.source_center, risk.destination_center)),
                         [("A", "B"), ("B", "A")])

    def test_missing_or_extra_directed_lane_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Risk coverage mismatch"):
            self.validate_rows(self.rows()[:1])
        with self.assertRaisesRegex(ValueError, "Risk coverage mismatch"):
            self.validate_rows(self.rows(), {("A", "B")})

    def test_duplicate_directed_lane_is_rejected(self):
        rows = self.rows()
        rows.append(dict(rows[0]))
        with self.assertRaisesRegex(ValueError, "duplicate directed lane"):
            self.validate_rows(rows)

    def test_required_multipliers_and_finite_values_are_enforced(self):
        rows = self.rows()
        for row in rows:
            del row["mult_hi90"]
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            self.validate_rows(rows)
        rows = self.rows()
        rows[0]["mult_pred"] = float("nan")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            self.validate_rows(rows)

    def test_point_multiplier_must_be_positive_and_interval_bounds_nonnegative(self):
        rows = self.rows()
        rows[0]["mult_pred"] = 0.0
        with self.assertRaisesRegex(ValueError, "mult_pred must be positive"):
            self.validate_rows(rows)
        rows = self.rows()
        rows[0]["mult_lo90"] = -0.1
        with self.assertRaisesRegex(ValueError, "interval multipliers must be nonnegative"):
            self.validate_rows(rows)

    def test_ratio_and_multiplier_intervals_must_be_nested_and_contain_the_point(self):
        rows = self.rows()
        rows[0]["hi50"] = 1.19
        with self.assertRaisesRegex(ValueError, "ratio intervals are not nested"):
            self.validate_rows(rows)
        rows = self.rows()
        rows[0]["mult_lo50"] = 1.21
        with self.assertRaisesRegex(ValueError, "multiplier intervals are not nested"):
            self.validate_rows(rows)

    def test_canonical_mult_pred_is_required(self):
        rows = self.rows()
        for row in rows:
            del row["mult_pred"]
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            self.validate_rows(rows)


class RiskAdjustedDurationTests(unittest.TestCase):
    @staticmethod
    def graph_and_risk():
        graph = nx.DiGraph()
        graph.add_node("A", cap=5.0)
        graph.add_node("B", cap=0.0)
        graph.add_edge("A", "B", cost=2.0, cap=7.0, trips=14.0)
        graph.add_edge("B", "A", cost=3.0, cap=8.0, trips=28.0)
        risk = pd.DataFrame([
            {"source_center": "A", "destination_center": "B", "mult_pred": 1.5},
            {"source_center": "B", "destination_center": "A", "mult_pred": 0.5},
        ])
        return graph, risk

    def test_formula_direction_and_capacity_preservation(self):
        graph, risk = self.graph_and_risk()
        multipliers = apply_risk_adjusted_durations(graph, risk)
        self.assertEqual(multipliers, {("A", "B"): 1.5, ("B", "A"): 0.5})
        self.assertEqual(graph.edges["A", "B"]["cost"], 2.0)
        self.assertEqual(graph.edges["B", "A"]["cost"], 3.0)
        self.assertEqual(graph.edges["A", "B"]["cap"], 7.0)
        self.assertEqual(graph.edges["B", "A"]["cap"], 8.0)
        self.assertEqual(graph.edges["A", "B"]["trips"], 14.0)
        scenario = attach_travel_time_multipliers({}, multipliers)
        self.assertEqual(scenario["travel_time_multipliers"], multipliers)

    def test_risk_adjustment_cannot_be_applied_twice(self):
        graph, risk = self.graph_and_risk()
        scenario = {"travel_time_multipliers": apply_risk_adjusted_durations(graph, risk)}
        with self.assertRaisesRegex(ValueError, "already present"):
            attach_travel_time_multipliers(scenario, apply_risk_adjusted_durations(graph, risk))

    def test_reverse_direction_is_not_interchanged(self):
        graph, risk = self.graph_and_risk()
        risk.loc[risk.source_center.eq("A"), "mult_pred"] = 2.0
        multipliers = apply_risk_adjusted_durations(graph, risk)
        self.assertEqual(multipliers[("A", "B")], 2.0)
        self.assertEqual(multipliers[("B", "A")], 0.5)


class FrozenPlanContractTests(unittest.TestCase):
    def write_plan(self, root, invalid_closed_flow=False):
        daily = 5395 / 14
        scenarios = []
        names = ["do nothing", "greedy", "preserve (affected flows only)", "LP (all flows)"]
        for i in range(1, 11):
            records = ([{"od": ["A", "B"], "edge": ["A", "B"], "flow": daily}]
                       if invalid_closed_flow else [])
            scenarios.append({
                "id": f"L{i:02d}", "closed_lanes": [["A", "B"]], "penalty": 96.0,
                "flow_unit": "legs per day", "cost_unit": "leg-hours",
                "horizon": "one steady-state day", "demand": [
                    {"od": ["A", "B"], "legs_per_day": daily}],
                "plans": {name: records if name == names[0] else [] for name in names},
                "expected": {name: {"shipping": 0.0, "unmet": daily,
                                    "total_cost": 96.0 * daily} for name in names},
            })
        path = root / "plans.json"
        path.write_text(json.dumps(scenarios), encoding="utf-8")
        return path

    def test_frozen_plan_scenario_and_strategy_contract(self):
        with tempfile.TemporaryDirectory(prefix="supplyshield-frozen-plan-") as temp:
            path = self.write_plan(Path(temp))
            result = validate_frozen_plans(path, {("A", "B"): 5395 / 14}, {("A", "B")})
        self.assertEqual(len(result), 10)
        self.assertEqual(list(result[0]["plans"]), [
            "do nothing", "greedy", "preserve (affected flows only)", "LP (all flows)"])

    def test_frozen_plan_flow_on_its_closed_lane_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="supplyshield-frozen-plan-") as temp:
            path = self.write_plan(Path(temp), invalid_closed_flow=True)
            with self.assertRaisesRegex(ValueError, "closed lane"):
                validate_frozen_plans(path, {("A", "B"): 5395 / 14}, {("A", "B")})


class AuthoritativeDemandPopulationTests(unittest.TestCase):
    def test_complete_train_cohort_not_departure_window_is_used(self):
        with tempfile.TemporaryDirectory(prefix="supplyshield-demand-") as temp_dir:
            root = Path(temp_dir)
            legs = pd.DataFrame([
                {"trip_uuid": "t1", "trip_creation_time": "2018-09-25 12:00",
                 "od_start_time": "2018-09-25 13:00", "source_center": "A",
                 "destination_center": "B"},
                {"trip_uuid": "t2", "trip_creation_time": "2018-09-25 12:00",
                 "od_start_time": "2018-09-26 00:01", "source_center": "A",
                 "destination_center": "B"},
            ])
            edges = pd.DataFrame([{"source": "A", "destination": "B", "trips": 2}])
            nodes = pd.DataFrame([{"hub": "A", "capacity_est": 2.0},
                                  {"hub": "B", "capacity_est": 0.0}])
            split = pd.DataFrame([{"trip_uuid": "t1", "split": "train"},
                                  {"trip_uuid": "t2", "split": "train"}])
            for name, frame in [("legs.csv", legs), ("edges.csv", edges),
                                ("nodes.csv", nodes), ("split.csv", split)]:
                frame.to_csv(root / name, index=False)
            result = build_demand_inputs(root / "legs.csv", root / "edges.csv",
                                         root / "nodes.csv", root / "split.csv")
        self.assertEqual(result.lane_counts[("A", "B")], 2)
        self.assertAlmostEqual(result.demands[("A", "B")], 2 / 14)
        self.assertEqual(result.reconciliation["strict_created_and_departed_window_rows_informational"], 1)
        self.assertEqual(result.reconciliation["strict_window_rows_excluded_from_authoritative_population"], 0)


class OptimizerPlanContractTests(unittest.TestCase):
    def setUp(self):
        self.lanes = {
            ("A", "B"), ("B", "D"), ("C", "B"), ("B", "E"),
            ("A", "D"), ("C", "E"),
        }
        self.capacities = {node: 10.0 for node in "ABCDE"}

    @staticmethod
    def add_required_metadata(result, demands):
        result["demands"] = demands
        result["flow_unit"] = "legs/day"
        result["objective"] = {
            "travel_leg_hours_per_day": 0.0,
            "unmet_penalty_leg_hours_per_day": 0.0,
            "total_leg_hours_per_day": 0.0,
        }
        return result

    def test_single_od_conservation(self):
        demands = {("A", "D"): 3.0}
        result = {
            "status": "optimal",
            "flows": {("A", "D"): {("A", "B"): 3.0, ("B", "D"): 3.0}},
            "unmet": {("A", "D"): 0.0},
        }
        self.add_required_metadata(result, demands)
        flows = validate_optimizer_plan(result, demands, self.lanes, self.capacities)
        self.assertEqual(flows[("A", "D")][("B", "D")], 3.0)

    def test_multi_od_attribution_and_shared_hub_capacity(self):
        demands = {("A", "D"): 3.0, ("C", "E"): 4.0}
        result = {
            "status": "optimal",
            "flows": {
                ("A", "D"): {("A", "B"): 3.0, ("B", "D"): 3.0},
                ("C", "E"): {("C", "B"): 4.0, ("B", "E"): 4.0},
            },
            "unmet": {("A", "D"): 0.0, ("C", "E"): 0.0},
        }
        self.add_required_metadata(result, demands)
        self.capacities["B"] = 7.0
        flows = validate_optimizer_plan(result, demands, self.lanes, self.capacities)
        self.assertEqual(len(flows), 2)
        self.capacities["B"] = 6.9
        with self.assertRaisesRegex(ValueError, "capacity exceeded"):
            validate_optimizer_plan(result, demands, self.lanes, self.capacities)

    def test_unserved_demand_is_explicit_and_conserved(self):
        demands = {("A", "D"): 5.0}
        result = {
            "status": "optimal",
            "flows": {("A", "D"): {("A", "B"): 3.0, ("B", "D"): 3.0}},
            "unmet": {("A", "D"): 2.0},
        }
        self.add_required_metadata(result, demands)
        validate_optimizer_plan(result, demands, self.lanes, self.capacities)

    def test_closed_lane_is_rejected(self):
        demands = {("A", "D"): 1.0}
        result = {
            "status": "optimal",
            "flows": {("A", "D"): {("A", "B"): 1.0, ("B", "D"): 1.0}},
            "unmet": {("A", "D"): 0.0},
        }
        self.add_required_metadata(result, demands)
        with self.assertRaisesRegex(ValueError, "closed lane"):
            validate_optimizer_plan(result, demands, self.lanes, self.capacities,
                                    closed_lanes={("B", "D")})

    def test_aggregate_only_optimizer_result_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "per-OD flows"):
            validate_optimizer_plan({"status": "optimal", "cost": 1.0, "unmet_total": 0.0},
                                    {("A", "D"): 1.0}, self.lanes, self.capacities)

    def test_missing_or_unknown_od_is_rejected(self):
        result = {"status": "optimal", "flows": {}, "unmet": {}}
        with self.assertRaisesRegex(ValueError, "demand"):
            validate_optimizer_plan(result, {("A", "D"): 1.0}, self.lanes, self.capacities)

    def test_explicit_demand_prepares_a_copy_using_solver_trips_convention(self):
        graph = nx.DiGraph()
        graph.add_edge("A", "B", trips=98.0)
        graph.add_edge("B", "C", trips=28.0)
        demands = {("A", "B"): 1.0, ("B", "C"): 2.0}
        prepared = optimizer_graph_with_authoritative_demand(graph, demands)
        self.assertEqual(prepared.edges["A", "B"]["trips"], 14.0)
        self.assertEqual(prepared.edges["B", "C"]["trips"], 28.0)
        self.assertEqual(graph.edges["A", "B"]["trips"], 98.0)

    def test_flat_person_c_result_normalizes_zero_served_od_and_unavailable_status(self):
        graph = nx.DiGraph()
        graph.add_nodes_from([("A", {"cap": 5}), ("B", {"cap": 0}),
                              ("C", {"cap": 5}), ("D", {"cap": 0})])
        graph.add_edge("A", "B", cost=2.0, cap=10.0)
        graph.add_edge("C", "D", cost=3.0, cap=10.0)
        demands = {("A", "B"): 1.0, ("C", "D"): 0.5}
        result = normalize_optimizer_return(
            (3.0, 0.5, [{"od": ["A", "B"], "edge": ["A", "B"], "flow": 1.0}]),
            demands, graph, penalty_value=2.0,
        )
        self.assertFalse(result["solver_status_available"])
        self.assertEqual(result["solver_status"], None)
        self.assertEqual(len(result["per_od"]), 2)
        self.assertEqual(result["served_flow_per_od"][("C", "D")], 0.0)
        self.assertEqual(result["unmet_flow_per_od"][("C", "D")], 0.5)
        checked = validate_optimizer_plan(
            result, demands, set(graph.edges),
            {node: graph.nodes[node]["cap"] for node in graph},
        )
        self.assertIn(("C", "D"), checked)


class MultiOdQueueTests(unittest.TestCase):
    @staticmethod
    def graph():
        graph = nx.DiGraph()
        for node, cap in {"A": 5.0, "B": 5.0, "X": 1.0, "H": 1.0,
                          "D": 0.0, "E": 0.0}.items():
            graph.add_node(node, cap=cap, buffer=5.0)
        for edge, cap in [(("A", "X"), 10.0), (("B", "X"), 10.0),
                          (("X", "H"), 1.0), (("H", "D"), 10.0), (("H", "E"), 10.0)]:
            graph.add_edge(*edge, cost=1.0, cap=cap)
        graph.graph["demands"] = {("A", "D"): 1.0, ("B", "E"): 1.0}
        graph.graph["waiting_cost"] = 0.0
        graph.graph["unmet_penalty"] = 96.0
        return graph

    @staticmethod
    def records():
        return [
            {"od": ["A", "D"], "edge": ["A", "X"], "flow": 1.0},
            {"od": ["A", "D"], "edge": ["X", "H"], "flow": 1.0},
            {"od": ["A", "D"], "edge": ["H", "D"], "flow": 1.0},
            {"od": ["B", "E"], "edge": ["B", "X"], "flow": 1.0},
            {"od": ["B", "E"], "edge": ["X", "H"], "flow": 1.0},
            {"od": ["B", "E"], "edge": ["H", "E"], "flow": 1.0},
        ]

    def run_plan(self, plan=None, scenario=None):
        graph = self.graph()
        config = {"demand_days": 2, "horizon": 20, "failure_start": 0,
                  "failure_days": 0, "capacity_scale": 1.0}
        config.update(scenario or {})
        return simulate(graph, config, self.records() if plan is None else plan)

    def test_multi_od_records_preserve_identity_and_share_hub_capacity(self):
        result = self.run_plan()
        self.assertEqual(result["generated"], 4.0)
        self.assertEqual(result["delivered"], 4.0)
        self.assertEqual(result["unmet"], 0.0)
        for day in result["history"]:
            self.assertAlmostEqual(
                day["generated"], day["delivered"] + day["queued"]
                + day["outside_backlog"] + day["in_transit"], places=7,
            )

    def test_repeated_run_is_deterministic(self):
        self.assertEqual(self.run_plan(), self.run_plan())

    def test_closed_lane_preserves_unaffected_route_and_reconciles_unmet(self):
        graph = self.graph()
        scenario = {"demand_days": 1, "horizon": 5, "failure_start": 0,
                    "failure_days": 1, "closed_lanes": [["A", "X"]]}
        plan = [
            {"od": ["B", "E"], "edge": ["B", "X"], "flow": 1.0},
            {"od": ["B", "E"], "edge": ["X", "H"], "flow": 1.0},
            {"od": ["B", "E"], "edge": ["H", "E"], "flow": 1.0},
        ]
        result = simulate(graph, scenario, plan)
        self.assertEqual(result["generated"], 2.0)
        self.assertEqual(result["delivered"], 1.0)
        self.assertEqual(result["unmet"], 1.0)
        self.assertEqual(result["generated"], result["delivered"] + result["unmet"])

    def test_plan_on_closed_lane_waits_then_dispatches_after_reopening(self):
        result = self.run_plan(scenario={
            "closed_lanes": [["A", "X"]], "failure_start": 0, "failure_days": 2,
        })
        self.assertEqual(result["generated"], result["delivered"] + result["unmet"])
        self.assertEqual(result["unmet"], 0.0)
        self.assertGreater(result["recovery_days"], 0)

    def test_single_od_flat_plan_compatibility(self):
        graph = nx.DiGraph()
        graph.add_node("S", cap=2.0)
        graph.add_node("T", cap=0.0)
        graph.add_edge("S", "T", cost=1.0, cap=5.0)
        graph.graph["demands"] = {("S", "T"): 1.0}
        graph.graph["unmet_penalty"] = 96.0
        result = simulate(graph, {"demand_days": 1, "horizon": 5}, {("S", "T"): 1.0})
        self.assertEqual(result["delivered"], 1.0)

    def test_failed_hub_recovers_and_zero_capacity_edge_is_unserved(self):
        graph = self.graph()
        failed = simulate(
            graph, {"demand_days": 1, "horizon": 12, "failure_start": 0,
                    "failure_days": 2, "failed": {"X": 0.0}}, self.records(),
        )
        self.assertEqual(failed["unmet"], 0.0)
        graph.edges["X", "H"]["cap"] = 0.0
        blocked = simulate(
            graph, {"demand_days": 1, "horizon": 5, "failure_days": 0}, self.records(),
        )
        self.assertEqual(blocked["generated"], blocked["delivered"] + blocked["unmet"])
        self.assertGreater(blocked["unmet"], 0.0)

    def test_negative_and_unknown_plan_edges_are_rejected(self):
        graph = self.graph()
        bad = [{"od": ["A", "D"], "edge": ["A", "X"], "flow": -1.0}]
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            simulate(graph, {"demand_days": 1, "horizon": 4}, bad)
        bad = [{"od": ["A", "D"], "edge": ["A", "Q"], "flow": 1.0}]
        with self.assertRaisesRegex(ValueError, "Unknown edge"):
            simulate(graph, {"demand_days": 1, "horizon": 4}, bad)


class PersonCOptimizerApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        opt_dir = str(Path(__file__).resolve().parents[1] / "opt")
        sys.path.insert(0, opt_dir)
        import c_multiflow
        import c_real_graph
        cls.cm = c_multiflow
        cls.rg = c_real_graph

    @classmethod
    def tearDownClass(cls):
        opt_dir = str(Path(__file__).resolve().parents[1] / "opt")
        if opt_dir in sys.path:
            sys.path.remove(opt_dir)

    def test_tuple_compatibility_and_actual_plan_export(self):
        graph = nx.DiGraph()
        graph.add_node("S", cap=10.0)
        graph.add_node("T", cap=10.0)
        graph.add_edge("S", "T", cost=2.0, cap=1e9, trips=14.0)
        legacy = self.cm.solve_multiflow(graph)
        planned = self.cm.solve_multiflow(graph, return_plan=True)
        self.assertEqual(len(legacy), 2)
        self.assertEqual(len(planned), 3)
        demands = {("S", "T"): 1.0}
        normalized = normalize_optimizer_return(
            planned, demands, graph, penalty_value=float(self.rg.PENALTY_HOURS),
        )
        self.assertFalse(normalized["solver_status_available"])
        self.assertEqual(normalized["total_requested_flow"], 1.0)
        self.assertAlmostEqual(normalized["total_served_flow"], 1.0)
        self.assertEqual(normalized["total_unmet_flow"], 0.0)

    def test_actual_multiod_optimizer_preserves_od_and_shared_capacity_unmet(self):
        graph = nx.DiGraph()
        for node, capacity in {"A": 10.0, "B": 1.0, "C": 10.0,
                               "D": 10.0, "E": 10.0}.items():
            graph.add_node(node, cap=capacity)
        graph.add_edge("A", "B", cost=1.0, cap=1e9, trips=0.0)
        graph.add_edge("B", "D", cost=1.0, cap=1e9, trips=0.0)
        graph.add_edge("C", "B", cost=1.0, cap=1e9, trips=0.0)
        graph.add_edge("B", "E", cost=1.0, cap=1e9, trips=0.0)
        graph.add_edge("A", "D", cost=100.0, cap=1e9, trips=14.0)
        graph.add_edge("C", "E", cost=100.0, cap=1e9, trips=14.0)
        demands = {("A", "B"): 0.0, ("B", "D"): 0.0, ("C", "B"): 0.0,
                   ("B", "E"): 0.0, ("A", "D"): 1.0, ("C", "E"): 1.0}
        graph = optimizer_graph_with_authoritative_demand(graph, demands)
        raw = self.cm.solve_multiflow(graph, return_plan=True)
        normalized = normalize_optimizer_return(
            raw, demands, graph, penalty_value=float(self.rg.PENALTY_HOURS),
        )
        validate_optimizer_plan(
            normalized, demands, set(graph.edges),
            {node: graph.nodes[node]["cap"] for node in graph}, tolerance=1e-4,
        )
        self.assertEqual(len(normalized["per_od"]), 6)
        self.assertAlmostEqual(normalized["total_unmet_flow"], 1.0, places=6)
        self.assertAlmostEqual(normalized["total_served_flow"], 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
