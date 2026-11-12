# SupplyShield Person B Final Handoff — Version 1

**Prepared:** 2026-11-12
**Repository:** `day6-integration-solo` at HEAD `130787c7858d58395b96fdd681d86517f03961c8`
**Scope:** Person B's independent prediction, uncertainty, risk, structural-cascade, API, explainability, demo-preparation and documentation work. This handoff is not a publication approval or Day 6 integration certificate.

**Snapshot clarification (2026-11-13):** The repository/HEAD metadata above identifies the earlier source snapshot. Fresh independent checks for this handoff were run in the isolated cleanup worktree based at 8e4e4346b3ea1ec4fb4c7065b6b4e0ed16190e84; current API and SHAP suites each passed there. The historical Day 6 run described below is not current integration verification.

## 1. Responsibilities and status

Person B owns the prediction and conformal workflow, lane risk outputs, B04 structural cascade, Prediction API, SHAP explainability, synthetic Person B demo, and Person B documentation. Person A owns the data/network/weather pipeline and operational queue simulator. Person C owns the optimizer and optimizer plans. This handoff does not claim ownership of A/C code or approval of shared outputs.

| Workstream | Current status |
|---|---|
| B01 data/split analysis | Historical B01 split analysis is labelled historical in its current local notebook text. `data/processed/split_trip_ids.csv` is the authoritative model split. Raw Delhivery input data is unavailable in this checkout, so source-data rebuild is not established here. |
| B02 prediction | Saved residual XGBoost model and master-split evaluation exist. Prediction API exists and its test suite has 8/8 passing at the recorded verification checkpoint. |
| B03 uncertainty | Saved Method C calibration parameters, test intervals, comparisons and manifest exist. Empirical test coverage is below nominal at all three recorded levels; no online or lane-level coverage guarantee is claimed. |
| B04 cascade | Final-v3 notebook and final-v2 output package record a completed structural scalar-load analysis with conservation checks. The new CLI illustration uses the same synthetic H1–H8 fixture. This is not the operational queue simulator. |
| B05 risk | Representative lane-route predictions and lane-level risk artifacts exist. Cell 15 remains unresolved and is not a validated analysis. Cell 21's current text correction has no demonstrated computational change. |
| SHAP | Native XGBoost TreeSHAP implementation and saved full-test run exist. The SHAP test module passed 9/9. Attributions explain the residual output only. |
| Demo | A synthetic-only command-line illustration is prepared at `models/person_b_demo.py`. No demo format or scope is specified by the repository README/specification inspected; no interactive application is claimed. |
| Day 6 | The local historical report and manifest record 40/40 runs (10 scenarios × 4 strategies) under 5,395 legs / 14 demand days, a 40-day simulator horizon, and a static 14-day closure; 19 runs are recovery-censored. This configuration-specific result does not establish that this Person B base contains the final simulator interface or is team-approved. The distinct 7-day/120-day/3-day configuration is not interchangeable. Current A-interface alignment and C-plan confirmation remain pending. Evidence is in the original-checkout `docs/person_b_day6_final_integration_v1.md` and `experiments/day6/final_integration_v2/execution_manifest.json`; it is not included in this source-only worktree.

## 2. Dataset, split and feature preparation

`data/processed/split_trip_ids.csv` defines 9,969 train, 2,424 calibration and 2,424 test trips. The mapped population contains 17,674 train, 4,301 calibration and 4,394 test legs. B02/B03 evaluation uses this master split. The legacy `data/datasplit/` split and B01 baseline are historical and are not the current B02 held-out evaluation.

The supported B02 training population is 5,395 core training legs over the approved 14-day Day 6 denominator. The separate 5,357 strict timestamp-window count is informational and does not replace or filter that approved Day 6 population. B04's own historical baseline uses a separate 14-day departures window; those populations must not be conflated.

The project README `docs/README.md` describes the data pipeline but does not define a public-demo format. Its broad testing-date wording does not replace the precise master-split file; any correction to this shared data-pipeline README needs its owner review and is not made here.

