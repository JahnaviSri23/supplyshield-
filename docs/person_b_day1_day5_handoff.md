# Person B Day 1–Day 5 Handoff

> **Status clarification — 2026-11-12:** The repository snapshot and findings below are retained as a historical Day 1–Day 5 handoff. Subsequent work added a Person B Prediction API and native XGBoost TreeSHAP explainability. The existing Prediction API suite was verified at 8/8 passing in the repository `.venv`. SHAP 0.49.1 is installed in that environment; the verified explainability run uses native XGBoost contributions because `shap.TreeExplainer` cannot parse this model's vector-valued base score. It produced 4,394 × 11 contributions with maximum additivity error about `5.27e-7` under a `1e-6` check, explaining the residual prediction only.
>
> For Day 6, the authoritative demand is 5,395 master-train core legs / 14 days. The 5,357 strict timestamp-window count is informational, not the demand population. Person B's adapter preparation and tests do not mean end-to-end integration is complete: the adapter must be aligned to A's `scenario["travel_time_multipliers"]` interface after A's final duration-aware simulator is available. C's frozen plan is also a dependency. The older status statements below describe the snapshot recorded in this handoff and are superseded where they conflict with this clarification.

## Status and scope

**Overall:** Person B’s Day 1–Day 5 artifacts are present and their primary saved outputs passed the read-only checks listed below. Day 6 is **not ready for production integration**: the optimizer does not export per-OD flows and the queue simulator does not accept multi-OD plans. Those changes cross Person C and Person A ownership boundaries.

**Repository snapshot:** branch `person-b-prediction-cascade`, HEAD `c968251` (`Finalize Day 5: generate risk table and realized test lane outputs`), tracking `origin/person-b-prediction-cascade` at the same commit at last local observation. No fetch was performed. Current pre-handoff worktree already had a modified B01 notebook. This handoff and the B05 exploratory-cell repairs are uncommitted; nothing is staged.

The eight historical B04 files identified in the previous audit are restored and tracked in this worktree. They are retained as historical evidence. The B01 split-documentation edit remains preserved.

## Data, target, and authoritative split

- `data/processed/legs.csv`: 26,369 leg rows, 14 columns, no exact duplicate rows, and no missing `delay_ratio` values in the checked file.
- `data/processed/split_trip_ids.csv`: 14,817 unique trips; train 9,969, calibration 2,424, test 2,424. Pairwise trip overlap is zero. Mapping all legs through the split gives 17,674 train, 4,301 calibration, and 4,394 test legs.
- The split is deterministic in `src/make_split.py`: trips are sorted by creation time and UUID; trips before the cutoff are train and the later trips are split chronologically into calibration and test. The date boundaries are train through 2018-09-25 23:58, calibration 2018-09-26 00:00 to 2018-09-29 20:36, and test from 2018-09-29 20:41.
- The network has 100 unique hubs and 292 unique directed core lanes. `core_train_legs.csv` contains 5,395 training legs on those lanes (4,709 trips), all mapped to train.
- `src/make_legs.py` defines `delay_ratio` as `actual_time_min / osrm_time_min` when actual time is finite and nonnegative and OSRM time is finite and positive. Person A’s `src/targets.py` defines `travel_ratio` as the same ratio and additionally requires finite, nonnegative distance and a non-null route type.
- Independent in-memory comparison applying Person A’s eligibility rule to all legs found 26,369 eligible rows: 22,146 bitwise-equal values, 4,223 differences attributable to floating-point evaluation, maximum absolute difference `7.105427357601002e-15` (all within `1e-12`). No target-value mismatch was found. `legs_targeted.csv` has only the 7,817 weather-enriched rows; it is not the full target comparison population.
- The B01 notebook’s local Markdown edit explicitly labels its 60/20/20 `data/datasplit/` analysis and baseline as historical and identifies `split_trip_ids.csv` as authoritative. Historical split counts remain 8,890/2,963/2,964 trips and 15,621/5,441/5,307 legs. The displayed historical baseline claims are not B02 metrics. `docs/README.md` still describes testing as “30 September onward”; its author is outside Person B, so that file was left unchanged. Readers should treat that section as legacy until Person A clarifies it.
- Keep `data/datasplit/`: `src/check_weather_handoff.py` depends on it. No archival decision is recorded.

