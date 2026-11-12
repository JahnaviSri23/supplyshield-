"""Unit and saved-artifact parity tests for the Person B prediction API."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from models import prediction_api as api


ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ROOT / "data" / "processed" / "preds_cal_test_master_split_v1.csv"
TEST_INTERVALS = (
    ROOT
    / "experiments"
    / "day3"
    / "master_split_v2"
    / "final"
    / "test_intervals_method_c_master_split_v2.csv"
)
PARITY_ATOL = 1e-12
INFERENCE_COLUMNS = [
    "trip_uuid",
    "source_center",
    "destination_center",
    "route_type",
    "od_start_time",
    "osrm_time_min",
    "osrm_distance_km",
    "lane_history_count",
    "base_pred",
    "pred_ratio",
    "pile",
]
ROW_KEYS = ["trip_uuid", "source_center", "destination_center", "od_start_time"]


def _requests(frame: pd.DataFrame) -> pd.DataFrame:
    request = frame.loc[:, list(ROW_KEYS) + [
        "route_type",
        "osrm_time_min",
        "osrm_distance_km",
        "lane_history_count",
        "base_pred",
    ] + (["pile"] if "pile" in frame.columns else [])].copy()
    return request.rename(columns={"base_pred": "lane_base"})


class PredictionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = api.load_model()
        cls.params = api.load_conformal_parameters()

    def test_runtime_and_model_feature_metadata(self) -> None:
        self.assertEqual(xgb.__version__, "3.2.0")
        self.assertEqual(tuple(self.model.feature_names), api.FEATURE_COLUMNS)
        self.assertEqual(tuple(self.model.feature_types), api.FEATURE_TYPES)

    def test_exact_feature_order_and_timestamp_features(self) -> None:
        row = {
            "source_center": "A",
            "destination_center": "B",
            "route_type": "FTL",
            "od_start_time": "2018-09-29 23:00:00",
            "osrm_time_min": 120.0,
            "osrm_distance_km": 80.0,
            "lane_base": 2.0,
            "lane_history_count": 0,
        }
        features = api.build_feature_matrix(row)
        self.assertEqual(tuple(features.columns), api.FEATURE_COLUMNS)
        self.assertEqual(features.loc[0, "start_hour"], 23)
        self.assertEqual(features.loc[0, "start_dow"], 5)
        self.assertEqual(features.loc[0, "is_weekend"], 1)
        self.assertEqual(features.loc[0, "is_ftl"], 1)
        self.assertAlmostEqual(features.loc[0, "osrm_speed_kmh"], 40.0)
        self.assertAlmostEqual(features.loc[0, "log_osrm_time"], np.log1p(120.0))

    def test_single_and_batch_prediction_and_zero_history_fallback(self) -> None:
        first = {
            "source_center": "UNSEEN_SOURCE",
            "destination_center": "UNSEEN_DESTINATION",
            "route_type": "Carting",
            "od_start_time": "2018-09-29 23:00:00",
            "osrm_time_min": 60.0,
            "osrm_distance_km": 40.0,
            "lane_base": 2.0,
            "lane_history_count": 0,
        }
        second = {**first, "source_center": "A", "destination_center": "B", "lane_base": 1.4, "lane_history_count": 3}
        batch = api.predict_batch([first, second], model=self.model)
        single = api.predict_single(first, model=self.model)
        self.assertEqual(len(batch), 2)
        self.assertEqual(batch.loc[0, "source_center"], "UNSEEN_SOURCE")
        self.assertEqual(batch.loc[1, "source_center"], "A")
        self.assertEqual(batch.loc[1, "destination_center"], "B")
        self.assertAlmostEqual(single["pred_ratio"], batch.loc[0, "pred_ratio"])
        self.assertAlmostEqual(
            batch.loc[0, "predicted_travel_time_min"],
            batch.loc[0, "pred_ratio"] * first["osrm_time_min"],
        )

    def test_validation_rejects_bad_inputs_and_target_leakage(self) -> None:
        valid = {
            "source_center": "A",
            "destination_center": "B",
            "route_type": "FTL",
            "od_start_time": "2018-09-29 23:00:00",
            "osrm_time_min": 120.0,
            "osrm_distance_km": 80.0,
            "lane_base": 2.0,
            "lane_history_count": 0,
        }
        cases = [
            ({k: v for k, v in valid.items() if k != "lane_base"}, "Missing required"),
            ({**valid, "source_center": "  "}, "source_center"),
            ({**valid, "route_type": "Other"}, "route_type"),
            ({**valid, "od_start_time": "not-a-date"}, "od_start_time"),
            ({**valid, "osrm_time_min": np.inf}, "finite"),
            ({**valid, "osrm_time_min": 0.0}, "greater than zero"),
            ({**valid, "osrm_distance_km": -1.0}, "greater than zero"),
            ({**valid, "lane_history_count": -1}, "non-negative integer"),
            ({**valid, "lane_history_count": 0.5}, "non-negative integer"),
            ({**valid, "lane_history_count": True}, "numeric value"),
            ({**valid, "y_ratio": 1.5}, "Target/outcome"),
            ({**valid, "lane_base": 3.0}, "must be 2.0"),
        ]
        for row, expected in cases:
            with self.subTest(row=row):
                with self.assertRaisesRegex((ValueError, TypeError), expected):
                    api.validate_prediction_rows(row)
        with self.assertRaisesRegex(ValueError, "(?i)at least one"):
            api.validate_prediction_rows([])

    def test_saved_prediction_parity_without_targets(self) -> None:
        saved = pd.read_csv(PREDICTIONS, usecols=INFERENCE_COLUMNS, parse_dates=["od_start_time"])
        request = _requests(saved)
        # The API receives only the approved fields, never y_ratio/delay_ratio.
        result = api.predict_batch(request, model=self.model)
        self.assertEqual(len(result), len(saved))
        matched = result.merge(
            saved[ROW_KEYS + ["base_pred", "pred_ratio", "pile"]],
            on=ROW_KEYS,
            how="inner",
            suffixes=("", "_saved"),
            validate="one_to_one",
        )
        self.assertEqual(len(matched), len(saved))
        self.assertTrue(np.array_equal(matched["pile"].to_numpy(), matched["pile_saved"].to_numpy()))
        point_diff = np.abs(matched["pred_ratio"].to_numpy() - matched["pred_ratio_saved"].to_numpy())
        base_diff = np.abs(matched["lane_base"].to_numpy() - matched["base_pred"].to_numpy())
        self.assertLessEqual(float(point_diff.max()), PARITY_ATOL)
        self.assertLessEqual(float(base_diff.max()), PARITY_ATOL)
        self.assertEqual(tuple(api.build_feature_matrix(request).columns), api.FEATURE_COLUMNS)

    def test_test_interval_parity_by_stable_row_keys(self) -> None:
        saved = pd.read_csv(PREDICTIONS, usecols=INFERENCE_COLUMNS, parse_dates=["od_start_time"])
        saved = saved.loc[saved["pile"].eq("test")].copy()
        result = api.predict_batch(
            _requests(saved),
            model=self.model,
            include_intervals=True,
            conformal_parameters=self.params,
        )
        expected_cols = ROW_KEYS + [
            "lower_50", "upper_50", "lower_80", "upper_80", "lower_90", "upper_90"
        ]
        expected = pd.read_csv(TEST_INTERVALS, usecols=expected_cols, parse_dates=["od_start_time"])
        merged = result.merge(expected, on=ROW_KEYS, how="inner", suffixes=("", "_saved"), validate="one_to_one")
        self.assertEqual(len(merged), len(saved))
        for name in ("lower_50", "upper_50", "lower_80", "upper_80", "lower_90", "upper_90"):
            diff = np.abs(merged[name].to_numpy() - merged[f"{name}_saved"].to_numpy())
            self.assertLessEqual(float(diff.max()), PARITY_ATOL, name)

    def test_unknown_group_uses_global_offsets(self) -> None:
        frame = pd.DataFrame({
            "route_type": ["UnseenRoute"],
            "osrm_distance_km": [10.0],
            "pred_ratio": [0.1],
        })
        bounded = api.apply_conformal_intervals(frame, self.params)
        for level in ("50%", "80%", "90%"):
            tag = level[:-1]
            lo, hi = self.params["levels"][level]["global_offsets"]
            self.assertEqual(bounded.loc[0, f"lower_{tag}"], max(0.0, 0.1 + lo))
            self.assertAlmostEqual(bounded.loc[0, f"upper_{tag}"], 0.1 + hi)

    def test_module_does_not_load_prediction_or_history_datasets(self) -> None:
        source = Path(api.__file__).read_text(encoding="utf-8")
        self.assertNotIn("read_csv", source)
        self.assertNotIn("delay_ratio", api.FEATURE_COLUMNS)
        self.assertNotIn("y_ratio", api.FEATURE_COLUMNS)


if __name__ == "__main__":
    unittest.main()
