# Person B Remaining Work Audit — Version 1

**Audit date:** 2026-11-12
**Repository snapshot before this report was created:** branch `day6-integration-solo`, HEAD `130787c7858d58395b96fdd681d86517f03961c8`.
**Scope:** Person B deliverables and dependencies. This report does not certify unrepeated tests, modify teammate work, or declare Day 6 integrated.

## 1. Repository and Git state

Before creating this report, `git status --short --branch` showed no staged files and these tracked modifications:

```text
 M notebooks/B05_risk_table_day5.ipynb
 M notebooks/B06_day6_optimizer_simulator_interface_v2.ipynb
 M opt/c_multiflow.py
 M sim/simulator.py
```

The untracked paths were:

```text
data/processed/preds_test_master_split_v1.csv
docs/day6_contract_reconciliation_v1.md
docs/day6_end_to_end_handoff_v1.md
docs/day6_integration_contract_v1.md
docs/day6_integration_handoff.md
docs/person_b_day1_day5_handoff.md
docs/person_b_independent_work_handoff.md
docs/shap_explainability.md
experiments/day5/shap_native_v1/
experiments/day5/shap_native_v2/
experiments/day6/solo_integration_v1/
experiments/day6/v2/
models/day5_final_pipeline.py
models/day6_integration.py
models/outputs/day5_final_manifest_master_split_v1.json
models/outputs/day5_lane_test_metrics_master_split_v1.csv
models/outputs/day5_model_vs_baseline_master_split_v1.json
models/outputs/day5_test_interval_coverage_master_split_v1.csv
models/outputs/realized_test_lane_master_split_v2.csv
models/outputs/risk_table.csv
models/shap_explainability.py
models/test_day6_integration.py
models/test_shap_explainability.py
```

The specified plan `experiments/c_multiflow_plans.json` is absent. Its expected SHA-256, `f588d41116e69cf00e71f8602ee6f98919140143fa10ec50a63c15a5a99c435a`, is therefore **not verified**. The plan spec (5,395 training legs / 14 days; penalty 96.0 leg-hours per undelivered leg) is recorded as user-provided contract information, not as a checked plan artifact.

There is no `data/raw/` directory in this checkout. Processed data and saved outputs are available, but rebuilding the source leg dataset from raw Delhivery scans cannot be reproduced from this checkout alone.

## 2. Person B deliverables inventory

