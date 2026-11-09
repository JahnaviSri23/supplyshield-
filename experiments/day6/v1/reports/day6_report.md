# SupplyShield Day 6 — Optimizer / Queue-Simulator Interface Audit

**Status: PARTIALLY COMPLETE**  
**Repository:** `C:\Local\Documents-Local\ML Project\supplyshield--1`  
**Branch / HEAD at audit:** `person-b-prediction-cascade` / `0b4e435b462ed67ca683077b9f64e5835817f91f`  
**Execution environment:** repository `.venv`, Python 3.10.8, NumPy 2.2.6, SciPy 1.15.3, NetworkX 3.4.2, pandas 2.3.3, ipykernel 7.3.0.

## 1. Objective and scope

Day 6 examines a per-OD optimizer plan interface for the daily queue simulator. The single authoritative notebook is `notebooks/B06_day6_optimizer_simulator_interface_v2.ipynb`; useful explanations and results from prior B06 drafts were consolidated into it, and execution output is saved in that same notebook. Deterministic toy validations and the existing single-OD toy test were run. No real-network optimization was run.

## 2. What was inspected

- The prior Day 6 notebook content and its saved outputs, compared cell-by-cell with the authoritative notebook before consolidation.
- `opt/c_multiflow.py`, `opt/c_real_graph.py`, `opt/c_toy_recovery.py`.
- `sim/simulator.py`, `sim/simulate.py`, `sim/test_toy.py`, and `sim/test_core.py`.
- `docs/c_notes.md`, `docs/assumptions.md`, B04 final_v2 manifest/results, and B05 master-split risk table/manifest/success marker.
- Relevant master-split/core files and current dependency metadata.

## 3. Interface findings

### Current optimizer

`opt/c_multiflow.py::build_model` creates one commodity for each directed core edge, with daily demand `core_edges.trips / 14`. `solve_multiflow(G, closed=None)` optimizes per-commodity edge variables, shared outgoing hub capacity, and unmet demand. `closed` accepts one directed edge. Finite shared edge capacities and hub-failure scenarios are not included in the LP. The solver discards the per-OD decision variables and returns only `(total_cost, unmet)`, so it cannot currently emit a simulator plan.

### Current queue simulator

`sim/simulator.py::simulate(graph, scenario, plan=None)` expects a directed, non-multigraph NetworkX graph. Graph metadata includes `graph.graph["demands"] = {(origin, destination): legs_per_day}`; nodes need `cap` and may include `buffer`; edges need `cost` and may include `cap` (default unlimited). Scenario fields include `demand_days`, `horizon`, `failure_start`, `failure_days`, `capacity_scale`, and `failed`. Results include generated, delivered, unmet, shipping cost, waiting cost, total cost, recovery metrics, and daily history.

Its current `_routes` accepts `plan=None` or one OD's `{(u,v): flow}` mapping. It rejects multi-OD plans. The static evaluator `sim/simulate.py::_normalize_plan` accepts nested `{od: {edge: flow}}` maps or records shaped `{"od":[o,d], "edge":[u,v], "flow":legs_per_day}`; that support is not the queue simulator API.

### Proposed contract demonstrated on toy data

The B06 v2 notebook defines a plan envelope containing explicit `demands`, nested per-OD `flows`, per-OD `unmet`, `closed_lanes`, units, and solver provenance. Its serializer emits the existing OD-edge-flow record shape. The queue adapter in the notebook is **in-memory only** and calls the real queue simulator's existing single-OD route decomposer once per commodity. It is not installed in `sim/simulator.py`.

The v2 validator checks demand agreement, finite nonnegative flows/unmet, per-OD flow balance, delivered-plus-unmet accounting, aggregate shared hub and edge capacities, closed lanes, and route decomposition. Additional checks reject non-finite unmet values, a shared-edge overload, and a balanced cycle. It also exercises zero demand, a failed origin, and a zero-capacity final destination.

## 4. Experiment setup and results

### Single authoritative Day 6 notebook

The final notebook is `notebooks/B06_day6_optimizer_simulator_interface_v2.ipynb`. The earlier draft used `closed` instead of the documented `closed_lanes` field, so its saved 19/19 count did not validate the stated closure contract. The authoritative notebook carries the corrected field, expanded invariant table, ownership and decision context, and stronger checks for NaN unmet values, shared edge capacity, and cycles.

All **9 code cells** were executed sequentially in memory under the repository `.venv`, with no errors; the corrected checks reported **26/26 passed**. The notebook has no magics or `display()` calls. Standard `nbformat`/`nbclient` execution was unavailable because `nbformat` is not installed in `.venv`; no package was installed. Outputs are stored in the authoritative notebook itself. The `_routes` monkey-patch was restored in `finally`, and the notebook output confirms restoration.

Toy multi-OD results use 5 days of 12 legs/day total:

| Scenario | Delivered | Unmet | Shipping | Waiting | Queue total |
|---|---:|---:|---:|---:|---:|
| S0, no closure | 60 | 0 | 290 | 0 | 290 |
| S1, lane H1→D closed | 60 | 0 | 360 | 0 | 360 |
| S2, H1→D and A→D closed | 55 | 5 | 355 | 4,560 | 5,395 |

For S0–S2, simulator shipping equals the toy LP travel cost multiplied by five demand days. This is **shipping-component parity only**. The queue adds waiting cost; S2's total is horizon-dependent and is not equal to the LP objective. The LP's S2 per-day objective is 167 (71 travel + 96 × 1 unmet), while the queue's 40-day run totals 5,395 including waiting. `plan=None` was much more expensive on this toy graph and is not a neutral capacity-aware baseline.

### Existing single-OD toy simulator script

