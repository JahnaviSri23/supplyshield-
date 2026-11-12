"""Synthetic-only Prediction API and native TreeSHAP smoke demonstration.

The request fields are hypothetical. The script reads the saved model and
Method C parameters but no shipment, target, prediction-export, or lane-history
records, and it writes no files. Its outputs are software-flow examples, not
real-data evaluation or business-risk classifications.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models import prediction_api as api
from models.shap_explainability import calculate_native_contributions


def run_demo() -> None:
    """Score one synthetic request and show its interval and local attributions."""
    request = {
        "source_center": "SYNTH_ORIGIN_01",
        "destination_center": "SYNTH_DESTINATION_02",
        "route_type": "FTL",
        "od_start_time": "2030-01-15 10:30:00",
        "osrm_time_min": 120.0,
        "osrm_distance_km": 84.0,
        "lane_base": api.ZERO_HISTORY_BASE,
        "lane_history_count": 0,
    }
    model = api.load_model()
    prediction = api.predict_single(request, model=model, include_intervals=True)
    features = api.build_feature_matrix(request)
    residuals, contributions, bias, validation = calculate_native_contributions(
        features, model
    )
    if not math.isclose(
        float(residuals[0]),
        float(prediction["predicted_residual"]),
        rel_tol=0.0,
        abs_tol=validation["additivity_atol"],
    ):
        raise AssertionError("API and native contribution predictions do not align")
    contribution_sum = float(contributions.iloc[0].sum() + bias[0])
    if not math.isclose(
        contribution_sum,
        float(prediction["predicted_residual"]),
        rel_tol=0.0,
        abs_tol=validation["additivity_atol"],
    ):
        raise AssertionError("Synthetic local contributions failed additivity")

    print("SYNTHETIC REQUEST ONLY - not an observed shipment or performance result")
    print('The zero-history baseline 2.0 is the documented fit-only fallback; other request features are illustrative.')
    print(f"predicted_residual={prediction['predicted_residual']:.6f}")
    print(f"pred_ratio={prediction['pred_ratio']:.6f}")
    print('pred_ratio is relative to OSRM travel time; above 1 means a longer predicted trip, with no category assigned.')
    print(f"predicted_travel_time_min={prediction['predicted_travel_time_min']:.2f}")
    for tag in ("50", "80", "90"):
        print(
            f"{tag}% interval ratio="
            f"[{prediction[f'lower_{tag}']:.6f}, {prediction[f'upper_{tag}']:.6f}]"
        )
    print("Largest-magnitude local native contributions to residual output:")
    ranked = contributions.iloc[0].abs().sort_values(ascending=False).head(3).index
    for feature in ranked:
        print(f"  {feature}: {contributions.iloc[0][feature]:+.6f}")
    print(f"  bias: {bias[0]:+.6f}")
    print(
        "Interpretation: contributions explain the residual only; lane_base is "
        "added separately. Values are model attributions, not causal effects."
    )
    print(
        "No discrete risk category is defined by this demo. Intervals are "
        "saved split-conformal bounds, not confidence guarantees."
    )


if __name__ == "__main__":
    run_demo()