## Day 1 — Dataset analysis

**Deliverable:** `notebooks/B01_dataset_analysis.ipynb` (13 cells; JSON and strict nbformat validation pass).

The notebook analyzes the 26,369-leg dataset and preserves its original historical baseline. Its local uncommitted Markdown distinguishes the legacy split from the current master split, includes master counts/date boundaries, and warns against presenting B01 legacy metrics as B02 held-out evaluation. The update did not alter notebook code or outputs.

## Day 2 — Delay prediction

**Deliverables:** `notebooks/B02_xgboost_day2.ipynb`, `models/residual_xgb_plain_master_split_v1.json`, `experiments/day2/master_split/`, and `data/processed/preds_cal_test_master_split_v1.csv`.

The model card describes a lane-median baseline plus a residual XGBoost correction trained on the master training partition, internally divided into fit/validation. Calibration and test are separate. Its ten features are OSRM time/distance/speed, log OSRM time, departure hour/day/weekend, FTL indicator, lane baseline, and lane-history count. No weather feature is in the primary model. Outcome history is limited to previously completed legs; current-leg actual time and delay ratio are not model features.

The saved prediction file has 8,695 rows: 4,301 calibration and 4,394 test. Its SHA-256 is `5165f4027afea3491f5be01d6d5d22a1b4318ff486270eb9efa70bc1a8777eb4`. Recomputed from its test rows, residual XGBoost MAE/RMSE are `0.653957215972931` / `1.727802656778531`; lane-history baseline MAE/RMSE are `0.6686060922605898` / `1.737589550840338`. These values were checked from saved predictions, not by retraining.

## Day 3 — Conformal intervals

**Deliverables:** `notebooks/B03_conformal_day3.ipynb` and `experiments/day3/master_split_v2/`.

The run manifest and success marker state `complete`, identify the saved prediction export as input, and report 4,394 test rows / 2,424 test trips. Method C grouped by route type and distance has empirical test coverage:

| Nominal level | Covered test legs | Empirical coverage | Trip-bootstrap 95% interval |
|---|---:|---:|---:|
| 50% | 2,028 / 4,394 | 46.1538% | 44.6%–47.7% |
| 80% | 3,411 / 4,394 | 77.6286% | 76.4%–78.9% |
| 90% | 3,904 / 4,394 | 88.8484% | 87.9%–89.8% |

Coverage was recomputed from the saved test intervals joined one-to-one to test labels on trip, lane, route, and departure-time keys. Coverage is leg-level held-out coverage; 88.85% is not nominal 90% and says nothing about lane-day coverage. The results do not establish a formal lane-aggregate interval guarantee.

## Day 4 — Cascade analysis

**Current authoritative artifacts:** `notebooks/B04_cascade_day4_final_v3.ipynb`, `experiments/day4/final_v2/`, and `docs/cascade_rules_v1.md`.

The analysis is a structural stress abstraction, not an operational forecast. It symmetrizes the 292 directed lanes for load redistribution, uses a 14-day outgoing-departure baseline (2018-09-12 through 2018-09-25, including zero days), and uses the ceiling of per-hub linear p95 outgoing departures as a dispatch-capacity proxy. It redistributes the entire accumulated scalar load using spare room, with a capacity-proportional fallback. It does not preserve OD flows, direction, or reroute only excess traffic; receiving capacity is not measured.

Read-only checks found final-v2 output hashes matching the manifest, the `_SUCCESS_v1.json` manifest hash matching the manifest file, and the figure/log hashes matching. Row counts are 100 real-data scenarios, 1 critical-hub scenario, and 44 synthetic stress scenarios. These are saved-artifact checks; the notebook was not re-executed.

