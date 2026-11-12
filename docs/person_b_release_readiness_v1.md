# Person B Handoff Cleanup and Data-Release Readiness — Version 1

**Review date:** 2026-11-12
**Scope:** Person B documentation and sharing-risk review of existing prediction, calibration, evaluation, risk-table, and explainability artifacts. No artifact contents were printed at row level. This report is not a data-release approval.

## 1. Documentation corrections made

The following clarifications were added to active handoffs or technical documentation. Earlier snapshot claims and experiment records were retained rather than rewritten.

| Path | Correction |
|---|---|
| `docs/person_b_remaining_work_audit_v1.md` | Added a dated status update recording Prediction API 8/8, native TreeSHAP results and residual-only interpretation, the B05 cell 15/21 review, and the current Day 6 blockers. The original audit snapshot remains intact. |
| `docs/person_b_day1_day5_handoff.md` | Added a current-status note correcting the obsolete “no SHAP” implication, recording API verification, distinguishing the 5,395-leg demand from the informational 5,357 window count, and clarifying that adapter preparation is not end-to-end integration. |
| `docs/person_b_independent_work_handoff.md` | Added a superseding note for its earlier “SHAP/API unavailable” assessment and clarified current Day 6 status. The point-in-time assessment remains intact. |
| `docs/day6_integration_handoff.md` | Added a historical-run notice: the earlier 5,357-leg one-day-hop run is not current end-to-end verification. Its detailed historical results remain unchanged. |
| `docs/day6_integration_contract_v1.md` | Clarified that its 5,357 windowed-demand entry is an earlier proposal; the approved demand is 5,395 master-train core legs divided by 14 days. |
| `docs/day6_contract_reconciliation_v1.md` | Clarified that the existing adapter's `edge_durations` gate is not the final A interface and must later align to `scenario["travel_time_multipliers"]`. |
| `docs/day6_end_to_end_handoff_v1.md` | Clarified that the completed adapter preparation/tests are not a production integration and that the B adapter still needs alignment to A's interface. |
| `docs/prediction_api.md` | Added the recorded test checkpoint: `8 passed, 0 failed` using the repository `.venv` command. |

`docs/shap_explainability.md` already describes the native XGBoost method, SHAP 0.49.1 compatibility issue, 4,394 × 11 matrix, approximately `5.27e-7` additivity error, and residual-only interpretation, so it was not changed.

## 2. Historical statements preserved

- Earlier handoffs saying SHAP was unavailable or that a Prediction API did not exist are preserved as point-in-time findings. The added notes mark them as superseded by later implementation and verification.
- The older Day 6 integration report and experiment still describe a 5,357-leg, one-day-hop local run. Those results were not edited; they are explicitly historical and do not establish completion under the current contract.
- The draft contract's 5,357-row windowed population remains visible as a prior proposal, now labeled as superseded. The 5,357 count itself remains informational, not the approved demand.
- Historical B02/B03/Day 5 experiment results and manifests were not changed. Saved SHAP results remain distinct from whether its unit test suite has been run.

## 3. Data-release inventory

Classification meanings: `AGGREGATE_DEMO_CANDIDATE` means lower-risk aggregate material that may be considered for a demo after ordinary project approval; `INTERNAL_ONLY` means do not include in public materials; `REQUIRES_OWNER_APPROVAL` means obtain the relevant data/model owner’s explicit release decision; `HISTORICAL_REFERENCE` means retain as evidence, not as a current public input. No category here grants publication approval.

### Prediction and target-bearing tables