## 3. B02 residual prediction

The saved model is `models/residual_xgb_plain_master_split_v1.json`, XGBoost 3.2.0, best iteration 134. It predicts a residual correction on top of a lane baseline:

`pred_ratio = lane_base + predicted_residual`

The ten ordered features are `osrm_time_min`, `osrm_distance_km`, `osrm_speed_kmh`, `log_osrm_time`, `start_hour`, `start_dow`, `is_weekend`, `is_ftl`, `lane_base`, and `lane_history_count`. The model fit used 14,073 legs from 7,975 trips, with 3,601 training legs in its later validation partition. Calibration and test trips are held out from model fitting. No weather feature is part of the primary B02 model.

Saved test predictions report model MAE/RMSE of 0.653957 / 1.727803. The B02 as-of prior-history baseline reports 0.668606 / 1.737590 on the same 4,394 test legs. This baseline is distinct from B05's fixed training-only baseline comparison; the two baseline metrics should not be presented as the same method.

Primary artifacts: `notebooks/B02_xgboost_day2.ipynb`, `models/residual_xgb_plain_master_split_v1.json`, `experiments/day2/master_split/`, and `data/processed/preds_cal_test_master_split_v1.csv`. The prediction CSV includes actual labels for evaluation; labels are not API/model inputs and require data-release review.

## 4. B03 conformal intervals

Method C applies signed-residual split-conformal offsets grouped by route type and calibration-distance tercile. It uses group offsets when the saved calibration group size meets the configured minimum; otherwise it falls back to global offsets. The saved parameters are in `experiments/day3/master_split_v2/final/conformal_params_method_c_master_split_v2.json`; saved test bounds are in `experiments/day3/master_split_v2/final/test_intervals_method_c_master_split_v2.csv`.

On 4,394 held-out test legs, saved empirical coverage is 46.1538% at nominal 50%, 77.6286% at nominal 80%, and 88.8484% at nominal 90%. These are leg-level split-partition results, not lane-day coverage, online coverage, or a guarantee for future lanes. The saved workflow notes that some calibration outcomes finish after the earliest test departure, so it is not a per-departure online calibration guarantee.

## 5. B05 lane-risk analysis

The representative source `experiments/day5/risk_table_master_split_v1.csv` has 296 lane-route rows across 292 directed lanes. The expanded `models/outputs/risk_table.csv` has one row per directed lane and includes baseline, point prediction, interval endpoints, relative multipliers and excess hours. `models/outputs/risk_table_lane.csv` is a separate compatibility projection. The saved generation manifest is `models/outputs/day5_final_manifest_master_split_v1.json`.

Lane baselines use master-training outcomes, with route-type/distance-tercile and global training fallbacks where needed. Representative route point estimates and interval endpoints are weighted by their training-leg counts and reduced to lane rows. Averaged endpoints are proxy aggregates, not formally calibrated lane-level intervals or valid mixture intervals. `models/outputs/realized_test_lane_master_split_v2.csv` contains all-lane held-out realized outcomes; `models/outputs/realized_test_lane.csv` is the earlier 93-lane thresholded artifact. Neither is a planning input.

**B05 cell 15 remains unresolved.** Its `merged_train` lacks the lane-level fields it references, and the intended grain/feature provenance is not specified. `actual_time_min` is an observed outcome and must not be substituted as a prediction feature. Leave the cell unexecuted and do not use it as evidence until a safe, explicit experiment specification exists. **Cell 21 requires no computational correction:** its current source/output changes from HEAD are limited to explanatory text encoding; preserve its saved computation and output.

## Day 5 final pipeline and reproducibility

