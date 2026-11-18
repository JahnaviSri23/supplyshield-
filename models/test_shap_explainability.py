"""Tests for Person B's native TreeSHAP explainability workflow."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
import xgboost as xgb

from models import prediction_api as api
from models import shap_explainability as explain


class NativeTreeShapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = explain.load_model()
        cls.requests = explain.load_test_population().head(16).reset_index(drop=True)
        cls.features = explain.build_test_features(cls.requests)

    def test_model_loads_with_exact_ten_feature_schema(self) -> None:
        self.assertEqual(xgb.__version__, "3.2.0")
        self.assertEqual(tuple(self.model.feature_names), api.FEATURE_COLUMNS)
        self.assertEqual(tuple(self.model.feature_types), api.FEATURE_TYPES)
        self.assertEqual(self.model.num_features(), 10)

    def test_inference_allowlist_and_features_exclude_targets(self) -> None:
        self.assertTrue(set(api.REQUIRED_INPUTS).issubset(self.requests.columns))
        self.assertFalse(set(self.requests.columns).intersection(explain.TARGET_COLUMNS))
        self.assertEqual(tuple(self.features.columns), api.FEATURE_COLUMNS)
        self.assertFalse(set(self.features.columns).intersection(explain.TARGET_COLUMNS))
        self.assertEqual(len(self.features), 16)

    def test_authoritative_split_is_used_for_test_population(self) -> None:
        requests = explain.load_test_population()
        self.assertEqual(len(requests), explain.EXPECTED_PREDICTION_ROWS)
        self.assertEqual(requests.attrs["test_trip_count"], explain.EXPECTED_TEST_TRIPS)
        self.assertEqual(requests["explanation_id"].nunique(), len(requests))

    def test_fit_history_precedes_test_without_reading_targets(self) -> None:
        check = explain.verify_fit_history_precedes_test()
        self.assertTrue(check["all_fit_outcomes_precede_all_test_departures"])
        self.assertEqual(check["fit_outcomes_after_first_test_departure"], 0)
        self.assertFalse(check["targets_read"])

    def test_native_contributions_are_finite_aligned_and_additive(self) -> None:
        residuals, contributions, bias, metadata = explain.calculate_native_contributions(
            self.features, self.model
        )
        self.assertEqual(contributions.shape, (16, 10))
        self.assertEqual(tuple(contributions.columns), api.FEATURE_COLUMNS)
        self.assertEqual(bias.shape, (16,))
        self.assertEqual(tuple(metadata["contribution_shape"]), (16, 11))
        self.assertTrue(np.isfinite(contributions.to_numpy()).all())
        self.assertTrue(np.isfinite(bias).all())
        self.assertTrue(np.isfinite(residuals).all())
        expected = api.predict_residuals(self.features, self.model)
        self.assertTrue(np.array_equal(residuals, expected))
        self.assertTrue(
            np.allclose(
                contributions.sum(axis=1).to_numpy() + bias,
                residuals,
                rtol=0.0,
                atol=explain.ADDITIVITY_ATOL,
            )
        )
        self.assertEqual(metadata["iteration_range"], [0, int(self.model.attributes()["best_iteration"]) + 1])

    def test_global_importance_calculations(self) -> None:
        sample = pd.DataFrame(
            {
                name: np.array([1.0, -1.0, 2.0, -2.0]) * (index + 1)
                for index, name in enumerate(api.FEATURE_COLUMNS)
            }
        )
        ranked = explain.global_importance(sample)
        self.assertEqual(list(ranked.columns), [
            "rank", "feature", "mean_abs_shap", "mean_signed_shap", "std_shap", "median_abs_shap"
        ])
        self.assertEqual(ranked.iloc[0]["feature"], api.FEATURE_COLUMNS[-1])
        self.assertAlmostEqual(ranked.iloc[0]["mean_abs_shap"], 1.5 * len(api.FEATURE_COLUMNS))
        self.assertEqual(ranked["rank"].tolist(), list(range(1, 11)))

    def test_local_selection_is_deterministic_and_spans_residual_quantiles(self) -> None:
        values = np.linspace(-0.3, 0.4, 20)
        ids = pd.Series([f"row_{i:02d}" for i in range(len(values))])
        first = explain.select_local_examples(ids, values)
        second = explain.select_local_examples(ids, values)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(first["quantile_target"].tolist(), ["p10", "p50", "p90"])
        self.assertEqual(first["explanation_id"].nunique(), 3)
        self.assertEqual(first["predicted_residual"].nunique(), 3)

    def test_shap_explanation_object_and_beeswarm_or_fallback(self) -> None:
        residuals, contributions, bias, _ = explain.calculate_native_contributions(
            self.features, self.model
        )
        explanation = explain.make_shap_explanation(self.features, contributions, bias)
        self.assertEqual(tuple(explanation.values.shape), (16, 10))
        self.assertEqual(tuple(explanation.base_values.shape), (16,))
        self.assertEqual(list(explanation.feature_names), list(api.FEATURE_COLUMNS))
        importance = explain.global_importance(contributions)
        with tempfile.TemporaryDirectory() as temp_dir:
            plot_path = Path(temp_dir) / "beeswarm.png"
            result = explain.render_beeswarm(
                self.features, contributions, bias, plot_path, importance
            )
            self.assertIn(result["method"], {"shap.plots.beeswarm", "matplotlib_fallback"})
            self.assertTrue(plot_path.is_file())
        self.assertEqual(len(residuals), 16)

    def test_output_destination_refuses_existing_content_and_writer_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            absent = root / "new_run"
            explain._assert_output_paths_available(absent)
            created = root / "new_artifact.txt"
            explain._write_text_new(created, "first version")
            self.assertEqual(created.read_text(encoding="utf-8"), "first version")
            with self.assertRaises(FileExistsError):
                explain._write_text_new(created, "second version")
            self.assertEqual(created.read_text(encoding="utf-8"), "first version")
            existing = root / "existing_run"
            existing.mkdir()
            protected = existing / "feature_importance.csv"
            protected.write_text("preserve this", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                explain._assert_output_paths_available(existing)
            with self.assertRaises(FileExistsError):
                explain._write_text_new(protected, "replacement")
            self.assertEqual(protected.read_text(encoding="utf-8"), "preserve this")


if __name__ == "__main__":
    unittest.main()