| Artifact | Format / grain / rows and columns | Disclosure considerations | Classification |
|---|---|---|---|
| `data/processed/preds_cal_test_master_split_v1.csv` | CSV, trip/leg-level, 8,695 rows. `trip_uuid`, source/destination centers, route type, departure time, OSRM time/distance, history count, `y_ratio`, `base_pred`, `pred_ratio`, `pile`. | Direct trip identifier, precise time and lane, observed target, baseline and model prediction. Could expose shipment activity even if names are absent. | `INTERNAL_ONLY` |
| `data/processed/preds_test_master_split_v1.csv` | CSV, test leg-level, 4,394 rows; same 12-column schema as above. Currently untracked. | Test identifiers, lane/time, actual target and prediction. Untracked does not mean approved or published. | `INTERNAL_ONLY` |
| `data/processed/preds_cal_test_v1.csv` | CSV, trip/leg-level, 10,748 rows; same 12-column schema as above. | Older split/export with trip identifiers, targets and predictions. | `HISTORICAL_REFERENCE` |
| `data/processed/preds_test.csv` | CSV, trip/leg-level, 5,307 rows; same 12-column schema as the master prediction export. | Legacy test partition; trip IDs, lane/time, target and predictions. | `HISTORICAL_REFERENCE` |
| `data/processed/preds_test_intervals_v1.csv` | CSV, trip/leg-level, 5,307 rows; 26 columns: the legacy prediction schema plus residual, 50/80/90 interval endpoints, excess-minute endpoints and predicted excess. | Contains trip IDs, lanes, departure times, actual target, point predictions and interval values. | `HISTORICAL_REFERENCE` |
| `data/processed/preds_test_intervals_v2.csv` | CSV, trip/leg-level, 5,307 rows; 27 columns, adding `grp` to the v1 interval schema. | Same row-level disclosure concerns as v1, plus group labels. | `HISTORICAL_REFERENCE` |
| `experiments/day3/master_split_v2/final/test_intervals_method_c_master_split_v2.csv` | CSV, test leg-level, 4,394 rows, 25 columns: trip/lane/route/time and OSRM fields, history count, partition, prediction, ratio and excess-minute interval endpoints, distance bucket and group. | Direct trip identifier, precise lane/time, model predictions and interval bounds. No target column in this file, but row linkage and operational detail remain sensitive. | `INTERNAL_ONLY` |
| `data/processed/legs.csv` and `data/processed/core_train_legs.csv` | CSV source populations, 26,369 and 5,395 leg rows respectively; contain trip IDs, directed lanes, timestamps, actual time, OSRM fields and `delay_ratio`. | Shipment/leg-level operational records and observed outcomes. | `INTERNAL_ONLY` |
| `data/processed/split_trip_ids.csv` | CSV, trip-level partition table, 14,817 rows; trip UUID, creation time and split label. | Direct trip IDs and dates disclose cohort membership and activity. | `INTERNAL_ONLY` |

### Conformal calibration and evaluation outputs

| Artifact | Format / grain / rows and columns | Disclosure considerations | Classification |
|---|---|---|---|
| `experiments/day3/master_split_v2/final/conformal_params_method_c_master_split_v2.json` | JSON calibration parameters, grouped offsets and counts; not row-level shipments. | Reveals fitted calibration parameters and group structure, but no trip identifiers. Model/provenance release should still be reviewed. | `REQUIRES_OWNER_APPROVAL` |
| `experiments/day3/master_split_v2/final/interval_comparison_master_split_v2.csv` | CSV aggregate, 12 rows; method, level, target, coverage, width, score and offsets. | Aggregate coverage and width summaries. | `AGGREGATE_DEMO_CANDIDATE` |
| `experiments/day3/master_split_v2/evaluation/method_c_trip_bootstrap_coverage_ci.csv` | CSV aggregate, 3 rows; level, target, coverage and trip-bootstrap bounds. | Aggregate uncertainty summary; no trip or lane rows. | `AGGREGATE_DEMO_CANDIDATE` |
| `experiments/day3/master_split_v2/evaluation/interval_comparison_all_methods.csv` | CSV aggregate, 12 rows; same comparison schema as final comparison. | Aggregate, but includes exploratory methods and offsets. | `HISTORICAL_REFERENCE` |
| `experiments/day3/master_split_v2/evaluation/method_b_trip_bootstrap_coverage_ci.csv` | CSV aggregate, 3 rows; level, target, coverage and bootstrap bounds. | Aggregate method comparison. | `HISTORICAL_REFERENCE` |
| `experiments/day3/master_split_v2/evaluation/method_c_90pct_slice_diagnostics.csv` | CSV group-level aggregate, 19 rows; slice/group, count, coverage and mean width. | Small or operationally meaningful groups may be inferable from granular metrics. | `REQUIRES_OWNER_APPROVAL` |
| `experiments/day3/master_split_v2/calibration/chronological_calibration_check.csv` | CSV aggregate, 3 rows; level, target and method coverage fields. | Aggregate calibration diagnostic. | `AGGREGATE_DEMO_CANDIDATE` |
| `experiments/day3/master_split_v2/run_manifest.json` and `_SUCCESS.json` | JSON run metadata, input/output paths, hashes, counts and status. | No row records, but exposes internal paths, hashes and run lineage. | `REQUIRES_OWNER_APPROVAL` |
| `experiments/day3/master_split_v2/figures/calibration_residuals.png`, `conformal_reliability_method_b.png`, `conformal_reliability_method_c.png` | Aggregate diagnostic figures. | No row identifiers are indicated by the artifact names; image contents were not visually inspected in this review. | `REQUIRES_OWNER_APPROVAL` |