`models/day5_final_pipeline.py` is a deterministic source-level builder/checker; it is not the Prediction API and is not executed as part of this handoff. It consumes the authoritative split and processed legs, master-split prediction export, core edge/training inputs, B05 representative predictions and manifest, B03 Method C parameters/test intervals/run manifest/success marker, B02 model card/model, and the two legacy prediction/risk/realization files used for compatibility checks. The exact required files are `data/processed/split_trip_ids.csv`, `data/processed/legs.csv`, `data/processed/core_edges.csv`, `data/processed/core_train_legs.csv`, `data/processed/preds_cal_test_master_split_v1.csv`, `data/processed/preds_test.csv`, `models/outputs/risk_table_lane.csv`, `models/outputs/realized_test_lane.csv`, `experiments/day5/risk_table_master_split_v1.csv`, `experiments/day5/risk_table_master_split_v1_manifest.json`, `experiments/day3/master_split_v2/final/conformal_params_method_c_master_split_v2.json`, `experiments/day3/master_split_v2/final/test_intervals_method_c_master_split_v2.csv`, `experiments/day3/master_split_v2/run_manifest.json`, `experiments/day3/master_split_v2/_SUCCESS.json`, `experiments/day2/master_split/final_model_card_master_split_v1.json`, and `models/residual_xgb_plain_master_split_v1.json`. The paths are declared in `calculate()` in the script.

The script's exact expected outputs are `data/processed/preds_test_master_split_v1.csv` (4,394 row-level held-out predictions), `models/outputs/risk_table.csv`, `models/outputs/realized_test_lane_master_split_v2.csv`, `models/outputs/day5_test_interval_coverage_master_split_v1.csv`, `models/outputs/day5_lane_test_metrics_master_split_v1.csv`, `models/outputs/day5_model_vs_baseline_master_split_v1.json`, and `models/outputs/day5_final_manifest_master_split_v1.json`. These outputs are not present in this isolated worktree; do not treat their absence as a failed `--check` or regenerate them in this task. Several would contain held-out outcomes or lane-level details and are not public demo artifacts.

`--check` recomputes in memory and compares all existing outputs byte-for-byte; it requires those output files to exist. `--write` refuses any existing output and creates the listed artifacts. `--refresh-generated` requires a matching previous manifest but overwrites those output paths, so preserve the current files and do not use it without a separate explicit authorization. Run a read-only reconstruction check only when all seven expected outputs already exist:

```powershell
.\.venv\Scripts\python.exe models/day5_final_pipeline.py --check
```

A one-time `--write` command is `.\.venv\Scripts\python.exe models/day5_final_pipeline.py --write`; it creates the listed outputs and must not be used without a separately approved output-generation task. `--refresh-generated` is also write-capable and can replace verified outputs. Do not run either write mode as part of a presentation/demo workflow.
No pipeline mode was run for this handoff. The pipeline and Prediction API share the saved model/Method C contract but the pipeline does not call the API.
## 6. B04 structural cascade

`sim/simulate.py::simulate_cascade` and `build_neighbors` implement the B04 structural load-redistribution abstraction. It symmetrizes directed lanes, redistributes the entire accumulated scalar load from failed hubs, uses dispatch-capacity proxies for spare room, and checks load conservation. It does not preserve OD flows/direction, model only excess rerouting, or establish measured receiving capacity.

Authoritative artifacts are `notebooks/B04_cascade_day4_final_v3.ipynb`, `experiments/day4/final_v2/`, and `docs/cascade_rules_v1.md`. The saved manifest records 100 real-data single-hub scenarios, 44 synthetic stress rows, convergence/conservation checks, and a largest cascade of four hubs including the initial failure. These are saved-manifest/notebook results; this task did not rerun the B04 experiment. Historical Day 4 results remain separate from final_v2.

## 7. Prediction API

`models/prediction_api.py` takes caller-supplied precomputed as-of `lane_base` and `lane_history_count`; it does not read raw outcome history or calculate lane statistics. It builds the exact B02 feature order, returns point predictions, and can apply saved Method C intervals. Zero-history requests use the documented fit-only fallback `lane_base = 2.0`. The API rejects target/outcome inputs.

