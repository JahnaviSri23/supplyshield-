# SupplyShield: Express Logistics Disruption Recovery Dashboard

An interactive, read-only demo dashboard for the **SupplyShield** research project.

## Quick Start Commands

From the repository root:

### 1. Installation
```bash
python -m pip install -r app/requirements.txt
```

### 2. Run the Dashboard
```bash
python -m streamlit run app/app.py
```
*(Alternatively: `streamlit run app/app.py`)*

### 3. Run Tests
```bash
python -m pytest app/tests/test_data.py
```
*(Or with the standard library unittest runner: `python -m unittest app/tests/test_data.py`)*

---

## Mandatory Notice
> **Real network and transit times (Delhivery, 3 weeks, 2018). Closures are simulated. Capacity = 95th percentile of outgoing legs per day. Results apply only to the 100-hub core.**

---

## Project Overview

SupplyShield benchmarks automated recovery policies when critical freight corridors fail across a major express parcel logistics network in India (Delhivery core subnetwork of 100 hubs and 292 directed lanes across 3 weeks in 2018).

### Evaluated Recovery Plans
When an active corridor closes, 4 recovery strategies are evaluated:
1. **`do nothing`**: Disrupted flow cannot reach its destination and becomes unmet demand. Incurs the maximum penalty (96 leg-hours per undelivered leg).
2. **`greedy`**: Reroutes disrupted flows locally along alternative shortest paths with available capacity without considering system-wide network congestion.
3. **`preserve (affected flows only)`**: Locks all unaffected shipments in their original baseline routes and optimizes rerouting strictly for the displaced flows within remaining capacity.
4. **`LP (all flows)`**: Global multi-commodity flow Linear Program (LP) re-optimizing the entire network jointly to minimize total transit cost and unmet penalties.

### Key Modeling Units
- **Flow**: legs per day (average steady-state parcel shipments).
- **Cost**: leg-hours (shipping travel time + undelivered penalties).
- **Horizon**: One steady-state day.
- **Unmet Demand Penalty**: 96 leg-hours per undelivered leg.
- **Capacity**: 95th percentile of outgoing daily legs per hub.

---

## Dashboard Pages

1. **Overview**:
   - 3 real-time data metric cards: Core Hubs (100), Directed Lanes (292), and Tested Closures (10).
   - Clean summary table comparing average `total_cost`, `extra_vs_best_normal`, and `unmet` flow across the 4 recovery plans from `experiments/c_multiflow_closures.csv`.
   - Comparative charts and operational insights.
   - Mandatory notice banner.

2. **Closure explorer**:
   - Deep-dive into each of the 10 lane closure scenarios (L01 through L10).
   - Selectbox of closed lanes with human-readable hub names and baseline daily traffic.
   - Plan comparison table (`total_cost`, `extra_vs_best_normal`, `unmet legs`).
   - Plotly bar chart of `extra_vs_best_normal` per plan.
   - One-line definition of each plan and verification badge (`LP total <= greedy total: PASS/FAIL`).

3. **Network view**:
   - Interactive geographic plot of India showing the 100 core hubs and 292 directed edges.
   - Hub coordinates with real lat/lon (95 hubs) and NetworkX spring layout fallback (seed=42) for unlocated hubs (5 hubs), clearly marked in legend and hover text.
   - Interactive scenario and plan inspector showing the closed lane in red and detour edges carrying disrupted OD flow in blue with width proportional to flow.
   - Clean table of detour edges and traffic volumes.

4. **Uncertainty**:
   - Evaluation of recovery policies under transit time stochasticity (conformal prediction intervals, expected-cost, and risk-averse CVaR optimization).
   - Table and Plotly bar charts comparing the four uncertainty plans (`deterministic`, `point`, `expected`, `CVaR`) across `eval_mean`, `eval_cvar` (CVaR 80%), `eval_worst`, and out-of-sample realized scores (`realized_primary`, `realized_sens_pred`, `realized_sens_5legs`).
   - Interval diagnostics table from `experiments/c_uncertainty_intervals.csv` (`population`, `interval`, `lanes`, `test_legs`, `coverage_of_realized`, `mean_width`, `share_of_samples_inside`).
   - Explicit methodological note on interval calibration and sampling spread.

5. **Method and limitations**:
   - Direct documentation from `docs/c_notes.md` with zero invented numbers or claims.
   - Mathematical formulation of the multi-commodity flow model.
   - Formal definitions of recovery policies and starting-point cost decomposition analysis.
   - Hub traffic analysis explaining why full hub failures are out of scope.
   - Explicit structural limitations and Viva / defense Q&A.

---

## Data Integrity & Architecture

- **Read-Only**: The dashboard reads strictly from precomputed data files and never invokes optimization solvers or simulation routines dynamically.
- **Validation & Caching**: All data access is mediated through `app/data.py` with column schema verification and `@st.cache_data`.
- **Files Used**:
  - `data/processed/core_nodes.csv`: Hub metadata, states, coordinates, capacities.
  - `data/processed/core_edges.csv`: Directed corridors, traffic volume, distances.
  - `experiments/c_multiflow_closures.csv`: 10 closures × 4 recovery policies benchmark metrics.
  - `experiments/c_real_lane_closures.csv`: Single-flow baseline closure metrics.
  - `experiments/c_multiflow_plans.json`: Full routed flow distributions and scenario configurations.
  - `experiments/c_uncertainty_summary.csv`: Uncertainty policy benchmark.
  - `experiments/c_uncertainty_intervals.csv`: Conformal interval coverage statistics.
  - `experiments/c_uncertainty_results.csv`: Per-seed, per-closure stochastic realization records.
  - `docs/c_notes.md`: Ground truth methodology, cost decomposition, and limitations notes.