### Day 2 model and evaluation

| Artifact | Format / grain | Disclosure considerations | Classification |
|---|---|---|---|
| `models/residual_xgb_plain_master_split_v1.json` | Trained XGBoost model artifact. | No raw row table, but encodes learned model and may be a controlled project artifact. | `REQUIRES_OWNER_APPROVAL` |
| `experiments/day2/master_split/final_model_card_master_split_v1.json` and `final_eval_master_split_v1.json` | JSON aggregate model card/evaluation. | Aggregate metrics and model configuration, no trip-level rows. | `AGGREGATE_DEMO_CANDIDATE` |
| `experiments/day2/master_split/v0_results_v2.json`, `v1_results_v1.json`, `v4_random_forest_results_v1.json`, `v5_extra_trees_results_v1.json` | JSON aggregate comparison outputs. | No row-level data; older model-selection evidence rather than final result. | `HISTORICAL_REFERENCE` |

### Day 5 lane-risk and SHAP outputs

| Artifact | Format / grain / rows and columns | Disclosure considerations | Classification |
|---|---|---|---|
| `experiments/day5/risk_table_master_split_v1.csv` | CSV representative lane-route rows, 296 × 36. Includes directed lane, route, prediction cutoff, feature/context counts, model features, predictions, interval endpoints and derived times. | No trip UUID column, but lane, route, timestamp and operational predictions can reveal route-level behavior. | `REQUIRES_OWNER_APPROVAL` |
| `models/outputs/risk_table.csv` | CSV lane-level, 292 × 25. Directed lane, baselines, point prediction, interval endpoints, multipliers and excess hours. | No trip IDs; exact origin-destination lane and operational risk estimates remain sensitive. | `REQUIRES_OWNER_APPROVAL` |
| `models/outputs/risk_table_lane.csv` | CSV lane-level, 292 × 10. Directed lane, lane baseline/source, history count and point/interval multipliers. | Exact lanes and model-derived operational multipliers. | `REQUIRES_OWNER_APPROVAL` |
| `models/outputs/realized_test_lane.csv` | CSV lane-level, 93 × 5. Directed lane, test-leg count, realized mean ratio and multiplier. | Actual held-out outcomes aggregated by lane; it is not merely prediction output. | `REQUIRES_OWNER_APPROVAL` |
| `models/outputs/realized_test_lane_master_split_v2.csv` | CSV lane-level, 292 × 8. Directed lane, test counts, realized mean, test-time range and multiplier. | Actual outcomes and precise per-lane time range, including low/zero-count lanes. | `REQUIRES_OWNER_APPROVAL` |
| `models/outputs/day5_lane_test_metrics_master_split_v1.csv` | CSV lane-level evaluation, 1,547 rows × 11; directed lane, test counts/trips, model/baseline errors, coverage and interval width. | Fine-grained held-out performance can reveal lane behavior; sparse rows can be especially disclosive. | `REQUIRES_OWNER_APPROVAL` |
| `models/outputs/day5_test_interval_coverage_master_split_v1.csv` | CSV aggregate, 2 rows × 10; level, nominal/empirical coverage, total legs, widths and calibration population counts. | Aggregate evaluation summary without lane/trip identifiers. | `AGGREGATE_DEMO_CANDIDATE` |
| `models/outputs/day5_model_vs_baseline_master_split_v1.json` | JSON aggregate model-versus-baseline evaluation. | Aggregate metrics without per-lane rows. | `AGGREGATE_DEMO_CANDIDATE` |
| `models/outputs/day5_final_manifest_master_split_v1.json`, `experiments/day5/risk_table_master_split_v1_manifest.json`, and `risk_table_master_split_v1_SUCCESS.json` | JSON provenance, artifact hashes, schemas/counts, model/calibration lineage and status. | No row records; may expose internal paths and model provenance. | `REQUIRES_OWNER_APPROVAL` |
| `experiments/day5/shap_native_v1/feature_importance.csv` and `shap_native_v2/feature_importance.csv` | CSV, each 10 × 6; feature rank and aggregate attribution statistics. | Aggregate feature-level summary, not row-level records. | `AGGREGATE_DEMO_CANDIDATE` |
| `experiments/day5/shap_native_v1/global_importance_bar.png` and `shap_native_v2/global_importance_bar.png` | Aggregate feature-importance figures. | Global summary, no row identifiers. | `AGGREGATE_DEMO_CANDIDATE` |
| `experiments/day5/shap_native_v1/validation_report.md` and `shap_native_v2/validation_report.md` | Aggregate run reports with validation, population counts and feature summaries. | No row records, but includes internal provenance and model results. | `AGGREGATE_DEMO_CANDIDATE` |
| `experiments/day5/shap_native_v1/test_row_contributions.csv` and `shap_native_v2/test_row_contributions.csv` | CSV, each 4,394 × 15; sequential explanation ID, ten contributions, bias, residual prediction, contribution sum and error. | One record per test leg. Sequential IDs do not eliminate linkage/disclosure risk. | `INTERNAL_ONLY` |
| `experiments/day5/shap_native_v1/local_explanations.csv` and `shap_native_v2/local_explanations.csv` | CSV, each 3 × 26; selected feature values, contributions, residual and reconstruction fields. | Small set of individual test-row explanations; no UUID, but features/predictions may identify activity. | `REQUIRES_OWNER_APPROVAL` |
| `experiments/day5/shap_native_v1/test_beeswarm.png` and `shap_native_v2/test_beeswarm.png` | Figure of row-level contribution distributions. | Each point represents a test row and is colored by feature values; aggregate appearance does not guarantee non-disclosure. | `REQUIRES_OWNER_APPROVAL` |
| `experiments/day5/shap_native_v1/local_test_01.png`–`local_test_03.png` and `shap_native_v2/local_test_01.png`–`local_test_03.png` | Three local explanation figures per run. | Selected row-level predictions/features; no trip IDs visible in labels, but still potentially linkable. | `REQUIRES_OWNER_APPROVAL` |
| `experiments/day5/shap_native_v1/run_manifest.json` and `shap_native_v2/run_manifest.json` | JSON hashes, package versions, model/input lineage, population and validation metadata. | No row records, but exposes internal lineage and paths. | `REQUIRES_OWNER_APPROVAL` |