Recorded verification command: `.\.venv\Scripts\python.exe -m unittest models.test_prediction_api -v` — **8 passed, 0 failed**. No API test rerun was needed in this task because the demo uses the separate B04 structural simulator and no API code changed.

## 8. SHAP explainability

SHAP 0.49.1 `TreeExplainer` could not parse the saved XGBoost 3.2.0 model's vector-valued base score. The implementation uses native XGBoost `Booster.predict(dmatrix, pred_contribs=True)` contributions and SHAP only for presentation. The saved full-test run covers 4,394 rows with a `(4394, 11)` matrix (ten features plus bias), finite values, and maximum additivity error `5.270703695714474e-07` against `1e-6`. These contributions explain the residual prediction, not final `pred_ratio` after adding `lane_base`.

The existing module `models/test_shap_explainability.py` passed **9/9** on 2026-11-12 using `.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v`. Environment: Python 3.10.8, SHAP 0.49.1, XGBoost 3.2.0, NumPy 2.2.6, pandas 2.3.3 and Matplotlib 3.10.9. The tests exercise a small inference sample; they did not rerun the 4,394-row experiment. Full-run evidence remains in `experiments/day5/shap_native_v2/run_manifest.json` and its validation report.

## 9. Synthetic Person B demo

Run from the repository root in the existing `.venv`:

```powershell
.\.venv\Scripts\python.exe models/person_b_demo.py
```

The script reuses the H1–H8 synthetic fixture from the B04 final notebook and calls `sim.simulate.build_neighbors` / `simulate_cascade`. It prints calm-load, full-cascade and higher-tolerance examples; assertions check the fixture outcomes and conservation. It reads no processed data, prediction file, actual outcome, lane table, SHAP row contribution, model weights or conformal parameters, and writes no output files. Its displayed values are illustrative synthetic results only, not predictions or estimates for the observed network.

The repository does not specify whether the final demo must be interactive, slide-based or a web app. The supported deliverable here is therefore a reproducible command-line illustration, not an invented product interface. The global SHAP bar chart and aggregate evaluation summaries may be considered separately for a presentation, but remain subject to the classifications and owner approvals in `docs/person_b_release_readiness_v1.md`.

## 10. Data-release status

Use `docs/person_b_release_readiness_v1.md` as the artifact-level release inventory. In summary:

- **Aggregate demo candidates:** final model-card/evaluation summaries, aggregate interval coverage/width summaries, aggregate SHAP feature importance/validation report, and aggregate Day 5 comparisons. These are candidates only; no owner approval is implied.
- **Internal only:** trip-level predictions/targets, test intervals, split IDs and per-leg SHAP contribution exports.
- **Owner approval required:** lane-specific prediction/risk tables, realized lane outcomes, per-lane metrics, route-level representatives, local SHAP examples, beeswarm plots, model weights, conformal parameters, detailed manifests and network/capacity tables.
- **Historical reference:** legacy split prediction/interval exports and earlier experiment versions. Historical status does not make row-level files safe to publish.

The synthetic demo script is separate from these production artifacts. No restricted source artifact was copied into a demo or report directory, and no data-release approval was made as part of this work.

## 11. Tests, reproduction and limits

| Check | Command/evidence | Result and scope |
|---|---|---|
| Prediction API suite | `.\.venv\Scripts\python.exe -m unittest models.test_prediction_api -v` | Fresh isolated-worktree run on 2026-11-12: 8 passed, 0 failed. |
| SHAP suite | `.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v` | Fresh isolated-worktree run on 2026-11-12: 9 passed, 0 failed. Does not rerun the full saved experiment. |
| Person B synthetic demo | `.\.venv\Scripts\python.exe models/person_b_demo.py` | Passed its synthetic fixture assertions and conservation checks in this task. No files written. |
| B04 full analysis | `experiments/day4/final_v2/run_manifest_v1.json`, notebook stored outputs | Saved checks report complete; not rerun in this task. |
| Day 5 saved artifact checks | `models/day5_final_pipeline.py --check` and the saved manifest are documented separately | Prior saved verification is recorded in the release-readiness report; not rerun here. |

