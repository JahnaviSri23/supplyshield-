# Person B Independent Work Handoff

**Audit date:** 2026-11-12
**Branch snapshot:** `day6-integration-solo` at `c968251`
**Scope:** independent Person B work only. This document records verified artifacts,
checks performed for this handoff, and work stopped at missing dependencies or
specifications. It does not certify the local Day 6 A/C code proposals.

> **Subsequent status clarification — 2026-11-12:** This document is a point-in-time audit; its statements below that SHAP or a standalone Prediction API did not exist describe that earlier inspection. Both deliverables now exist. The Prediction API suite passed 8/8 in the existing `.venv`. SHAP 0.49.1 is installed; explainability uses native XGBoost TreeSHAP after `TreeExplainer` failed on the vector-valued base score. The saved native run produced 4,394 × 11 contributions and maximum additivity error approximately `5.27e-7` within `1e-6`, for the model residual output only. Current Day 6 demand is 5,395 master-train core legs / 14 days; 5,357 is the informational strict-window count. Adapter preparation is not end-to-end integration: it must later align with A's `scenario["travel_time_multipliers"]` interface, and A's final simulator and C's frozen plan remain pending.

## Verified prediction and interval artifacts

The official split at `data/processed/split_trip_ids.csv` was checked against
`data/processed/legs.csv`. It contains 9,969 train, 2,424 calibration, and 2,424
test trips; mapping the 26,369 leg rows gives 17,674 train, 4,301 calibration,
and 4,394 test legs. No leg IDs are unmapped and no trip IDs overlap across
partitions.

The saved model is `models/residual_xgb_plain_master_split_v1.json`. Its model
metadata records ten ordered features and best iteration 134. The model card
identifies the model as a plain residual XGBoost model. Its explained model
output, if an explainability run is later completed, must be described as the
residual prediction; the B02 final ratio prediction is the lane-history base
prediction plus that residual.

The saved master-split prediction export has 8,695 calibration/test rows, and
the test-only export has 4,394 rows. Day 3 Method C artifacts are marked
complete; the saved test interval table has 4,394 rows. Reported held-out
coverage is 46.15%, 77.63%, and 88.85% at the nominal 50%, 80%, and 90% levels.
These are leg-level trip-partition results, not lane-level guarantees or
per-test-time online calibration guarantees.

The expanded `models/outputs/risk_table.csv` was checked against
`data/processed/core_edges.csv`: 292 rows, 292 unique directed lane keys, exact
lane-set equality, no duplicate keys, and no missing values. Its SHA-256 is
`051d71563f540df4869d4a2bd59dea38c5c2f173c47974f47629674ceffb53d7`, matching
`models/outputs/day5_final_manifest_master_split_v1.json`. The 296-row
representative source describes route-level representatives; the expanded
table contains one row per core lane.

`python models/day5_final_pipeline.py --check` performs an in-memory
reconstruction and compares saved outputs byte-for-byte; it does not train the
model or write outputs. It was run for this handoff and passed: all saved
versioned outputs matched the in-memory reconstruction byte-for-byte.

## Explainability status

SHAP was not available in the repository `.venv` (`importlib.util.find_spec`
returned `None`), and `requirements.txt` does not list SHAP. No package was
installed, no feature-importance result was calculated, no SHAP value was
computed, and no explainability experiment folder or figure was created.
Therefore there are no explainability results to interpret or claim as
validated.

The supplied protocol is suitable for a future run once the dependency is
available: explain the residual model on all eligible official test legs, use
only official training legs as the background, and exclude calibration legs
from both populations. Do not explain `pred_ratio` as though it were the model
output: it also includes the lane-history base prediction. Before saving
results, reconstruct the exact B02 feature matrix in saved model feature order,
compare final predictions against saved inference predictions, verify SHAP
dimensions and finite values, and test additivity where supported. Do not treat
feature effects as causal. The SHAP version and deterministic runtime settings
must be recorded; do not silently sample either population.

## Prediction API status

No standalone Person B prediction API wrapper was found. B02 notebook code
defines feature construction and inference; `models/day5_final_pipeline.py` is
an artifact reconstruction/check pipeline, not a request-facing API. No
`models/risk.py` was created because the external input contract is unspecified.

The B02 feature logic is recoverable at notebook level: eight raw derived
features plus `lane_base` and `lane_history_count`; lane history is restricted
to outcomes completed by each leg's departure time. The final ratio prediction
adds the saved residual-model output to the base. Method C intervals also need
route type, OSRM distance, the saved calibration grouping/offsets, and
well-defined missing/unknown-group handling.