Historical Day 4 files and the prior notebook are retained in the active worktree and Git history. They contain intermediate unit/capacity experiments, per-hub results, centrality comparisons, and validation material. Do not combine them with final_v2 results as if they were comparable runs.

## Day 5 — Risk table and realized test output

**Deliverables:** `notebooks/B05_risk_table_day5.ipynb`, `models/day5_final_pipeline.py`, the 296-row representative source `experiments/day5/risk_table_master_split_v1.csv`, and the versioned final outputs listed below. The representative source covers 292 lanes; four lanes have two route rows.

The canonical expanded risk table is `models/outputs/risk_table.csv`. It has one row for each of the 292 directed core lanes and includes `baseline_ratio`, `pred_ratio`, `lo50`, `hi50`, `lo90`, `hi90`, and their baseline-relative multipliers. Compatibility aliases (`lane_base`, `base_source`, and `mult_*`) are retained in the expanded table. `models/outputs/risk_table_lane.csv` is the preserved earlier 10-column output used by the appended C1–C5 notebook cells; it was not overwritten.

The earlier `models/outputs/risk_table_lane.csv` has 292 unique directed lanes and columns:

```text
source_center,destination_center,lane_base,base_source,n_train_legs,
mult_pred,mult_lo90,mult_hi90,mult_lo50,mult_hi50
```

`baseline_ratio` is the median observed `delay_ratio` for the directed lane using master-training legs only when at least three lane observations exist. Sparse-lane fallbacks are training-only route-type × training-distance-tercile median, then the global training median. All 292 current core lanes have sufficient training history and use the lane median. The output `pred_ratio` and interval endpoints are weighted arithmetic means over representative lane-route rows, weighted by `representative_training_legs`; multipliers are the corresponding values divided by `baseline_ratio`. Averaged endpoints remain proxy intervals, not formal mixture intervals or lane-level conformal guarantees.

The current B02 model is the saved residual XGBoost model (XGBoost 3.2.0 parity assertion; best iteration 134). Its features are `osrm_time_min`, `osrm_distance_km`, `osrm_speed_kmh`, `log_osrm_time`, `start_hour`, `start_dow`, `is_weekend`, `is_ftl`, `lane_base`, and `lane_history_count`. It is fit on 14,073 legs from 7,975 trips in the first 80% of master-training trips (trip creation dates 2018-09-12 00:00:16 through 2018-09-22 23:54:08); 3,601 legs from the later 1,994 training trips form its validation partition (2018-09-22 23:54:45 through 2018-09-25 23:58:48). Calibration and test trips are excluded from model fitting. Saved B02 predictions are per leg. B05 representative predictions are scored at the 2018-09-29 00:00 feature cutoff from training-only lane-route representative features, then reduced to one lane row by the weighted aggregation above. The saved prediction export contains actual test labels for evaluation; labels are not model inputs. The interval offsets use calibration rows, however, and are an offline held-out evaluation artifact rather than information available at that earlier feature cutoff.

B03 Method C uses signed residual offsets grouped by route type × calibration-distance tercile, with groups below the saved minimum group size falling back to global calibration offsets. This remediation independently reproduced its offsets from the 4,301 calibration legs and verified the saved test interval bounds. On the official 4,394 test legs, 50% intervals covered 2,028 (46.1538%; mean width 0.561920 ratio, 33.8259 minutes) and 90% intervals covered 3,904 (88.8484%; mean width 2.809186 ratio, 164.8442 minutes). These are leg-level results; the test coverage does not imply lane-average coverage. Among observed test lanes with at least five legs, the descriptive mean of lane-level 90% coverage was 88.16% across 187 lanes. This is not a lane-level conformal guarantee. The split is chronological by trip creation, but 329 calibration-leg outcomes finish after the earliest test-leg start; therefore the static intervals are a held-out trip-partition evaluation, not a per-test-time online calibration guarantee.

