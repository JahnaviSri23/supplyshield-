# Person B Day 6 Extended 120-Day Report - provisional

## Simulator provenance and configuration

The verified run imported simulator commit `893a82a7fa731b95d97de8486cfa8ad59a848f38`, with CRLF-copy byte hash `3c8a9f82347594638301c18c45506186e56c903dc088070c3093d2d59b767204`; the committed LF blob has SHA-256 `bd8065b993475d280ae3f55ea3a11df7fbe2b5dfa5b99688fe613f9fcd953320`. The wrapper evidence asserts that the import path is inside the isolated root and hashes the imported bytes before running. The 40-day reproduction was byte-identical to the v2 summary; the h120 manifest records 40 calls at horizon 120. The original recorded CRLF simulator bytes are reproducible from the named git commit, so the simulator bytes and commit provenance are verified. Separately, the four copied `h*.json` reproduction manifests record a historical wrapper SHA, not the packaged `run_extended.py` SHA; those manifests are historical and must not be attributed to the exact packaged script. The README documents that SHA discrepancy. A fresh checkout also lacks the exact-hash `models/outputs/risk_table.csv` required by `prepare_isolated.py`; it is present only as local untracked input here, so reproduction is not self-contained from a clean checkout. The current helper `models/day6_extended_runner.py` has raw SHA-256 `70782429bc288c758fbb4fc28abd76ec08c8d66de6b8bb2a924653d90d8c4153` and LF-normalized SHA-256 `541fe0b62eded21876cb637009e1fbc8fea0ecd9935bb90c8429f30578a858f3`; neither matches the historical wrapper SHA-256 `50495f1d9ca4bed104718f64a044d5f056cdde50304b6d24ccfa94f8920641e8`, so the current helper is not proven to be the exact historical run wrapper.

Frozen plan SHA-256: `f588d41116e69cf00e71f8602ee6f98919140143fa10ec50a63c15a5a99c435a`. Configuration: **14 demand days / 14-day closure / 120-day horizon = a simulator-side assumption owned by A and B, approved provisionally by A and C.** Penalty 96.0. Both waiting rates are reported with equal prominence: **1.0, as executed**; **24.0, unit-consistent rerun with the same simulator, not the costs of the original execution**. The waiting-rate decision belongs to A and B; C approved reporting both rates. Instructor approval remains pending.

## Pricing-independent recovery and unmet results at horizon 120

These metrics are reported before cost results because they do not depend on the waiting-rate choice. Unmet percentage is total unmet legs divided by total generated legs for the ten scenarios in that strategy.

| Strategy | Runs | Recovered | Censored | Recovery days min | Median | Mean | Max | Unmet legs | Unmet % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| do nothing | 10 | 0 | 10 |  |  |  |  | 770 | 1.43 |
| greedy | 10 | 7 | 3 | 3.0 | 3.0 | 3.29 | 5.0 | 23 | 0.043 |
| preserve (affected flows only) | 10 | 7 | 3 | 3.0 | 3.0 | 3.29 | 5.0 | 23 | 0.043 |
| LP (all flows) | 10 | 7 | 3 | 4.0 | 4.0 | 4.14 | 5.0 | 23 | 0.043 |

## Pending versus unassigned

The instrumented simulator copy adds read-only result keys for final `pending` and `unassigned`; simulation logic is unchanged. The instrumented run imported from the isolated root, and its 40-row summary matches the verified 120-day summary in every compared column within 1e-9 (largest absolute difference: 7.28e-12). These are measured final-state values. The F2 plan-unassigned value is the sum of per-OD `expected_unmet` within each run, not the maximum OD value.

For the 19 censored runs at horizon 120, **0 of 19 have final pending > 1e-6**. All 19 have queued=0 and moving=0. Differences below are measured values minus derived/planned values, in legs.