| Area | Implementation and artifacts | Latest verifiable evidence | Status and exact remaining work |
|---|---|---|---|
| Dataset / features / B01 | `src/targets.py`; `notebooks/B01_dataset_analysis.ipynb`; `data/processed/split_trip_ids.csv`; `docs/README.md`; `experiments/day1/` | B01's current cell 10 labels its 60/20/20 `data/datasplit/` analysis historical and gives the authoritative master counts and date boundaries. B01 is clean in the current working tree. | **Complete with source-data limitation.** Raw inputs are absent. B01 results are historical; they are not the current B02 evaluation. Keep legacy split files while their dependencies remain. |
| B02 residual model | `notebooks/B02_xgboost_day2.ipynb`; tracked `models/residual_xgb_plain_master_split_v1.json`; `experiments/day2/master_split/` | Model card records the master split, 10-feature order, best iteration 134, and test MAE 0.654 versus 0.6686 for its lane baseline. Saved model SHA-256: `72324e57d019c5f70b65838f8a05901af5f5cbb73ffc4050c3d1d3b6c2a63acf`. | **Complete as a saved model/evaluation.** Do not claim fresh training or independent rerun in this audit. The notebook contains exploratory versions in addition to the final model record. |
| B03 conformal intervals | `notebooks/B03_conformal_day3.ipynb`; `experiments/day3/master_split_v2/final/conformal_params_method_c_master_split_v2.json`; `test_intervals_method_c_master_split_v2.csv`; `run_manifest.json` | Saved manifest says complete: 4,394 test legs / 2,424 trips. Method C test coverage recorded as 46.15%, 77.63%, 88.85% for 50/80/90%. Final test interval file has 4,394 rows. | **Complete as saved offline evaluation.** 90% coverage is below nominal. The documentation notes that some calibration outcomes finish after the earliest test departure; this is not an online/per-departure coverage guarantee. No test recalibration should be done. |
| B04 structural cascade | B-owned structural implementation `sim/simulate.py`; rules `docs/cascade_rules_v1.md`; `notebooks/B04_cascade_day4_final_v3.ipynb`; `experiments/day4/final_v2/` | Tracked final manifest status is `complete`; it records 100 hubs, 292 directed lanes, a 14-day baseline, 100 single-hub failures, and passing conservation/output checks. Notebook includes synthetic toy checks and saved outputs. | **Complete within its stated abstraction.** It symmetrizes lanes and redistributes scalar loads; it is not an OD-preserving operational queue. Do not conflate it with A's simulator or risk-adjusted transit. Legacy Day 4 artifacts remain historical. |
| B05 representative risk table | `notebooks/B05_risk_table_day5.ipynb`; untracked generator/checker `models/day5_final_pipeline.py`; `experiments/day5/risk_table_master_split_v1.csv` (296 lane-route rows); untracked `models/outputs/risk_table.csv` (292 lane rows); tracked `models/outputs/risk_table_lane.csv` (292 rows) | `day5_final_manifest_master_split_v1.json` says complete; its hashes match the current six output artifacts checked read-only, including the 292-row `risk_table.csv` (SHA-256 `051d71563f540df4869d4a2bd59dea38c5c2f173c47974f47629674ceffb53d7`). Both 292-row risk files cover 292 unique directed keys. | **Primary saved artifacts complete; notebook needs review.** Current notebook diff changes cells 8, 12, 14, 15, and 21 and adds cell 22. Cells 12/14 have cleared outputs; cell 15 remains unexecuted and explicitly unresolved. Cell 21 (C5) source and stored output differ from HEAD; do not treat its output as independently consistent without review. Cells 17–18 are write-once and will fail if rerun with existing outputs. Use pipeline `--check` for saved artifact verification, not notebook output regeneration. |
| Prediction API | `models/prediction_api.py`; `models/test_prediction_api.py`; `docs/prediction_api.md`; saved model and B03 parameters | Code implements the ordered ten-feature contract, loads the tracked model and Method C JSON, uses caller-provided as-of lane history, rejects target columns, and includes saved prediction and interval parity tests. | **Implemented; current suite result not established in this audit.** No API test-result report was found. Run the suite and record its exact result before publication. |
| SHAP explainability | Untracked `models/shap_explainability.py`, `models/test_shap_explainability.py`, `docs/shap_explainability.md`; untracked `experiments/day5/shap_native_v1/` and `shap_native_v2/` | V2 manifest/report records all 4,394 test rows, `(4394, 11)` contributions, all finite, maximum additivity error `5.270703695714474e-07` under `1e-6` absolute tolerance, native XGBoost contributions for residual output, and no target columns read. Manifest model/prediction hashes match current tracked inputs. | **Analysis run recorded complete; test suite not rerun here.** V1 and V2 have identical hashes for feature importance, row contributions, local explanations, and three local plots; beeswarm image, manifest, and report differ. Review whether both versions are needed; preserve both until publication/data policy is decided. |
| Person B demo | No app, web service, Streamlit, or Gradio implementation found. `notebooks/B06_day6_optimizer_simulator_interface_v2.ipynb` is a shared integration/toy demonstration. | Existing handoff says no interactive application exists. | **Not implemented / scope unclear.** Obtain a concrete demo requirement before building one. B06 is not a production demo and is currently modified/shared. |
| Day 6 adapter | Untracked `models/day6_integration.py`, `models/test_day6_integration.py`; new B handoffs and `experiments/day6/` history | In the prior project turn, the `.venv` command `python -m unittest models.test_day6_integration -v` passed 28 tests; `python -m models.day6_integration` passed preflight with 5,395 rows, 292 lanes, and 385.357143 legs/day. Neither was a real optimizer/simulator integration run. | **Integration blocked; adapter needs A-interface reconciliation.** Current adapter gates on `edge_durations` and builds adjusted-hour costs; the newly supplied A plan uses `scenario["travel_time_multipliers"]` keyed by directed edge and applies multipliers to baseline hours. Do not guess or edit the adapter to the unfinished API. Once A's implementation lands, adapt only B-owned files to that actual interface and ensure exactly-once multiplication. C's frozen plan is also absent. |
| B technical handoffs | `docs/person_b_day1_day5_handoff.md`; `docs/person_b_independent_work_handoff.md`; `docs/prediction_api.md`; `docs/shap_explainability.md`; Day 6 docs | The newer Day 6 v1 handoff states the 5,395 demand contract and current blockers. | **Conflicting/stale documents need consolidation.** The older handoffs say no SHAP deliverable exists; that is false for the current local tree. Older Day 6 handoffs/contracts describe 5,357 as authoritative and/or claim integration complete. The modified B06 notebook also contains old 5,357 and old interface descriptions. Correct only B-owned documentation; obtain review for B06/shared content. |

## 3. Completed work with evidence

