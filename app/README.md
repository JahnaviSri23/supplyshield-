# SupplyShield: Express Logistics Disruption Recovery Dashboard

An interactive, read-only demo dashboard for the **SupplyShield** research project.

## Quick Start

From the repository root, run:

```bash
python -m streamlit run app/app.py
```

Or with a specific virtual environment (e.g. `ss_env`):

```bash
.\ss_env\Scripts\streamlit.exe run app/app.py
```

## Mandatory Notice
> **Real network and transit times (Delhivery, 3 weeks, 2018). Closures are simulated. Capacity = 95th percentile of outgoing legs per day. Results apply only to the 100-hub core.**

---

## Project Overview

SupplyShield benchmarks automated recovery policies when critical freight corridors fail across a major express parcel logistics network in India (Delhivery core subnetwork of 100 hubs and 292 directed lanes across 3 weeks in 2018).

### Evaluated Recovery Plans
When an active corridor closes, 4 recovery strategies are evaluated:
1. **`do nothing`**: Disrupted flow cannot reach its destination and becomes unmet demand. Incurs the maximum penalty (96 leg-hours per undelivered leg).
2. **`greedy`**: Reroutes disrupted flows locally along alternative shortest paths without considering system-wide network congestion.
3. **`preserve (affected flows only)`**: Locks all unaffected shipments in their original baseline routes and optimizes rerouting strictly for the displaced flow.
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
   - Origin/destination hub names, states, and baseline daily legs.
   - Comparison of total cost, extra cost, unmet flow, and solver time per plan.
   - Flow rerouting inspection (OD demand, path shifts, and active edge allocations).

3. **Network view**:
   - Interactive geographic plot of India showing the 100 core hubs (with coordinates) and 292 directed edges.
   - Visual highlighting of the 10 tested closure corridors.
   - Hub capacity and lane volume distributions with searchable data tables.

4. **Uncertainty**:
   - Evaluation of recovery policies under transit time stochasticity (conformal prediction intervals, expected-cost, and risk-averse CVaR optimization).
   - Summary comparison of deterministic vs. point estimate vs. expected vs. CVaR policies.
   - Validation of 50% and 90% conformal prediction intervals from `experiments/c_uncertainty_intervals.csv`.
   - Scenario-level breakdowns across simulation seeds.

5. **Method and limitations**:
   - Formulation details of the multi-commodity flow network model.
   - Precise mathematical and operational definitions of each recovery policy.
   - Explicit project assumptions, boundary constraints, and limitations.

---

## Data & Architecture

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

