"""
Tests for SupplyShield data loader module and data file integrity.
Checks that every required data file exists, loads cleanly, and contains all expected columns.
Compatible with both pytest and python -m unittest.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd

# Add app and repo root to sys.path
_test_dir = Path(__file__).resolve().parent
_app_dir = _test_dir.parent
_repo_root = _app_dir.parent

for d in [str(_app_dir), str(_repo_root)]:
    if d not in sys.path:
        sys.path.insert(0, d)

try:
    import data
    if not hasattr(data, "load_core_nodes"):
        from app import data
except Exception:
    from app import data


class TestSupplyShieldData(unittest.TestCase):
    """Test suite verifying schema and integrity of precomputed SupplyShield datasets."""

    def test_repo_root_resolution(self):
        root = data.get_repo_root()
        self.assertTrue((root / "experiments").is_dir(), f"experiments dir not found at {root}")
        self.assertTrue((root / "data").is_dir(), f"data dir not found at {root}")

    def test_load_core_nodes(self):
        nodes_df = data.load_core_nodes()
        self.assertIsInstance(nodes_df, pd.DataFrame)
        self.assertEqual(len(nodes_df), 100, f"Expected 100 hubs, found {len(nodes_df)}")
        required_cols = ["hub", "name", "state", "lat", "lon", "capacity_est"]
        for col in required_cols:
            self.assertIn(col, nodes_df.columns, f"Missing required column '{col}' in core_nodes.csv")

    def test_load_core_edges(self):
        edges_df = data.load_core_edges()
        self.assertIsInstance(edges_df, pd.DataFrame)
        self.assertEqual(len(edges_df), 292, f"Expected 292 directed lanes, found {len(edges_df)}")
        required_cols = ["source_center", "destination_center", "leg_count", "trip_count"]
        for col in required_cols:
            self.assertIn(col, edges_df.columns, f"Missing required column '{col}' in core_edges.csv")

    def test_load_multiflow_closures(self):
        closures_df = data.load_multiflow_closures()
        self.assertIsInstance(closures_df, pd.DataFrame)
        self.assertEqual(len(closures_df), 40, f"Expected 40 closure records (10 closures x 4 plans), found {len(closures_df)}")
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
        for col in required_cols:
            self.assertIn(col, closures_df.columns, f"Missing required column '{col}' in c_multiflow_closures.csv")
        self.assertEqual(closures_df["lane"].nunique(), 10, "Expected exactly 10 distinct tested closure lanes")

    def test_load_real_lane_closures(self):
        real_df = data.load_real_lane_closures()
        self.assertIsInstance(real_df, pd.DataFrame)
        self.assertEqual(len(real_df), 30, f"Expected 30 records in c_real_lane_closures.csv, found {len(real_df)}")
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
        for col in required_cols:
            self.assertIn(col, real_df.columns, f"Missing required column '{col}' in c_real_lane_closures.csv")

    def test_load_multiflow_plans_json(self):
        plans_data = data.load_multiflow_plans()
        self.assertIsInstance(plans_data, list)
        self.assertEqual(len(plans_data), 10, f"Expected 10 scenarios in c_multiflow_plans.json, found {len(plans_data)}")
        required_keys = ["id", "closed_lanes", "penalty", "demand", "plans", "expected"]
        for idx, scenario in enumerate(plans_data):
            for k in required_keys:
                self.assertIn(k, scenario, f"Scenario {idx} missing required key '{k}'")
            plans_dict = scenario.get("plans", {})
            for plan_name in ["do nothing", "greedy", "preserve (affected flows only)", "LP (all flows)"]:
                self.assertIn(plan_name, plans_dict, f"Scenario {scenario.get('id')} missing recovery plan '{plan_name}'")

    def test_load_uncertainty_summary(self):
        summary_df = data.load_uncertainty_summary()
        self.assertIsInstance(summary_df, pd.DataFrame)
        self.assertEqual(len(summary_df), 4, f"Expected 4 uncertainty plans, found {len(summary_df)}")
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
        for col in required_cols:
            self.assertIn(col, summary_df.columns, f"Missing required column '{col}' in c_uncertainty_summary.csv")

    def test_load_uncertainty_intervals(self):
        intervals_df = data.load_uncertainty_intervals()
        self.assertIsInstance(intervals_df, pd.DataFrame)
        self.assertEqual(len(intervals_df), 4, f"Expected 4 interval rows, found {len(intervals_df)}")
        required_cols = [
            "population",
            "interval",
            "lanes",
            "test_legs",
            "coverage_of_realized",
            "mean_width",
            "share_of_samples_inside",
        ]
        for col in required_cols:
            self.assertIn(col, intervals_df.columns, f"Missing required column '{col}' in c_uncertainty_intervals.csv")

    def test_load_uncertainty_results(self):
        results_df = data.load_uncertainty_results()
        self.assertIsInstance(results_df, pd.DataFrame)
        self.assertEqual(len(results_df), 60, f"Expected 60 stochastic simulation records, found {len(results_df)}")
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
        for col in required_cols:
            self.assertIn(col, results_df.columns, f"Missing required column '{col}' in c_uncertainty_results.csv")

    def test_overview_metrics(self):
        num_hubs, num_lanes, num_closures = data.get_overview_metrics()
        self.assertEqual(num_hubs, 100)
        self.assertEqual(num_lanes, 292)
        self.assertEqual(num_closures, 10)

    def test_overview_summary_table(self):
        agg = data.get_overview_summary_table()
        self.assertEqual(len(agg), 4)
        expected_plans = ["do nothing", "greedy", "preserve (affected flows only)", "LP (all flows)"]
        self.assertListEqual(agg["plan"].tolist(), expected_plans)
        for col in ["total_cost", "extra_vs_best_normal", "unmet", "lp_seconds"]:
            self.assertIn(col, agg.columns)

    def test_hub_coordinates_generator(self):
        coords, is_approx = data.get_hub_coordinates()
        self.assertEqual(len(coords), 100, "Expected coordinates for all 100 hubs")
        self.assertEqual(len(is_approx), 100)
        self.assertEqual(sum(not v for v in is_approx.values()), 95, "Expected 95 known hubs")
        self.assertEqual(sum(is_approx.values()), 5, "Expected 5 approximate hubs")


if __name__ == "__main__":
    unittest.main()