- **Model artifacts exist:** the saved residual model and Method C calibration JSON are tracked; the SHAP and Day 5 manifests point to the current model/prediction inputs.
- **Saved prediction and conformal evidence:** Day 5 manifest records 8,695 prediction parity rows and 4,394 interval parity rows. Its output hashes match the current saved output files. This is stored evidence; it was not recomputed in this audit.
- **Risk-table coverage:** `models/outputs/risk_table.csv` and `risk_table_lane.csv` each have 292 rows and 292 unique directed lanes. The 296-row experiment table is lane-route grain, not one row per lane.
- **Structural cascade:** final_v2 manifest and success marker are present; documented limitations distinguish structural scalar-load stress from operational OD routing.
- **SHAP:** v2 saved report documents native TreeSHAP additivity and residual-only interpretation. It does not explain the final ratio after adding `lane_base`, establish causality, or provide online coverage.
- **Day 6 Person B unit/preflight checks:** 28 tests passed in the previous project turn and the current Day 6 handoff records the exact scope. This does not validate A's new interface or consume C's frozen file.

## 4. Incomplete work and exact issues

1. **B05 cell 15:** `notebooks/B05_risk_table_day5.ipynb` still references `distance_km` and `median_actual_time` on `merged_train`, although the joined dataframe is leg-level and those are lane-level `core_edges` fields. `actual_time_min` is an outcome. The cell is unexecuted and labeled unresolved; do not substitute similar columns or include it as a validated analysis.
2. **B05 C5 output consistency:** cell 21 source and saved output differ from HEAD. Cell 21 is in the appended C1–C5 section. Review with Person C before treating or publishing it as an unchanged teammate-facing deliverable.
3. **API verification:** run `models.test_prediction_api` in `.venv`; compare test counts and outputs to recorded saved parity artifacts. No current test result is claimed here.
4. **SHAP suite:** run `models.test_shap_explainability` only when ready to verify the test suite. The saved v2 analysis report is not a substitute for test-suite results.
5. **Day 6 interface:** A's planned key is `scenario["travel_time_multipliers"]`; B adapter currently has a different duration interface and adjusts graph costs. Wait for A's actual source and use its exact contract. Do not pre-emptively modify A or guess a B integration.
6. **Person C plan:** `experiments/c_multiflow_plans.json` is absent. The expected digest cannot be checked. Existing `experiments/day6/solo_integration_v1/simulator_input_plans.json` and `normalized_optimizer_plans.json` are B's historical run artifacts, not proof that the newly specified frozen C plan is present or current.
7. **No interactive demo:** no separate B-owned demo component exists. B06 is a notebook and its current content is stale for the latest demand and timing contracts.
8. **Data release:** `data/processed/preds_cal_test_master_split_v1.csv` contains `y_ratio`, trip IDs, lanes, and timestamps. Untracked `preds_test_master_split_v1.csv` also contains row-level test targets and identifiers. Test interval exports include trip identifiers; realized lane tables contain test outcomes. SHAP row contributions include row-level feature/contribution data. Obtain data-release approval before publishing these, even where raw UUIDs are replaced with sequential explanation IDs.

## 5. Independent work that can be completed now (priority order)

1. **Verify prediction API tests and saved parity** using `.venv`: `python -m unittest models.test_prediction_api -v`. Record result without changing artifacts; diagnose failures without loosening parity tolerance.
2. **Verify SHAP test suite** using `.venv`: `python -m unittest models.test_shap_explainability -v`. Treat the existing v2 run manifest/report as historical run evidence, not as proof this suite passes now.
3. **Reconcile Person B-owned handoffs** by marking SHAP as present, superseding 5,357-demand claims with the 5,395 contract, and clearly distinguishing the prior one-day/ non-risk-adjusted Day 6 experiment from current readiness. Keep B06 unchanged until shared/owner review.
4. **Make a publication/data review list** for the row-level target, prediction, interval, realized, and contribution files. This needs a release decision but no A/C code changes.
5. **Check B05 structure and saved results** without notebook execution; decide whether to retain its exploratory weather cells as explicitly unresolved. Do not use cell 15 as analysis evidence and do not touch C1–C5 without C review.

## 6. Work blocked by A or C

### Person A

- Deliver the actual duration-aware simulator implementation using `scenario["travel_time_multipliers"]` and verify application exactly once to baseline hours.
- Verify daily arrival rounding, including 6/24/25/30/48/72-hour examples; closure behavior; in-flight continuation; outgoing-only failed-hub capacity; receiving at failed hubs; queued flow accounting; and zero-capacity destination delivery.
- Once source exists, Person B can reconcile `models/day6_integration.py` and its tests against the exact API without changing `sim/simulator.py`.

### Person C

- Supply `experiments/c_multiflow_plans.json` at the specified SHA-256, or provide a new confirmed immutable path/hash if the supplied file changes.
- Confirm the actual plan wrapper includes demand/objective/unmet metadata needed for validation, and that plan totals use 5,395 / 14 demand and penalty 96.0.
- Review the B05 C1–C5/C5 stored-result difference and the 93-lane versus all-lane outcome consumers. Do not substitute the historical B-generated Day 6 plan for C's frozen plan.

## 7. Recommended execution sequence