`sim/test_toy.py::main` completed in the same `.venv`. Its output was redirected to a temporary directory during execution, then copied to the new Day 6 output area. It produced **21 scenario rows** (7 cases × 3 capacity scales) and **3 matched comparison rows**. Every row delivered 700 with zero unmet. Recovery-plan savings under D failure were +70, +34, and −20 at capacity scales 1.0, 1.2, and 1.5; the recovery plan is not uniformly cheaper. Existing `experiments/toy_simulator_checks.csv` and `experiments/toy_simulator_comparisons.csv` hashes remained unchanged.

## 5. Data, cost, and scenario mismatches

- The optimizer's current demand totals 5,395/14 = 385.3571 legs/day from `core_edges.trips`; the queue test's in-window departure demand totals 5,357/14 = 382.6429 legs/day. They differ by 38 legs across 28 lanes. A real comparison must use one explicit, agreed demand vector.
- Lane cost medians matched in the B06 data audit. Code uses a 96-hour penalty (`opt/c_real_graph.py` and `sim/test_core.py`); `docs/c_notes.md` says 48 hours; queue default is 20. The toy notebook explicitly uses 96, but this does not establish a project-wide canonical penalty.
- The LP has no waiting cost. The queue accumulates waiting cost per leg-day, so total cost changes with the horizon when demand remains queued/unmet.
- The optimizer supports one lane closure; the queue has no lane-closure scenario field. The toy adapter represented closure by a zero-capacity edge on a graph copy, which is a permanent closure for that simulation.
- Queue failures are temporary node-capacity multipliers and currently block transfers both into and out of a failed node during the failure window. The optimizer does not optimize around failed hubs.
- `sim/simulate.py::simulate_scenario` and the queue simulator disagree on zero-capacity destination-only hubs: the static evaluator reports demand unmet when destination capacity is zero, while the queue simulator permits final delivery without destination dispatch. Queue buffers are assumed storage, not measured receiving throughput.

## 6. Tests and skipped work

- **Passed:** corrected B06 toy validation, 26/26 checks; current single-OD toy simulator script, 21 scenarios and 3 comparisons, all internal assertions completed.
- **Not run:** `sim/test_core.py::main` because it runs the real 100-hub/292-lane core and writes existing `experiments/core_simulator_*.csv` outputs. The real optimizer was not run for the same real-network and output-preservation reasons.
- **Not run:** pytest. The two existing `sim/test_*.py` files are executable `main()` scripts rather than pytest test-function suites.
- **Not run:** real-network LP, real-network plan evaluation, package installation, and live remote fetch.

## 7. Files created and preservation

Created by this Day 6 run:

- `notebooks/B06_day6_optimizer_simulator_interface_v2.ipynb` (single authoritative notebook; execution outputs stored in place).
- `experiments/day6/v1/toy_network/toy_simulator_checks.csv`.
- `experiments/day6/v1/toy_network/toy_simulator_comparisons.csv`.
- `experiments/day6/v1/logs/toy_test_run.txt`.
- `experiments/day6/v1/reports/day6_report.md`.
- `experiments/day6/v1/manifests/run_manifest.json`.

The superseded B06 v1 notebook and separate executed copy were removed after content/result consolidation and final notebook validation; their pre-removal hashes are recorded in the Day 6 manifest as historical consolidation metadata. No other Day 6 notebook duplicate was found.

**Project-wide notebook rule:** maintain one authoritative notebook per task; make corrections in place; create another notebook only for a genuinely separate task or when explicitly requested; keep experiment outputs separate, preserve useful prior results, and never overwrite existing experiment results.

No B01–B05 notebook, model, dataset, or authoritative experiment output was modified. No teammate-owned source file was changed. The B04 final_v2 manifest hashes still match for `sim/simulate.py` and both hashed documentation inputs. B05 risk-table SHA-256 still matches its manifest and success marker. The two pre-existing toy output CSV hashes remained unchanged. No real-network or optimizer experiment was run. Git was used only for read-only status/branch/HEAD inspection; no Git state-changing operation occurred.

## 8. Remaining work and proposed teammate changes

1. **Person C / optimizer owner:** expose the solver's per-commodity edge variables, unmet rates, travel term, demand vector, closure context, units, and provenance. Preserve `solve_multiflow(G, closed=None)`'s current two-value return by factoring the solution extraction into a plan-returning helper and keeping the old function as a compatibility wrapper. This changes only API availability if the LP formulation/objective stays the same; it must be reviewed and regression-tested by the owner.
2. **Person A / queue simulator owner:** extend `_routes` to accept the multi-OD nested map or OD-edge-flow records, call the existing single-OD decomposition per commodity, and keep the current single-OD dict behavior. This affects route assignment only; flow accounting, buffer behavior, and failure semantics need owner tests.
3. **Team decisions before real-network execution:** select the authoritative demand vector; settle 48 vs 96 unmet penalty and queue defaults; define whether closures are single/static or time-varying; decide whether optimizer plans need hub-failure constraints; align zero-capacity destination semantics for the intended evaluator.

Toy-network success is not real-network validation. Day 6 is **PARTIALLY COMPLETE**, not complete, until owners review/apply the interface changes, assumptions are agreed, and approved regression plus real-network validation succeeds.

## 9. Reproduction notes

- Open and run the authoritative Day 6 notebook with the `.venv` Python 3.10.8 kernel. The current `.venv` does not contain `nbformat`, and its installed NumPy/SciPy/NetworkX/pandas versions differ from `requirements.txt`; no installation was performed.
- `sim/test_toy.py` writes into `experiments/toy_simulator_*.csv` when run normally. The saved Day 6 run redirected its output root to temporary storage to avoid overwriting those existing files.
- Do not run `sim/test_core.py` or the real `opt/c_multiflow.py` until demand, penalty, and plan-interface questions are resolved and real-network execution is approved.