The model versus fixed training-only lane-history baseline comparison uses the same 4,394 official test legs. Missing or fewer than three lane training observations fall back to the training route-type × training-distance-tercile median, then global training median. The model achieved MAE/RMSE `0.653957` / `1.727803`; the baseline achieved `0.729950` / `1.934731`. Predictions were present for all 4,394 legs and all 1,547 test lanes. No test outcome was used to calculate the baseline. This fixed training-only baseline differs from the model card's `0.6686` test baseline, which uses B02's as-of prior-history feature (training plus already completed calibration legs).

The legacy `data/processed/preds_test.csv` is not a current official test export: it has 5,307 rows and 2,964 unique trip IDs; 540 IDs (913 rows) map to calibration, zero official test IDs are missing, and its first row is dated 2018-09-28. It has 3,558 rows belonging to repeated trip IDs (2,343 extra ID occurrences), but no duplicate leg keys. The current authoritative B02 `pile=test` has exactly 4,394 official test leg rows and 2,424 test trips, with zero group violations and zero duplicate leg keys; its repeated trip IDs are expected because trips can contain multiple legs (1,970 extra trip-ID occurrences). The B02 model card and master-split pipeline use `data/processed/split_trip_ids.csv`; the mixed legacy export was not used for training, calibration, or these evaluations. A clean test-only copy is `data/processed/preds_test_master_split_v1.csv`.

`models/outputs/realized_test_lane_master_split_v2.csv` is the complete official-test realization over all 292 core lanes. It contains test leg/trip counts, mean realized delay ratio, test date bounds, and realized multiplier; 66 lanes have zero test legs and therefore blank realized values. It is evaluation-only. The prior `models/outputs/realized_test_lane.csv` remains unchanged as the earlier 93-lane thresholded output (at least five test legs); it is not the complete all-lane table. The full result is versioned rather than replacing that appended C1–C5 output; promoting it to the unversioned filename requires Person C agreement.

`models/outputs/day5_test_interval_coverage_master_split_v1.csv`, `models/outputs/day5_lane_test_metrics_master_split_v1.csv`, and `models/outputs/day5_model_vs_baseline_master_split_v1.json` hold the reproducible evaluation summaries. `models/outputs/day5_final_manifest_master_split_v1.json` records input and output hashes.

| Output | SHA-256 |
|---|---|
| `models/outputs/risk_table_lane.csv` | `d32af6b38157cb9ecd4a99214b9fba39c0fdc4b2b7a7a87d98e0302439990d7e` |
| `models/outputs/realized_test_lane.csv` | `8a844d81dbe5bd58513ff6ae4d8d931bb6848c15ab1cfa1cf777775a50b36b84` |

The new versioned artifact hashes are recorded in `models/outputs/day5_final_manifest_master_split_v1.json`; the versioned full 292-lane realization and the expanded canonical risk table do not overwrite the earlier outputs above.

The two original files remain unchanged and their hashes match the earlier saved artifacts. The expanded `risk_table.csv` has no duplicate lanes, covers the exact core lane set, and satisfies interval ordering checks. The previous thresholded realized table remains unchanged; a separate complete versioned realization was generated and validated from official test rows.

### Exploratory weather cells

Cells 12 and 14 were corrected locally: missing `rain_mm` remains NaN, missing target rows are excluded, features are not zero-imputed, and the Random Forest comparison is labeled in-sample/exploratory and not a held-out result or input to the primary model/table. The old outputs were cleared because they reflected the prior imputation code; their previous notebook version remains in Git at `c968251`. A tiny in-memory check in the project venv confirmed its scikit-learn 1.7.2 RandomForest accepts NaN.

Cell 15 remains explicitly unresolved and unexecuted. `merged_train` contains per-leg `osrm_distance_km` and `actual_time_min`; the cell asks for lane-level `distance_km` and `median_actual_time`. Substituting per-leg actual time is invalid and can leak the target. Joining `core_edges` summaries to the same rows used for in-sample scoring would also reuse those rows’ outcomes in their own aggregate feature. A valid experiment would need an as-of/leave-out feature construction or a separate later evaluation population. This cell does not participate in the lane-risk output.