1. Run the API test suite and record results; then run SHAP tests and record results. Do not regenerate outputs.
2. Correct only stale Person B documentation after confirming the exact intended publication scope; leave B06 and C1–C5 pending owner review.
3. Obtain Person A's implemented duration API and regression results.
4. Verify the exact Person C plan file SHA-256, wrapper, demand, penalty, directed edges, and unmet accounting.
5. Reconcile only B-owned adapter/tests to A's actual `travel_time_multipliers` interface and the validated C plan.
6. Run integration acceptance tests and actual scenarios only after steps 3–5. Create a new versioned experiment/manifest only after successful real execution.
7. Complete data-release and publication review before publishing row-level outputs or test outcomes.

## 8. Exact first task after this audit

Run the existing Prediction API test suite from the repository root with the current `.venv`:

```powershell
.\.venv\Scripts\python.exe -m unittest models.test_prediction_api -v
```

Record the exact pass/fail count and any parity mismatch. Do not modify the API, artifacts, or tolerances as part of that verification step.

## Subsequent verification update — 2026-11-12

This addendum records later checks without rewriting the audit snapshot above.

- **Prediction API:** the existing `.venv` command `.\.venv\Scripts\python.exe -m unittest models.test_prediction_api -v` completed with **8 passed, 0 failed**. This supersedes the point-in-time statement above that the suite result was not established.
- **SHAP:** native XGBoost TreeSHAP (`Booster.predict(dmatrix, pred_contribs=True)`) is implemented and the saved `experiments/day5/shap_native_v2/` run records a `(4394, 11)` contribution matrix and maximum additivity error `5.270703695714474e-07`, within `1e-6`. The values explain the residual prediction, not `pred_ratio`; SHAP 0.49.1 `TreeExplainer` was not used because of the vector-valued XGBoost base-score parsing failure. The test suite result is not asserted by this addendum.
- **B05 review:** cell 15 remains unresolved, unexecuted and unsuitable as a validated analysis. Cell 21 differs from HEAD only in two explanatory multiplication-sign encoding corrections; its working-tree source and saved Markdown output agree, its computation is unchanged, and the saved aggregate numbers match HEAD. No fresh notebook execution was performed.
- **Day 6:** the approved population is 5,395 master-train core legs over 14 days. The 5,357 strict timestamp-window count is informational only. Person B's adapter preparation and focused checks are distinct from end-to-end integration: the adapter still needs alignment to A's `scenario["travel_time_multipliers"]` interface, and A's final duration-aware simulator plus C's frozen plan artifact remain prerequisites. End-to-end Day 6 is not verified.

## Subsequent demo preparation — 2026-11-12

The earlier inventory's statement that no separate Person B demo component existed described its audit snapshot. `models/person_b_demo.py` now provides a synthetic-only command-line illustration of the existing B04 H1–H8 structural cascade fixture. It was run with the repository `.venv`; fixture assertions and conservation checks passed. It is not an interactive app or a real-network forecast, writes no files, and contains no restricted production artifacts.

## Current publication checkpoint — 2026-11-13

This note supersedes only forward-looking status statements above; earlier audit snapshots, experiment results, and dated records remain historical.

- **Prediction API:** the isolated-worktree suite completed with 8 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_prediction_api -v`.
- **SHAP:** the isolated-worktree suite completed with 9 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v`. The 4,394 × 11 native XGBoost contribution run has maximum additivity error `5.270703695714474e-07` at `1e-6` tolerance and explains the residual prediction, not final `pred_ratio`.
- **Synthetic demo:** `models/person_b_demo.py` is already published on `person-b-prediction-cascade` in commit `8e4e4346b3ea1ec4fb4c7065b6b4e0ed16190e84`. It uses only the synthetic H1–H8 fixture; this does not approve release of production data.
- **B05:** cell 15 is an explanatory Markdown note excluding the invalid lane-feature duplicate; cell 14 remains an in-sample exploratory comparison, and weather availability as of departure is unestablished. The notebook was not executed; cell 21 and its stored output were preserved.
- **Day 6:** the approved demand is 5,395 master-train core legs / 14 days; 5,357 remains informational. The destination simulator source still describes one edge as one day and does not expose `scenario["travel_time_multipliers"]`, so duration-aware end-to-end integration is not verified. The two plan snapshots and their hashes are reconciled in `docs/person_b_final_handoff_v1.md`; Person C confirmation of the candidate's wrapper and provenance remains pending.
- **Release:** trip-level predictions, outcomes, intervals, and SHAP contribution rows remain `INTERNAL_ONLY`. Lane-level risk/realized tables and local SHAP explanations/plots require owner approval. The B05 notebook contains stored row-preview and lane-level outputs, so its edited notebook remains release-gated; no standalone generated result CSVs are included in this prepared bundle.
