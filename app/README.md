# SupplyShield: Express Logistics Control Tower & Disruption Recovery

An executive-ready, high-contrast SaaS Control Tower dashboard for the **SupplyShield** research project.

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

## Control Tower SaaS Features

- **High-Contrast Dark Slate Theme**: Configured via `app/.streamlit/config.toml` (`#0B1120` canvas, `#111827` cards, `#38BDF8` cyber cyan accents).
- **Executive SaaS Header**: Live status pill (`● LIVE CONTROL TOWER`) and collapsible operational scope expander.
- **Interactive Live What-If Simulator**: Real-time recruiter demo solving multi-commodity flow LPs on demand (`scipy.optimize.linprog` with `method="highs"` in <50 ms), displaying cost reductions vs. doing nothing, glowing route visualizations, and CSV dispatch downloads.
- **Geographic India Corridor Visualizer**: Centered on India (`Scattergeo` with `scope="asia"`, `lonaxis_range=[67, 98]`, `lataxis_range=[6, 37]`), with a toggle to the full 100-hub spring-layout network topology.

---

## Dashboard Pages

1. **Overview**:
   - Executive metric cards with delta badges: Core Hubs (100), Directed Lanes (292), and % LP Cost Reduction vs. Do Nothing.
   - Clean summary table comparing average `total_cost`, `extra_vs_best_normal`, and `unmet` flow across the 4 recovery plans from `experiments/c_multiflow_closures.csv`.
   - Dark-transparent Plotly comparative charts and operational insights.
   - Collapsible operational scope notice.

2. **Live What-If Simulator (Interactive Recruiter Demo)**:
   - Select any active corridor from `data/processed/core_edges.csv` (labeled with facility names).
   - Dynamic Lost-Leg Penalty Slider (20 to 200 leg-hours, default 96).
   - Toggle Machine-Learning Risk-Adjusted Costs (`pred_multiplier` from `models/outputs/risk_table_lane.csv`).
   - "Run Live Rerouting Optimization" button executing HiGHS LP dual-simplex solver in milliseconds.
   - Interactive India corridor map with glowing red closed lane (`#EF4444`) and live computed cyan detour flows (`#38BDF8`).
   - Downloadable CSV of the optimal dispatch plan.

3. **Closure explorer**:
   - Deep-dive into each of the 10 precomputed lane closure scenarios (L01 through L10).
   - Selectbox of closed lanes with human-readable hub names and baseline daily traffic.
   - Plan comparison table (`total_cost`, `extra_vs_best_normal`, `unmet legs`).
   - Plotly bar chart of `extra_vs_best_normal` per plan.
   - One-line definition of each plan and verification badge (`LP total <= greedy total: PASS/FAIL`).
   - Flow routing inspector expander.

4. **Network view**:
   - High-fidelity geographic plot of India (`Scattergeo` centered on India corridors `[67, 98]°E`, `[6, 37]°N`).
   - Toggle to switch between Geographic Map (India corridors) and Full 100-hub Spring Layout Topology view.
   - Hub coordinates with real lat/lon (95 hubs) and NetworkX spring layout fallback (seed=42) for unlocated hubs (5 hubs), clearly marked in legend and hover text.
   - Interactive scenario and plan inspector showing the closed lane in red and detour edges carrying disrupted OD flow in cyan with width proportional to flow.
   - Clean table of detour edges and traffic volumes.

5. **Uncertainty**:
   - Evaluation of recovery policies under transit time stochasticity (conformal prediction intervals, expected-cost, and risk-averse CVaR optimization).
   - Table and Plotly bar charts comparing the four uncertainty plans (`deterministic`, `point`, `expected`, `CVaR`) across `eval_mean`, `eval_cvar` (CVaR 80%), `eval_worst`, and out-of-sample realized scores (`realized_primary`, `realized_sens_pred`, `realized_sens_5legs`).
   - Interval diagnostics table from `experiments/c_uncertainty_intervals.csv` (`population`, `interval`, `lanes`, `test_legs`, `coverage_of_realized`, `mean_width`, `share_of_samples_inside`).
   - Explicit methodological note on interval calibration and sampling spread.

6. **Method and limitations**:
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
