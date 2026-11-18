# SupplyShield native TreeSHAP explainability

## Purpose

This analysis describes how the frozen B02 XGBoost model produces its
**residual prediction**. The deployed point prediction is
`pred_ratio = lane_base + predicted_residual`; the lane baseline is added
outside the Booster, so these attributions do not explain the complete
`pred_ratio`.

SHAP values allocate a model prediction among the model's input features under
the TreeSHAP attribution method. They describe model behavior for the selected
rows; they do not show that a feature causes delays.

## Why native XGBoost TreeSHAP is used

The frozen model is `models/residual_xgb_plain_master_split_v1.json`. With
XGBoost 3.2.0, the model's vector-valued `base_score` is serialized in a form
that SHAP 0.49.1 `TreeExplainer` cannot parse. For this reason the analysis
does not call `shap.TreeExplainer`. It calculates the feature attributions
using XGBoost's native
`Booster.predict(dmatrix, pred_contribs=True)` implementation. SHAP is used
only to create an `Explanation` presentation object and, when compatible, to
render the beeswarm plot. Attribution values are never recalculated by SHAP.

The Booster has a saved `best_iteration` attribute. The Prediction API uses
`iteration_range=(0, best_iteration + 1)`; this analysis applies that same
range to both ordinary residual prediction and native contributions. Using
all stored rounds would explain a different prediction: this model stores more
rounds than its best iteration.

## Model feature contract

The feature matrix comes from `models/prediction_api.py` through
`build_feature_matrix()`. Its verified feature order is:

1. `osrm_time_min`
2. `osrm_distance_km`
3. `osrm_speed_kmh`
4. `log_osrm_time`
5. `start_hour`
6. `start_dow`
7. `is_weekend`
8. `is_ftl`
9. `lane_base`
10. `lane_history_count`

The output contribution matrix has ten feature columns and one final bias
column. The feature columns are assigned the exact model names and order; the
bias is stored separately. For each row, the ten contributions plus the bias
must reconstruct the raw residual prediction within absolute tolerance
`1e-6` and relative tolerance zero.

## Population and leakage safeguards

The explanation population is every eligible held-out test leg in
`data/processed/preds_cal_test_master_split_v1.csv`, joined by `trip_uuid` to
the authoritative `data/processed/split_trip_ids.csv`. The master split
selects the test population; the export's `pile` value is checked against it
(`cal` is normalized to `calibration`). No resampling is performed.

The prediction export is read using an explicit inference-only allowlist:
trip and lane identifiers, route type, departure timestamp, OSRM time and
distance, lane history count, lane baseline, and partition label. Target and
actual-outcome columns, including `y_ratio`, are not read. No test target is
used to construct a feature, prediction, explanation, or background dataset.

B02 constructs lane history from its chronological fit subset, selected as the
first 80% of master-train trips ordered by trip creation time. This workflow
uses the existing B02-exported baseline and history count rather than
reconstructing them. A metadata-only check verifies that the latest fit-leg
`od_end_time` is no later than the earliest test departure. The check reads
trip and timestamp fields only, not target values. No test-row labels are used.
The beeswarm colors use the test rows' actual model feature values; no
calibration or test outcomes form a reference background.

Each test row receives a deterministic, non-identifying sequential ID after
sorting stable row keys. Raw trip UUIDs are not included in generated result
tables or plot labels.

## Global importance

For each of the ten features, the ranked table reports:

- mean absolute contribution, `mean(abs(SHAP))`;
- mean signed contribution;
- sample standard deviation of contributions (`ddof=1`);
- median absolute contribution; and
- rank by mean absolute contribution, with model feature order as the stable
  tie-breaker.

Mean absolute contribution measures average attribution magnitude on this
held-out population. It is not causal importance. The bias contribution is
excluded from the ranking.

### Verified run: `experiments/day5/shap_native_v2/`

The run explained all **4,394 test legs across 2,424 trips** with no sampling.
The contribution matrix was `(4394, 11)`, all values were finite, and the
maximum absolute additivity error was `5.270703695714474e-07` (absolute
tolerance `1e-6`, relative tolerance zero). It used the API's best iteration
134 of 235 stored rounds. `shap.plots.beeswarm` accepted the native
`shap.Explanation` object.

The top three features by mean absolute native contribution were `lane_base`
(`0.12030077`), `start_hour` (`0.064427862`), and `osrm_speed_kmh`
(`0.041298145`). These are descriptive attribution magnitudes for this test
population, not causal findings.