| Scenario | Strategy | Sim unmet | Pending | Unassigned | Queued | Moving | Plan-unassigned | Pending − derived | Unassigned − plan |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L01 | do nothing | 94.000000 | 0.000000 | 94.000000 | 0.000000 | 0.000000 | 94.000000 | 0.000000 | -0.000000 |
| L01 | greedy | 5.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 |
| L01 | preserve (affected flows only) | 5.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 |
| L01 | LP (all flows) | 5.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 |
| L02 | do nothing | 93.000000 | 0.000000 | 93.000000 | 0.000000 | 0.000000 | 93.000000 | 0.000000 | 0.000000 |
| L03 | do nothing | 87.000000 | 0.000000 | 87.000000 | 0.000000 | 0.000000 | 87.000000 | 0.000000 | -0.000000 |
| L04 | do nothing | 79.000000 | 0.000000 | 79.000000 | 0.000000 | 0.000000 | 79.000000 | 0.000000 | 0.000000 |
| L05 | do nothing | 76.000000 | 0.000000 | 76.000000 | 0.000000 | 0.000000 | 76.000000 | 0.000000 | 0.000000 |
| L05 | greedy | 14.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 |
| L05 | preserve (affected flows only) | 14.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 |
| L05 | LP (all flows) | 14.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 |
| L06 | do nothing | 69.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 |
| L07 | do nothing | 69.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 |
| L08 | do nothing | 69.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 |
| L09 | do nothing | 67.000000 | 0.000000 | 67.000000 | 0.000000 | 0.000000 | 67.000000 | 0.000000 | 0.000000 |
| L10 | do nothing | 67.000000 | 0.000000 | 67.000000 | 0.000000 | 0.000000 | 67.000000 | 0.000000 | 0.000000 |
| L10 | greedy | 4.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 |
| L10 | preserve (affected flows only) | 4.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 |
| L10 | LP (all flows) | 4.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 |

**L05 / LP (all flows).** Measured unmet is 13.999999999995, final pending is 0, and final unassigned is 14.000000000000. F2 plan-unassigned sums to 14.000000000000. Per the two plan OD records, demand/day 2.285714285714 has planned flow 1.5 and residual 0.785714285714/day (11 over 14 days); demand/day 0.214285714286 has zero planned flow and residual 0.214285714286/day (3 over 14 days). Their sum is 14. The earlier v4 calculation took the maximum per-OD residual (11) instead of summing the two residuals (11+3); the 3 legs were therefore mislabeled “pending.” The direct measurement shows they are not pending.

Pinned simulator code: `sim/simulator.py:86` sets `planned = balance[source]`; lines 94 onward initialize `assigned = 0.0`; lines 114–115 append `(None, demand - assigned)` when residual is above EPS; lines 299–302 add `amount` to `unassigned` when `path is None`, while a non-null path enters `pending`. Thus these two plan residuals flow to final unassigned under the pinned code.

## Why the frozen plan leaves some demand unserved (C's explanation)

In L10, the frozen plan leaves 0.286 legs/day (4 legs over 14 demand days) unserved. C explained that this is expected LP behaviour: the multi-commodity LP reroutes only along valid active candidate corridors (k-shortest paths) and enforces the 95th-percentile hub capacity at every intermediate node. C reported 15 hubs at 100% of their daily `capacity_est` ceiling in L10; the remaining flow cannot reach its destination without violating an intermediate-hub capacity, even where downstream hubs have unused capacity. This is a limitation of the 95th-percentile hub-capacity plus candidate-path formulation. C's report was specific to L10; L01 and L05 were not separately reported by C.

B independently reproduced 15 hubs at or above 99.9% utilization for the L10 LP plan by summing planned outgoing flow across all commodities at each hub and dividing by `capacity_est`. The earlier B-side slack computation of spare capacity on rerouted-path hubs counted only affected flows rather than total hub load and is NOT used. No hub identifiers are included.

| Scenario | Strategy | Hubs >=99.9% | Five highest outgoing-flow / capacity ratios |
|---|---|---:|---|
| L10 | greedy | 5 | 1.000000, 1.000000, 1.000000, 1.000000, 1.000000 |
| L10 | preserve (affected flows only) | 5 | 1.000000, 1.000000, 1.000000, 1.000000, 1.000000 |
| L10 | LP (all flows) | 15 | 1.000000, 1.000000, 1.000000, 1.000000, 1.000000 |
| L01 | greedy | 4 | 1.000000, 1.000000, 1.000000, 1.000000, 0.928571 |
| L01 | preserve (affected flows only) | 4 | 1.000000, 1.000000, 1.000000, 1.000000, 0.928571 |
| L01 | LP (all flows) | 15 | 1.000000, 1.000000, 1.000000, 1.000000, 1.000000 |
| L05 | greedy | 4 | 1.000000, 1.000000, 1.000000, 1.000000, 0.928571 |
| L05 | preserve (affected flows only) | 4 | 1.000000, 1.000000, 1.000000, 1.000000, 0.928571 |
| L05 | LP (all flows) | 15 | 1.000000, 1.000000, 1.000000, 1.000000, 1.000000 |
### All 40 measured runs