### Upstream lane/network context

| Artifact | Format / grain | Disclosure considerations | Classification |
|---|---|---|---|
| `data/processed/core_edges.csv` | CSV, 292 directed lanes; lane counts, distance, median actual time/ratio and other network statistics. | Origin/destination centers and operational lane statistics; no direct trip UUIDs. | `REQUIRES_OWNER_APPROVAL` |

## 4. Recommended aggregate-only demo materials

Use a presentation assembled from aggregate materials only, subject to the data owner’s release approval:

- B02 final model card/evaluation summaries, without row-level prediction exports.
- B03 final 50/80/90 aggregate coverage and width summaries; state that these are held-out leg-level results and that 90% observed coverage was below nominal. Do not imply lane-level or online coverage.
- B05 global feature-importance table/bar chart and the aggregate SHAP validation report. Attribute the residual model output, not the final delay ratio; avoid the beeswarm and local examples unless explicitly approved.
- Aggregate Day 5 model-versus-baseline and test interval coverage summaries. Avoid per-lane metrics and realized outcomes in public material without owner approval.
- A synthetic, non-production illustration if a visual example is needed. Do not derive it from hidden or substituted shipment records.

Prefer a purpose-built aggregate slide/table over distributing source CSVs. No new aggregate artifact was generated in this review. Subsequent Person B demo preparation added `models/person_b_demo.py`, a synthetic-only B04 illustration that reads no production records and writes no artifacts. It is prepared and locally checked, not an approval for public release or an interactive demo.

## 5. Internal and approval-gated artifacts

- Keep all trip-level rows, targets, predictions, intervals, times, trip identifiers and SHAP per-row contribution tables internal unless an authorized data-release owner approves them.
- Obtain owner approval before sharing lane-specific risk tables, realized outcomes, per-lane metrics, route-level representative rows, local SHAP examples, beeswarm distributions, model weights, conformal parameter files, detailed manifests, or network/capacity tables.
- Treat anonymized or sequential row IDs as pseudonyms, not proof of safe release.
- Legacy prediction and interval CSVs remain historical references. Their older version or partition does not make them safer to share.
- This review did not inspect row values or search for individual personal identifiers. Classification is based on schema, row grain and provenance; it is not a legal/privacy determination.

## 6. Remaining Person B work

- Keep B05 cell 15 unresolved until its intended analysis grain/features and safe timing provenance are specified. It is not a validated result and is separate from final risk-table generation.
- **SHAP unit-test suite verified:** on 2026-11-12, `.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v` passed **9/9** in Python 3.10.8 with SHAP 0.49.1, XGBoost 3.2.0, NumPy 2.2.6, pandas 2.3.3 and Matplotlib 3.10.9. No code/test fixes were needed. This suite result is separate from the saved full-population experiment result.
- Complete a data-release decision for approval-gated lane-level and model artifacts before any public sharing.
- Preserve the current Prediction API verification record (8/8) and existing output hashes; no API changes are required by this report.