The current venv is not an exact match for `requirements.txt`: XGBoost is 3.2.0 (matches the notebook parity assertion), but scikit-learn is 1.7.2 rather than pinned 1.9.1, pandas 2.3.3 rather than 3.1.0, and NumPy 2.2.6 rather than 2.4.6; nbformat is absent from the venv. Strict notebook validation was performed with the system Python’s installed nbformat, not by installing packages. No dependency was installed.

## Person B code and deliverable inventory

- `sim/simulate.py` contains Person B’s static `simulate_cascade` implementation and `simulate_scenario` plan evaluator. Its documented cascade rules are consistent with the inspected implementation.
- `sim/simulator.py` is Person A-owned; `opt/` optimizer implementation is Person C-owned. They were not modified.
- `models/risk.py` does not exist in this repository, and no tracked source or documentation references that path. The risk-table workflow is currently in B05. No separate module was created because no standalone API contract was found.
- No SHAP deliverable or explicit SHAP requirement was found in the tracked project files searched. No SHAP output was invented. B06 is the existing interface/demo notebook; it demonstrates a toy in-memory adapter, not a production integration.

## Day 6 integration interface and blockers

`notebooks/B06_day6_optimizer_simulator_interface_v2.ipynb` documents the current contract gap. `opt/c_multiflow.py::solve_multiflow` returns total cost and unmet demand but discards the per-OD flow vector. `sim/simulator.py` accepts only a single-OD plan mapping. B06’s multi-OD adapter is a toy, in-memory proposal and is not installed in either implementation. The real 292-commodity workflow was not run.

The B06 notebook also records unresolved input/objective semantics: optimizer demand counts 5,395 training legs while the simulator’s 14-day departure input counts 5,357 legs (38 legs across 28 lanes); unmet penalty values differ (96 hours in optimizer/tests, 48 in `docs/c_notes.md`, default 20 in the queue simulator); closure and failed-hub behavior differ; and waiting cost is time-horizon dependent. B06 does not directly read either `models/outputs/` Day 5 CSV. Therefore there is no verified production B05-to-B06 risk-table adapter yet.

**Required teammate action:** Person C must decide how the optimizer exposes per-OD flows and demand/unmet values; Person A must review multi-OD queue input and closure/failure semantics. Person B should not change those files without their approval.

## Validation record

| Check | Result |
|---|---|
| Strict JSON / nbformat validation of all 11 notebooks | PASS |
| AST parse of Python sources in `src/`, `sim/`, `models/`, `opt/` | PASS |
| Imports `sim.simulate`, `sim.simulator` | PASS |
| `opt.c_multiflow` imported as a package from repository root | FAIL: its bare `import c_real_graph` is not resolved in that invocation. B06 documents this packaging issue; Person C owns the module. |
| B05 changed cells 12, 14, 15 compile without execution | PASS |
| B05 cells 17–21 (C1–C5) source and stored outputs unchanged by this repair | PASS |
| `git diff --check` | PASS |
| Master split disjointness, counts, target formula comparison | PASS |
| B03 held-out coverage recomputation | PASS |
| B04 output, figure, log, manifest, success-marker hashes | PASS |
| B05 risk/realized row counts, schemas, lane set, ordering, hashes | PASS |
| Day 5 final pipeline: split membership, calibration-only offsets, coverage, training baseline, evaluation and output hashes | PASS (initial `.venv/Scripts/python.exe models/day5_final_pipeline.py --write`; corrected version refreshed only after prior-manifest hash checks; final independent `.venv/Scripts/python.exe models/day5_final_pipeline.py --check`) |
| Full notebook execution and model training | NOT RUN |
| Versioned Day 5 output generation | RUN: versioned exports and evaluations generated by `models/day5_final_pipeline.py`; prior committed outputs were preserved |
| `sim/test_core.py`, `sim/test_toy.py` | NOT RUN: their `main()` functions write experiment CSVs, including existing Person A/C outputs. |