| Scenario | Strategy | Simulated unmet | Measured pending | Measured unassigned | Queued | Moving | Plan-unassigned (F2) | Pending − derived | Unassigned − plan |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L01 | do nothing | 94.000000 | 0.000000 | 94.000000 | 0.000000 | 0.000000 | 94.000000 | 0.000000 | -0.000000 |
| L01 | greedy | 5.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 |
| L01 | preserve (affected flows only) | 5.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 |
| L01 | LP (all flows) | 5.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 | 5.000000 | 0.000000 | 0.000000 |
| L02 | do nothing | 93.000000 | 0.000000 | 93.000000 | 0.000000 | 0.000000 | 93.000000 | 0.000000 | 0.000000 |
| L02 | greedy | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L02 | preserve (affected flows only) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L02 | LP (all flows) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L03 | do nothing | 87.000000 | 0.000000 | 87.000000 | 0.000000 | 0.000000 | 87.000000 | 0.000000 | -0.000000 |
| L03 | greedy | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L03 | preserve (affected flows only) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L03 | LP (all flows) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L04 | do nothing | 79.000000 | 0.000000 | 79.000000 | 0.000000 | 0.000000 | 79.000000 | 0.000000 | 0.000000 |
| L04 | greedy | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L04 | preserve (affected flows only) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L04 | LP (all flows) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L05 | do nothing | 76.000000 | 0.000000 | 76.000000 | 0.000000 | 0.000000 | 76.000000 | 0.000000 | 0.000000 |
| L05 | greedy | 14.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 |
| L05 | preserve (affected flows only) | 14.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 |
| L05 | LP (all flows) | 14.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 | 14.000000 | 0.000000 | 0.000000 |
| L06 | do nothing | 69.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 |
| L06 | greedy | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L06 | preserve (affected flows only) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L06 | LP (all flows) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L07 | do nothing | 69.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 |
| L07 | greedy | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L07 | preserve (affected flows only) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L07 | LP (all flows) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L08 | do nothing | 69.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 | 69.000000 | 0.000000 | 0.000000 |
| L08 | greedy | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L08 | preserve (affected flows only) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L08 | LP (all flows) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L09 | do nothing | 67.000000 | 0.000000 | 67.000000 | 0.000000 | 0.000000 | 67.000000 | 0.000000 | 0.000000 |
| L09 | greedy | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L09 | preserve (affected flows only) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L09 | LP (all flows) | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| L10 | do nothing | 67.000000 | 0.000000 | 67.000000 | 0.000000 | 0.000000 | 67.000000 | 0.000000 | 0.000000 |
| L10 | greedy | 4.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 |
| L10 | preserve (affected flows only) | 4.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 |
| L10 | LP (all flows) | 4.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 | 4.000000 | 0.000000 | 0.000000 |

## Waiting-cost interpretation

C's project cost unit is leg-hours: one leg waiting one day is 24 leg-hours. The terminal unmet penalty 96 equals four days at that rate. Thus 24.0 is unit-consistent; 1.0 prices waiting at 1/24 of the unit-consistent rate. Waiting rate is a simulator parameter decided by A and B; C approved equal reporting prominence for both variants. The 24.0 results are reruns with the same simulator and are not the costs of the original execution.

Waiting cost accrues daily on queued demand and the simulator's outside-backlog accounting bucket. `unassigned` demand is not queued or retried, but this simulator counts it in that outside bucket for waiting-cost accounting. The terminal unmet penalty is applied once per undelivered leg at the horizon. Consequently, total cost for censored runs grows with horizon. In cost tables, shipping cost, waiting cost, and terminal unmet penalty are separate.

Simulator total-cost values must not be compared with C's `c_expected_*` per-day optimizer values. These quantities have different time bases.

| Waiting rate | Cost status | Cost at horizon 40 (censored runs): sum | Mean | Cost at horizon 120: sum | Mean |
|---:|---|---:|---:|---:|---:|
| 1.0 | as_executed | 657884.383333 | 34625.493860 | 725004.383333 | 38158.125439 |
| 24.0 | unit_consistent_rerun | 1304333.883333 | 68649.151754 | 2915213.883333 | 153432.309649 |

For every one of the 160 run rows (40 runs × two horizons × two rates), the identity `total_cost = shipping_cost + waiting_cost + terminal_unmet_penalty` holds. Recomputing the identity in decimal arithmetic from the CSV's 160 stored rows gives a maximum absolute residual of `2.2e-11`, below the `1e-9` comparison tolerance.

## Day-1 optimizer versus simulator

**Numerical check NOT performed; NOT DIRECTLY COMPARABLE.** C accepted the documented day-1 modelling differences. This is not a numeric parity result. Simulator totals must not be compared with C's per-day optimizer metrics.


## Required C context and limitations