An API requires a Person B contract decision for: single-row versus batch
requests; required raw columns and types; where eligible history comes from;
how history is filtered as-of departure; missing/invalid field behavior; and
whether the response contains residual, base, final ratio, intervals, or all of
them. Once specified, test exact feature order and prediction parity against
the saved B02 rows and conformal bounds. Until then, do not present a partial
wrapper as production-ready.

## Independent cascade validation

Person B's structural cascade is implemented in `sim/simulate.py` and scoped in
`docs/cascade_rules_v1.md`. The exact H1–H8 fixture and assertions in cell 1 of
`notebooks/B04_cascade_day4.ipynb` were executed in memory against
`build_neighbors` and `simulate_cascade` on 2026-11-12. Four test groups passed:
the calm H4 failure, the overloaded H4 network collapse, the 1.1 tolerance
case, and single-hub conservation. All eight single-hub conservation checks
passed. In the collapse case, all eight hubs failed in four rounds and 570
load units were unserved, matching the fixture assertions. The notebook was
not executed.

This validates the structural scalar-load model only. It does not establish
operational OD rerouting, measured receiving capacity, or approval of
Person A/C queue/optimizer integration.

## Interactive demonstration readiness

Person B can demonstrate the existing H1–H8 structural cascade with its saved
fixture and `sim/simulate.py`, without A/C code. No interactive application
was found or built. A demonstration using the project core would need to label
`core_nodes.csv` capacities as dispatch-throughput proxies and preserve the
documented B04 structural assumptions. An operational optimizer-to-queue demo
depends on approved Person A and Person C interfaces and is out of scope until
those owners approve their respective changes.

## Day 6 ownership and handoff status

Local changes to `sim/simulator.py` (Person A) and `opt/c_multiflow.py` (Person
C) were already present before this work and were not modified here. The
untracked Day 6 integration adapter and outputs consume those local proposals;
the existence of a completed local run does not constitute A/C approval.

The local Day 6 documentation is inconsistent: `docs/day6_integration_handoff.md`
describes a completed local integration, while
`docs/person_b_day1_day5_handoff.md` and portions of
`notebooks/B06_day6_optimizer_simulator_interface_v2.ipynb` still describe the
integration as blocked or proposed. Reconcile those descriptions with the
owners before calling the integration accepted. No A/C-owned files or prior
handoff documents were changed for this work.

## Reproduction and limits

- Day 5 output parity: `python models/day5_final_pipeline.py --check` (read-only
  check; no model retraining).
- The cascade check above used the existing fixture and function assertions in
  memory; it did not run a notebook or the cross-owner `sim/test_toy.py`.
- No SHAP, API, or interactive-demo result exists in this handoff.
- Existing Day 6 experiments are historical local integration evidence; they
  depend on unapproved A/C proposals and are not certified as an accepted team
  interface.

## Current publication checkpoint — 2026-11-13

This note supersedes only forward-looking status statements above; earlier audit snapshots, experiment results, and dated records remain historical.

- **Prediction API:** the isolated-worktree suite completed with 8 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_prediction_api -v`.
- **SHAP:** the isolated-worktree suite completed with 9 passed and 0 failed using `.\.venv\Scripts\python.exe -m unittest models.test_shap_explainability -v`. The 4,394 × 11 native XGBoost contribution run has maximum additivity error `5.270703695714474e-07` at `1e-6` tolerance and explains the residual prediction, not final `pred_ratio`.
- **Synthetic demo:** `models/person_b_demo.py` is already published on `person-b-prediction-cascade` in commit `8e4e4346b3ea1ec4fb4c7065b6b4e0ed16190e84`. It uses only the synthetic H1–H8 fixture; this does not approve release of production data.
- **B05:** cell 15 is an explanatory Markdown note excluding the invalid lane-feature duplicate; cell 14 remains an in-sample exploratory comparison, and weather availability as of departure is unestablished. The notebook was not executed; cell 21 and its stored output were preserved.
- **Day 6:** the approved demand is 5,395 master-train core legs / 14 days; 5,357 remains informational. The destination simulator source still describes one edge as one day and does not expose `scenario["travel_time_multipliers"]`, so duration-aware end-to-end integration is not verified. The two plan snapshots and their hashes are reconciled in `docs/person_b_final_handoff_v1.md`; Person C confirmation of the candidate's wrapper and provenance remains pending.
- **Release:** trip-level predictions, outcomes, intervals, and SHAP contribution rows remain `INTERNAL_ONLY`. Lane-level risk/realized tables and local SHAP explanations/plots require owner approval. The B05 notebook contains stored row-preview and lane-level outputs, so its edited notebook remains release-gated; no standalone generated result CSVs are included in this prepared bundle.