## 7. Person A and Person C dependencies

- **Person A:** deliver and test the final duration-aware simulator using `scenario["travel_time_multipliers"]`; Person B must then reconcile only the B-owned adapter/tests to that actual interface and verify exactly-once multiplier application through the real simulator.
- **Person C:** provide the frozen plan artifact at its approved path/hash and confirm its wrapper, demand, objective, penalty and flow semantics. The expected local artifact `experiments/c_multiflow_plans.json` was absent at this review.
- Until those dependencies are satisfied, Day 6 preparation is not end-to-end verification and must not be presented as such.

## 8. Current completion status

Person B's saved B01–B05 model, conformal, risk and native TreeSHAP deliverables exist locally; the Prediction API suite has 8/8 passing, the SHAP unit suite has 9/9 passing, and the saved native TreeSHAP run meets its additivity check for residual predictions. B05 cell 15 remains unresolved. The current Day 6 demand is 5,395 master-train core legs / 14 days; 5,357 is informational. Person B adapter preparation is present, but its interface must be reconciled with A and the real integration depends on A's final simulator and C's frozen plan. **Day 6 end-to-end integration is not verified.** No public data-release approval is implied by this report.

## Current publication checkpoint — 2026-11-13

This note supersedes only forward-looking status statements above; earlier audit snapshots, experiment results, and dated records remain historical.

- **Prediction API:** the isolated-worktree suite completed with 8 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_prediction_api -v`.
- **SHAP:** the isolated-worktree suite completed with 9 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v`. The 4,394 × 11 native XGBoost contribution run has maximum additivity error `5.270703695714474e-07` at `1e-6` tolerance and explains the residual prediction, not final `pred_ratio`.
- **Synthetic demo:** `models/person_b_demo.py` is already published on `person-b-prediction-cascade` in commit `8e4e4346b3ea1ec4fb4c7065b6b4e0ed16190e84`. It uses only the synthetic H1–H8 fixture; this does not approve release of production data.
- **B05:** cell 15 is an explanatory Markdown note excluding the invalid lane-feature duplicate; cell 14 remains an in-sample exploratory comparison, and weather availability as of departure is unestablished. The notebook was not executed; cell 21 and its stored output were preserved.
- **Day 6:** the approved demand is 5,395 master-train core legs / 14 days; 5,357 remains informational. The destination simulator source still describes one edge as one day and does not expose `scenario["travel_time_multipliers"]`, so duration-aware end-to-end integration is not verified. The two plan snapshots and their hashes are reconciled in `docs/person_b_final_handoff_v1.md`; Person C confirmation of the candidate's wrapper and provenance remains pending.
- **Release:** trip-level predictions, outcomes, intervals, and SHAP contribution rows remain `INTERNAL_ONLY`. Lane-level risk/realized tables and local SHAP explanations/plots require owner approval. The B05 notebook contains stored row-preview and lane-level outputs, so its edited notebook remains release-gated; no standalone generated result CSVs are included in this prepared bundle.

## Synthetic demonstration checkpoint — 2026-11-13

A local command-line smoke demo, `models/person_b_prediction_demo.py`, joins the Prediction API point prediction, saved Method C interval calculation, and native XGBoost local contributions using one hypothetical request with synthetic endpoint labels. It writes no output and does not read raw leg or prediction tables. It still loads the trained model and conformal parameters, which remain `REQUIRES_OWNER_APPROVAL` for external distribution. The printed example is not real performance, a risk category, or a causal explanation. The existing `models/person_b_demo.py` remains a separate synthetic H1–H8 structural-cascade illustration. No data-release approval is implied.
### Fresh validation checkpoint — 2026-11-12

From the isolated cleanup worktree, the existing API suite passed 8/8 and the SHAP suite passed 9/9 using the repository `.venv` (Python 3.10.8, NumPy 2.2.6, pandas 2.3.3, XGBoost 3.2.0, SHAP 0.49.1, Matplotlib 3.10.9). `pip check`, in-memory Python compilation of the relevant Person B modules, requirements parsing, and strict B05 `nbformat` 5.10.4 validation passed. The B05 notebook was validated structurally only; no cells ran. The synthetic API/interval/TreeSHAP CLI demo and existing synthetic H1–H8 structural demo both completed. The full Day 5 pipeline, full SHAP population run, notebooks, and Day 6 integration were not executed.
