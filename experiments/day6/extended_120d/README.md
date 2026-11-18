# Day 6 extended 120-day results — provisional v3

## Configuration and cost convention

Configuration is 14 demand days / 14-day closure / 120-day horizon, a simulator-side assumption owned by A and B and approved provisionally by A and C. The waiting-rate decision belongs to A and B. Both cost variants are reported with equal prominence: **1.0, as executed**; **24.0, unit-consistent rerun using the same simulator, not the costs of the original execution**. C clarified that the project cost unit is leg-hours: one leg waiting one day is 24 leg-hours; the terminal unmet penalty 96 equals four days at that rate. C approved reporting both rates.

Lead with pricing-independent recovery and unmet metrics; show costs afterward with separate shipping, daily waiting, and one-time terminal unmet-penalty columns. Waiting cost accrues daily on queued demand and the simulator's outside-backlog accounting bucket. `unassigned` demand is not queued or retried, but this simulator counts it in that outside bucket for waiting-cost accounting. The terminal penalty is applied once at the horizon, so total cost for censored runs grows with horizon. Simulator totals must not be compared with C's `c_expected_*` per-day optimizer values.

The day-1 numerical check was **NOT performed**. C accepted the documented modelling differences; the comparison remains **NOT DIRECTLY COMPARABLE**. The 95th-percentile hub-capacity and candidate-path formulation leaves some L10 demand unserved; see the report for C's explanation and B's aggregate-only check. A per-lane assigned-flow check was not performed because the unmodified simulator does not expose per-lane assigned flow.

## Hash conventions and provenance

- Simulator commit: `893a82a7fa731b95d97de8486cfa8ad59a848f38`. Committed LF blob SHA-256: `bd8065b993475d280ae3f55ea3a11df7fbe2b5dfa5b99688fe613f9fcd953320`. CRLF copy used by the isolated run SHA-256: `3c8a9f82347594638301c18c45506186e56c903dc088070c3093d2d59b767204`. The CRLF copy hash matches the v2-recorded simulator hash.
- Adapter manifest hash is LF-normalized: `74aa58245e485d318dffcd7ae686352134ead21639f61a5b0f0e6eb6968f233b`. Test manifest hash is LF-normalized: `6dd5a675035d746230dffba791ccbabb85ddb15f973bef19742d5272b51c7462`. Working copies are CRLF; their raw working-copy hashes are `168878e2c6efc1f2b65f8058efb8ceecf5eb4ca20e92223b34a79ea35ba0d0f5` (adapter) and `8d763edcf5a1445c76e35bae8686b2fefbdbffd6d68e5eff3d300ebdb9a8510d` (tests).
- The original run manifests remain in local run-output folders. The four `h*.json` manifests included here are historical reproduction manifests, distinct from the original run manifests. They record wrapper SHA-256 `8c8a71b21e7fd3c33d919cbc8c985185eae3565f8e7532beee4d992e117d2d6f`; that value does not match the packaged tree script raw SHA-256 `a4cce27ca731cfc546bfe3cbe16455fa92b7b7186b5aa4137622a1b4731b9a76`. It matches the local historical `submission_candidate_v6/repro/run_extended.py` wrapper. These four copied manifests are not attributable to the exact packaged script. The separate fresh-layout runs under `submission_final_v3/sanity/results/` were produced with the unchanged packaged script (raw SHA-256 `a4cce27ca731cfc546bfe3cbe16455fa92b7b7186b5aa4137622a1b4731b9a76`); their new measured manifests record that wrapper hash.
- Frozen plan SHA-256: `f588d41116e69cf00e71f8602ee6f98919140143fa10ec50a63c15a5a99c435a`; commit `9a8aa89bc964a21bc286642af97ea0e9fc02dbe0`, merged into local `origin/main` by C (read-only ancestry check).

## Reproduction

From the fresh-layout run, with the working directory set to the repo root:

```text
python experiments/day6/extended_120d/repro/run_extended.py --horizon 40 --waiting-rate 1.0 --out experiments/day6/extended_120d/repro_outputs/out_h40_w1
python experiments/day6/extended_120d/repro/run_extended.py --horizon 120 --waiting-rate 1.0 --out experiments/day6/extended_120d/repro_outputs/out_h120_w1
python experiments/day6/extended_120d/repro/run_extended.py --horizon 40 --waiting-rate 24.0 --out experiments/day6/extended_120d/repro_outputs/out_h40_w24
python experiments/day6/extended_120d/repro/run_extended.py --horizon 120 --waiting-rate 24.0 --out experiments/day6/extended_120d/repro_outputs/out_h120_w24
```