Useful commit references: B02 `6b70885`; B03 `0b4e435`; B04/Day 6 work `4bfda48`; Day 5 artifacts `c968251`. Current B01/B05 documentation and exploratory-cell edits, plus the final pipeline source and versioned outputs, are uncommitted.

## Reproduction and preservation notes

- Treat the saved manifests/success markers and hashes above as the reproducibility record for the existing B02/B03/B04 artifacts. No model was retrained and no B03 or B04 outputs were regenerated. New versioned Day 5 exports/evaluations were generated and their inputs and outputs are hashed in the final Day 5 manifest.
- The original B05 notebook uses exclusive-create (`"x"`) guards for its representative and original lane outputs. Do not rerun its output-writing cells over existing files. For a clean Windows copy with final-output paths absent, run `.venv\Scripts\python.exe models/day5_final_pipeline.py --write` once; use `.venv\Scripts\python.exe models/day5_final_pipeline.py --check` for subsequent in-memory reconstruction and byte/hash checks. `--write` refuses existing paths; `--refresh-generated` can replace outputs only when each existing file matches this pipeline's prior manifest.
- B04 final_v3 writes its versioned final_v2 package with exclusive-create semantics. Reproduce in a clean isolated copy; do not overwrite the checked final package.
- `src/make_split.py` writes `data/processed/split_trip_ids.csv`; do not rerun it against the authoritative split without an explicitly approved rebuild plan.
- Historical artifacts remain in the repository; no archive or deletion is pending from this handoff.
- `pred_excess_h` is defined in B05 as `(pred_ratio - 1) * osrm_time_h`, where `osrm_time_h = osrm_time_min / 60`; it is excess over OSRM reference duration in **hours**. It is not calculated from `core_edges.median_actual_time`. That source field is a median of `actual_minutes` and is therefore in minutes; using it in the same formula would produce minutes. Predicted total time is `pred_ratio * OSRM_time_h`; excess is the difference between predicted and OSRM reference time, so do not add the excess to predicted total time a second time.

## Current publication checkpoint — 2026-11-13

This note supersedes only forward-looking status statements above; earlier audit snapshots, experiment results, and dated records remain historical.

- **Prediction API:** the isolated-worktree suite completed with 8 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_prediction_api -v`.
- **SHAP:** the isolated-worktree suite completed with 9 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v`. The 4,394 × 11 native XGBoost contribution run has maximum additivity error `5.270703695714474e-07` at `1e-6` tolerance and explains the residual prediction, not final `pred_ratio`.
- **Synthetic demo:** `models/person_b_demo.py` is already published on `person-b-prediction-cascade` in commit `8e4e4346b3ea1ec4fb4c7065b6b4e0ed16190e84`. It uses only the synthetic H1–H8 fixture; this does not approve release of production data.
- **B05:** cell 15 is an explanatory Markdown note excluding the invalid lane-feature duplicate; cell 14 remains an in-sample exploratory comparison, and weather availability as of departure is unestablished. The notebook was not executed; cell 21 and its stored output were preserved.
- **Day 6:** the approved demand is 5,395 master-train core legs / 14 days; 5,357 remains informational. The destination simulator source still describes one edge as one day and does not expose `scenario["travel_time_multipliers"]`, so duration-aware end-to-end integration is not verified. The two plan snapshots and their hashes are reconciled in `docs/person_b_final_handoff_v1.md`; Person C confirmation of the candidate's wrapper and provenance remains pending.
- **Release:** trip-level predictions, outcomes, intervals, and SHAP contribution rows remain `INTERNAL_ONLY`. Lane-level risk/realized tables and local SHAP explanations/plots require owner approval. The B05 notebook contains stored row-preview and lane-level outputs, so its edited notebook remains release-gated; no standalone generated result CSVs are included in this prepared bundle.