C's stated assumptions: penalty 96; one-day steady-state; capacity is the 95th percentile of outgoing legs; three weeks of 2018 data; results are **NOT uncertainty-aware**. The frozen plan hash is shown above. The frozen plan commit `9a8aa89bc964a21bc286642af97ea0e9fc02dbe0` is present locally and is an ancestor of `origin/main`. Lane capacity is finite: `BIG = 10 ** 9` at `opt/c_real_graph.py:42`, and the edge builder uses `cap=BIG` at `opt/c_real_graph.py:121`. This is a large finite cap, not unlimited. Limitations: static closure representation; no per-day history for censored runs; the plan is NOT uncertainty-aware; optimizer was not rerun under the 120-day simulator; C expected metrics are per-day steady-state quantities and are not direct comparators for horizon totals. A per-lane assigned-flow check suggested by C was NOT performed: the unmodified simulator does not expose per-lane assigned flow.

## Approvals and open items

| Owner | Confirmed or pending |
|---|---|
| A | A previously confirmed the simulator commit, final interface, 120-day horizon, provisional 14/14/120 configuration, recovery definition, determinism, conservation formula, buffer rule, local-diff handling, and provisional publication. A approved reporting 1.0 (as executed) and 24.0 (unit-consistent) with equal prominence, and agreed with the pending-versus-unassigned, split-cost, finite-capacity, day-1-not-performed, and reproduction points. **A's approval remains provisional pending A's review of the actual report, CSVs, and manifests.** |
| C | Confirmed frozen plan SHA-256 `f588d41116e69cf00e71f8602ee6f98919140143fa10ec50a63c15a5a99c435a` from commit `9a8aa89bc964a21bc286642af97ea0e9fc02dbe0`, merged by C into `origin/main` (verified against local refs); 14/14/120; closure duration is an A/B assumption; both waiting rates with equal prominence. C's project cost unit is leg-hours: one leg waiting one day is 24 leg-hours, and penalty 96 equals four days at that rate. C accepted the day-1 documentation and provided the unserved-demand explanation below. |
| Pending | A's review of the pushed files; instructor release approval for lane-level tables, local SHAP, and row-level files. |

A review remains pending, so this report and its related outputs remain provisional. Instructor release approval remains pending.

## Reproduction

Reproduction uses `experiments/day6/extended_120d/repro/prepare_isolated.py` and `run_extended.py`, invoked from the repository root as shown in the README. The helper verifies the pinned simulator, frozen plan, adapter, test and inputs; the runner calls the unmodified adapter and records each call's horizon, waiting rate, reported days, timestamps and runtime. The required `models/outputs/risk_table.csv` is not tracked in this checkout; the exact hash-verified copy is a local untracked input. A clean clone therefore needs that approved input supplied before these commands can run. The legacy `models/day6_extended_runner.py` was not used. Both 1.0 as-executed and 24.0 unit-consistent reruns use the same simulator implementation.

## Hash conventions

- Adapter manifest hash is LF-normalized `74aa58245e485d318dffcd7ae686352134ead21639f61a5b0f0e6eb6968f233b`; working copy SHA-256 `168878e2c6efc1f2b65f8058efb8ceecf5eb4ca20e92223b34a79ea35ba0d0f5`; LF-normalized SHA-256 `74aa58245e485d318dffcd7ae686352134ead21639f61a5b0f0e6eb6968f233b`. `core.autocrlf=true`; working copies are CRLF.
- Test manifest hash is LF-normalized `6dd5a675035d746230dffba791ccbabb85ddb15f973bef19742d5272b51c7462`; working copy SHA-256 `8d763edcf5a1445c76e35bae8686b2fefbdbffd6d68e5eff3d300ebdb9a8510d`; LF-normalized SHA-256 `6dd5a675035d746230dffba791ccbabb85ddb15f973bef19742d5272b51c7462`. `core.autocrlf=true`; working copies are CRLF.
- Simulator commit `893a82a7fa731b95d97de8486cfa8ad59a848f38`; committed LF blob SHA-256 `bd8065b993475d280ae3f55ea3a11df7fbe2b5dfa5b99688fe613f9fcd953320`; CRLF copy used in the run SHA-256 `3c8a9f82347594638301c18c45506186e56c903dc088070c3093d2d59b767204`.
- The final reproduction uses the two files under `experiments/day6/extended_120d/repro/`; `models/day6_extended_runner.py` was not used.

## Superseded statements

The v4 statement “11 unassigned + 3 pending” was wrong: measured L05/LP pending is 0 and unassigned is 14. “Waiting cost 24 was used” was wrong: 1.0 was executed; 24.0 is a unit-consistent rerun with the same simulator, not the costs of the original execution. “Unlimited lane capacity” was wrong: lane capacity is finite, `BIG = 10 ** 9`.