Run all commands with the repository root as the current working directory. Outputs are placed beneath `experiments/day6/extended_120d/repro_outputs/` and each destination must not already exist. The isolated setup requires `models/outputs/risk_table.csv` with the exact hash listed in `manifests/pinned_inputs_manifest.json`. That file is untracked and is not included in a fresh checkout; reproduction is therefore not self-contained from a clean clone until the approved input is supplied. The four clean-room runs each made 40 simulator calls. The h40/rate-1 output hash matches the original v2 summary. The h120/rate-1 output matches the final h120 summary at `1e-9` after common-column mapping. Rate-24 outputs match their like-for-like reference; when compared with rate-1, waiting and total cost differ by design. For h120/rate-24, the old reference's horizon field remains 40; treat that metadata difference separately from the other columns.

## Package files and SHA-256

Hashes below are computed from the v3 tree file bytes. The report hash is included; this README is omitted to avoid embedding its own hash.

| File | SHA-256 |
|---|---|
| `docs/person_b_day6_extended_120d_report.md` | `daf9ea6bb3a432d389a9af5e3f411e107c8fc456a999b62da9e5d4ec8ede334e` |
| `experiments/day6/extended_120d/manifests/h120_w1.json` | `c560995497d14cc0945c624bee744c362eacc4ee434606592e92483f94f4f3ca` |
| `experiments/day6/extended_120d/manifests/h120_w24.json` | `736c951d740986e68f35793314804ac96af6bd844bd7f9e30ddb2e3ef03e99ce` |
| `experiments/day6/extended_120d/manifests/h40_w1.json` | `61b6d01987352d6d3d3970bdd8b2af4b950c464dad05b24d87b5a6e008a6ffeb` |
| `experiments/day6/extended_120d/manifests/h40_w24.json` | `5de6b84b6d5837bc17f259cd82b0a50f03134b4677ec066f29f5ab97c3efad38` |
| `experiments/day6/extended_120d/manifests/pinned_inputs_manifest.json` | `b1cde6e0bc7463959d4eda34230d72c645d8b5bc15a5855ccd02e4f5cf4e5613` |
| `experiments/day6/extended_120d/repro/prepare_isolated.py` | `983b58265d95f38897d046d82ae5c009fe404bf1e5ee4639c8436dc460bfc7ee` |
| `experiments/day6/extended_120d/repro/run_extended.py` | `a4cce27ca731cfc546bfe3cbe16455fa92b7b7186b5aa4137622a1b4731b9a76` |
| `experiments/day6/extended_120d/results/censored_breakdown.csv` | `5b5adc8be50ef7ee58f5b241e9b9bf8e13cd4353b79e255e378a3e51b2a3c75e` |
| `experiments/day6/extended_120d/results/final_summary_h120_waiting1_as_executed.csv` | `803811cf8a07822b6766ba5f6d8cc8dce681096caad15c5b2a75005836931d67` |
| `experiments/day6/extended_120d/results/pending_unassigned_40.csv` | `95fff01048057188af6eaded4ea8dc0d79b1cac5daee2687fae8d2a7c6d64c55` |
| `experiments/day6/extended_120d/results/recovery_stats.csv` | `f5a8d5eaf32175376a8387d06d4bfeac22ef53e3d322b18d84567451d8105117` |
| `experiments/day6/extended_120d/results/sensitivity_40_vs_120.csv` | `862a4ba232228028570c6c15cf9b43cf0ffaecdcfde592dec536edb13aafb5e0` |
| `experiments/day6/extended_120d/results/slide_aggregates.csv` | `b2c0d054d1ff44d38f46d61ee431f0241cf55b6a5ea28d503ce5f8bcd2a82f41` |
| `experiments/day6/extended_120d/results/waiting_cost_sensitivity.csv` | `46aa9b91619583b1f64d9c58639704e95a5d3b860e7f127c7f06211122b3fddb` |

## Pending approvals

- A review of the actual report, CSVs, and manifests; A's approval remains provisional until that review.
- Instructor release approval for lane-level tables, local SHAP, and row-level files.

All results and conclusions are provisional.