The processed dataset is available, but the raw Delhivery scan inputs are not present for a source-data rebuild. B05 cell 15 lacks a supported feature/grain specification. Public release approval for lane-level and row-level artifacts is pending. The repository has no explicit public demo rubric or required format.

## 12. Independent completion versus integration dependencies

Independently completed or verified: saved B01–B05 prediction, calibration, risk and structural-cascade work; Prediction API (8/8); SHAP suite (9/9) and saved native full-test explanation evidence; and the new synthetic-only structural demo (passed). B05 cell 15 remains blocked by missing experiment specification. Demo format beyond the reproducible CLI illustration remains undecided. Data-release decisions remain with authorized owners.

Day 6 is separate and incomplete. Person A must deliver and test the final duration-aware simulator using `scenario["travel_time_multipliers"]`; Person B must then reconcile only B-owned adapter/tests to that interface. Person C must supply the approved frozen plan artifact and confirm its wrapper/provenance. The local `experiments/c_multiflow_plans.json` was absent at the last recorded check. Do not describe adapter preparation or earlier local experiments as current end-to-end integration.

## Current publication checkpoint — 2026-11-13

This note supersedes only forward-looking status statements above; earlier audit snapshots, experiment results, and dated records remain historical.

- **Prediction API:** the isolated-worktree suite completed with 8 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_prediction_api -v`.
- **SHAP:** the isolated-worktree suite completed with 9 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v`. The 4,394 × 11 native XGBoost contribution run has maximum additivity error `5.270703695714474e-07` at `1e-6` tolerance and explains the residual prediction, not final `pred_ratio`.
- **Synthetic demo:** `models/person_b_demo.py` is already published on `person-b-prediction-cascade` in commit `8e4e4346b3ea1ec4fb4c7065b6b4e0ed16190e84`. It uses only the synthetic H1–H8 fixture; this does not approve release of production data.
- **B05:** cell 15 is an explanatory Markdown note excluding the invalid lane-feature duplicate; cell 14 remains an in-sample exploratory comparison, and weather availability as of departure is unestablished. The notebook was not executed; cell 21 and its stored output were preserved.
- **Day 6:** the approved demand is 5,395 master-train core legs / 14 days; 5,357 remains informational. The destination simulator source still describes one edge as one day and does not expose `scenario["travel_time_multipliers"]`, so duration-aware end-to-end integration is not verified. The tracked plan at the Person B target base commit 8e4e4346b3ea1ec4fb4c7065b6b4e0ed16190e84 has SHA-256 `8a2f4fa916eb87d8361dceecca088bff9efa7a7741f8178c481602edb249d8c9`. A separate untracked plan in the original `day6-integration-solo` checkout has SHA-256 `f588d41116e69cf00e71f8602ee6f98919140143fa10ec50a63c15a5a99c435a`, matching the previously expected digest. These are distinct snapshots; neither was copied or changed here. Person C must confirm the candidate's wrapper, demand, penalty, and provenance before integration or treating it as frozen.
- **Release:** trip-level predictions, outcomes, intervals, and SHAP contribution rows remain `INTERNAL_ONLY`. Lane-level risk/realized tables and local SHAP explanations/plots require owner approval. The B05 notebook contains stored row-preview and lane-level outputs, so its edited notebook remains release-gated; no standalone generated result CSVs are included in this prepared bundle.

### Synthetic prediction-plus-SHAP smoke demo (2026-11-12)

`models/person_b_prediction_demo.py` accepts one hypothetical request with synthetic endpoint labels, calls the Prediction API and saved Method C parameters, and calculates native XGBoost contributions for that same feature row. It prints the point ratio, travel-time estimate, interval bounds, and largest-magnitude signed local contributions. It writes no files and reports no real-record outcome or performance metric. Those local contributions explain the residual component only; the lane baseline is added separately. The command is `.\.venv\Scripts\python.exe models/person_b_prediction_demo.py` from the repository root.