## Automated test verification

The complete existing Person B SHAP test module was run on **2026-11-12**:

```powershell
.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v
```

Result: **9 passed, 0 failed** (`Ran 9 tests in 8.628s`, `OK`). The tests cover model/schema loading, target exclusion, authoritative test-split selection, temporal fit-history checks, finite/aligned/additive native contributions, global importance, deterministic local-row selection, SHAP presentation/beeswarm rendering, and refusal to overwrite existing output. No code or test fixes were needed.

Environment: Python `3.10.8`, SHAP `0.49.1`, XGBoost `3.2.0`, NumPy `2.2.6`, pandas `2.3.3`, and Matplotlib `3.10.9` from the existing repository `.venv`. The suite uses a 16-row inference sample for contribution tests and temporary-directory output tests; the separate saved v2 experiment remains the evidence for the full 4,394-row contribution run.

The metadata-only history check found 7,975 chronological fit trips and
14,073 fit legs; the latest fit `od_end_time` was `2018-09-25 16:21:16.077674`,
before the earliest test departure at `2018-09-29 20:41:18.098697`. No target
values were read by that check.

## Plots and interpretation

- **Global bar chart:** ranks features by mean absolute native contribution.
  Values are in residual-ratio units.
- **Beeswarm:** displays row-level contribution distributions, with feature
  values used for color. It uses `shap.plots.beeswarm` on a `shap.Explanation`
  constructed directly from native values if that works; otherwise an
  equivalent Matplotlib implementation colors by within-feature value
  percentile. Neither plot computes SHAP values.
- **Local waterfall charts:** use deterministic held-out rows nearest the
  p10, p50, and p90 predicted-residual quantiles. They show the bias separately
  from the ten feature contributions and check that their sum reconstructs
  the residual prediction. Row selection uses predictions only, not actual
  outcomes.

Positive and negative contribution bars indicate movement in the model's
residual output for that row relative to the bias contribution. These are
model attributions, not evidence of causal effects or guaranteed delay
reduction/increase.

## Reproduction

Run tests with the repository environment:

```powershell
.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v
```

Run the complete analysis:

```powershell
.\.venv\Scripts\python.exe -m models.shap_explainability --output-dir experiments/day5/shap_native_v2
```

The `shap_native_v2` directory contains the verified run described above, so
use a new version such as `shap_native_v3` for a fresh reproduction. The output
directory must not already exist. The pipeline refuses to overwrite an
existing run; select a new versioned directory for another run. The run
manifest records input/model hashes, package versions, population, feature
schema, prediction iteration range, additivity validation, plot path, and
local row selection. The validation report records the calculated findings.

## Limitations

- Explanations are specific to this saved residual Booster, its feature
  construction, best iteration, and held-out test population.
- They explain residual predictions only; `lane_base` is added separately.
- Attribution is not causation and does not establish that a feature causes
  transport delays.
- A global rank summarizes this test population and should not be interpreted
  as a universal ranking for future lanes or periods.
- Local examples are representative prediction quantiles, not selected
  examples of actual delay outcomes.
- No TreeExplainer, retraining, recalibration, or target-based feature
  construction is performed.

## Sharing and artifact status

The full test-row contribution exports and local explanations under `experiments/day5/shap_native_v1/` and `shap_native_v2/` are not part of this prepared source bundle. Keep per-leg contribution rows `INTERNAL_ONLY`; local explanations and beeswarm/local plots require owner approval before sharing. Aggregate feature-importance summaries and validation reports are demo candidates only after ordinary data/model-owner approval. Sequential explanation IDs do not make row-level records safe to release.

## Local experiment availability

The full-run files described above are retained as local experiment evidence in the original working checkout; `experiments/day5/shap_native_v2/` is not included in this isolated source-only package. The 4,394-row result is a recorded run result, not a run reproduced during the current work. The unit tests use a small sample and do not substitute for that full-population run.
The fresh isolated-worktree test rerun used the existing interpreter at 'C:\Local\Documents-Local\ML Project\supplyshield--1\.venv\Scripts\python.exe' (working directory: isolated cleanup worktree, which has no local .venv) with -m unittest models.test_shap_explainability -v; 9 tests passed and none failed. For a normal checkout with .venv at its root, the portable command above remains appropriate.