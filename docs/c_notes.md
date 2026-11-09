# Safe-Plan & Risk Analysis (Hub D Capacity Uncertainty)

## Decision Rule: Express Van Utilization
The optimizer routes flow through the express van only when the express van cost per parcel is strictly less than the penalty for an undelivered parcel (20).

## Safe-Plan Paragraph (CVaR Context)
A baseline planning model that assumes Hub D can consistently handle 60 parcels will route up to 60 units through it to minimize daily operating costs. However, on days when Hub D's capacity drops to 30 or 0, this aggressive baseline causes severe capacity overflows and massive penalty spikes.

Conditional Value at Risk (CVaR) is not the single absolute worst-case scenario; rather, it represents the expected average cost across the worst slice of outcomes (e.g., the worst 20% of days). A CVaR-optimized plan proactively diverts volume to slightly higher-cost secondary paths, effectively removing catastrophic cost spikes on bad days while accepting a small increase in standard operating costs.


# Toy Graph Policy Comparison & Real-Graph Design Notes

## 1. Five-Plan Policy Comparison Table

Below are the evaluated daily operational costs across 1,000 sampled scenarios (evaluated across 5 different seeds):

| Plan | Average Cost | CVaR 80% | Worst Day |
| :--- | :--- | :--- | :--- |
| **1. Do nothing** | 1250 | 1250 | 1250 |
| **2. Greedy** | 684 | 1206 | 1500 |
| **3. Deterministic LP** | 746 | 1406 | 1700 |
| **4. Expected-cost LP** | 681 | 926 | 1220 |
| **5. CVaR LP** | 810 | 810 | 810 |

---

## 2. Evaluation Findings

* **Deterministic LP vs. Greedy Baseline:** The deterministic LP assumes a fixed, ideal capacity for Hub D at all times without accounting for potential capacity drops or risk. Because it plans under the assumption that Hub D will never fail, it heavily over-allocates traffic to Hub D. When Hub D suffers capacity bottlenecks during bad days, the deterministic LP incurs extreme spillover penalties (leading to a worst-day cost of 1700), which severely drags down its overall average cost compared to the greedy baseline.

* **CVaR Plan Behavior:** The CVaR LP explicitly optimizes against worst-case tail outcomes. Instead of routing traffic through cheaper but volatile routes (such as Hub D), it proactively routes demand through consistently available, risk-averse alternative paths (costing 6 per unit instead of 5). By completely bypassing the volatile bottleneck, its daily operational cost remains flat at 810 regardless of Hub D's daily capacity fluctuations.

* **Expected-Cost LP Significance:** While the expected-cost LP shows a slightly lower average cost (681 vs. 684—a 3-point difference), this gap is **not statistically meaningful**. Given that the seed-to-seed standard deviation across runs is approximately 10, the 3-point difference falls well within normal sampling noise and variance.

* **Management Recommendations:**
  * **Risk-Averse Manager (Fears Bad Days):** Recommend **Plan 5 (CVaR LP)** or **Plan 4 (Expected-cost LP)**. Plan 5 guarantees a strict upper bound of 810 with zero daily variance, while Plan 4 caps worst-day exposure at 1220 (compared to 1500+ for greedy/deterministic).
  * **Cost-Focused Manager (Cares About Average):** Recommend **Plan 4 (Expected-cost LP)**. It achieves the lowest overall average cost (~681) while providing significantly better protection against worst-case spikes than the greedy or deterministic baselines.

---

## 3. Model Limitations Note

> **Note on Model Scope:** These results are derived from a simplified toy network with fixed parameters (spillover penalty of 20, specific failure probabilities, and alternative route costs of 6 vs. 5). These numbers illustrate policy behavior and risk-tradeoff mechanics rather than exact empirical predictions for real-world logistics.

---

## 4. Real-Graph Optimization Design Notes

* **Lane Cost Definition:** Assign baseline edge costs using the **median travel time** derived from historical leg/lane data.
* **Demand Definition:** Define origin-destination demand requirements using the **top 10–20 busiest Origin-Destination (OD) pairs** in the core graph.
* **Hub Capacity Definition:** Estimate baseline node capacities using historical peak-day throughput estimates generated from processed core files.


# C Optimization Notes & Sensitivity Analysis

## 1. Assumptions & Setup
* **Cost Unit:** Travel time in **hours**.
* **Penalty:** Default penalty for undelivered (unmet) legs is set to **48 hours** (`PENALTY_HOURS = 48`).
* **Daily Demand:** Demand per lane is calculated as $\text{trips} / 14$ legs per day, based on the 14-day training period.
* **Hub Capacities:** `capacity_est` is derived from the 95th percentile of normal daily outgoing legs (`ceil(p95 outgoing legs)`).
* **Isolation Test:** Each lane closure is evaluated individually (in isolation).

---

## 2. Limitations
* **Optimistic Mode:** Hubs are assumed to be empty apart from the rerouted flow, giving the rerouted legs full access to `capacity_est`.
* **Pessimistic Mode (`--spare`):** Hub capacities are reduced by normal daily background traffic, evaluating only available spare room.
* **Isolated Closure Limitation:** Background network traffic does not dynamically re-route during single-lane closures; multi-flow interactions are handled separately in `c_multiflow.py`.

---

## 3. Key Observations & Findings
* **No-Impact Lane Closures:** Certain lane closures (e.g., `IND560300AAA -> IND562132AAA`) result in the exact same cost (6.5) across all three plans (Do Nothing, Greedy, Optimizer). This occurs because the original shortest-path route did not utilize the closed lane in the first place, meaning the closure had zero impact on traffic flow. Additionally, direct lane median times can occasionally exceed a two-hop path due to using medians.
* **Plan Performance Ranking:** Across all modes and penalty tests, the strict performance ranking is maintained:
  $$\text{Optimizer} \le \text{Greedy} < \text{Do Nothing}$$
* **Penalty Sensitivity:**
  * **Optimistic Run:** Neither Greedy nor Optimizer lose any legs (0.0 unmet), so varying `PENALTY_HOURS` (24, 48, 96) has **zero impact** on their total cost (18.7 and 10.8 respectively). Only the "Do Nothing" cost scales linearly with penalty.
  * **Pessimistic Run:** Because spare capacity is limited, Greedy drops 1.7 legs, leading to cost increases as penalty scales ($28.6 \rightarrow 32.7 \rightarrow 40.9$). The LP Optimizer minimizes unmet legs down to 0.5, resulting in significantly lower cost growth ($16.5 \rightarrow 17.7 \rightarrow 20.1$).

---

## 4. Single Lane Closure Experiment Results

### Mode 1: Optimistic (Hubs Empty)

| Penalty Hours | Plan | Average Total Cost (leg-hours) | Unmet Legs (Sum over 10 closures) |
| :--- | :--- | :--- | :--- |
| **24** | **Do Nothing** <br> **Greedy** <br> **Optimizer** | 123.0 <br> 18.7 <br> 10.8 | 51.0 <br> 0.0 <br> 0.0 |
| **48** | **Do Nothing** <br> **Greedy** <br> **Optimizer** | 245.4 <br> 18.7 <br> 10.8 | 51.0 <br> 0.0 <br> 0.0 |
| **96** | **Do Nothing** <br> **Greedy** <br> **Optimizer** | 490.2 <br> 18.7 <br> 10.8 | 51.0 <br> 0.0 <br> 0.0 |

---

### Mode 2: Pessimistic (`--spare` Capacity)

| Penalty Hours | Plan | Average Total Cost (leg-hours) | Unmet Legs (Sum over 10 closures) |
| :--- | :--- | :--- | :--- |
| **24** | **Do Nothing** <br> **Greedy** <br> **Optimizer** | 129.4 <br> 28.6 <br> 16.5 | 53.8 <br> 1.7 <br> 0.5 |
| **48** | **Do Nothing** <br> **Greedy** <br> **Optimizer** | 258.5 <br> 32.7 <br> 17.7 | 53.8 <br> 1.7 <br> 0.5 |
| **96** | **Do Nothing** <br> **Greedy** <br> **Optimizer** | 516.6 <br> 40.9 <br> 20.1 | 53.8 <br> 1.7 <br> 0.5 |

---

## 5. Share of Legs Lost (Pessimistic Mode)
Total daily legs: 56
Fraction unmet by plan:
 plan
do nothing    0.960714
greedy        0.030357
optimizer     0.008929
Name: unmet, dtype: float64

## 6. Multi-Flow Optimization (`c_multiflow.py`)

### Baseline (No Closure)
* **LP Optimum:** 2041.6 leg-hours
* **Unmet Legs:** 0.00 (Network capacities successfully support baseline traffic demand)
* **Solve Time:** 0.5 seconds

### Multi-Flow Single-Lane Closure Results

| Plan | Average Extra Cost (leg-hours) | Total Unmet Legs (Sum over 10 closures) |
| :--- | :--- | :--- |
| **LP (All Flows)** | **25.2** | **1.65** |
| **Greedy** | **28.4** | **1.65** |
| **Do Nothing** | **515.9** | **55.00** |

*Max LP solve time:* 0.85s

### Key Findings & Methodology Notes
* **Network-Wide Re-optimization:** Allowing background traffic to adjust routes (LP) reduces closure-induced extra costs from 28.4 to 25.2 leg-hours (~11% savings over Greedy).
* **Comparison Caveat:** In `c_multiflow.py`, extra cost is calculated by comparing each plan against its own no-closure baseline. Because the global LP can re-optimize background routes simultaneously, this baseline comparison is not strictly 1-to-1 with greedy baseline behavior.

## Day 7 Experiments: Baseline Validation & Cost Decomposition

### Key Takeaways & Validation
- **Optimizer Correctness:** The LP solver was formally verified to never perform worse than the greedy heuristic across all evaluated single-lane closures (`CHECK: LP total <= greedy total: True`).
- **Feasibility & Speed:** Zero unmet demand under normal baseline conditions (`unmet: 0.00`), confirming that core traffic fits within estimated hub capacities. LP solve time remains under 1.1 seconds across the 100-hub core network.
- **Rerouting Efficiency:** Across 10 single-lane closures, the "do nothing" baseline loses 55.0 leg-hours of total flow, whereas both the LP and greedy rerouting deliver ~97% of affected traffic (losing only 1.65 leg-hours).

---

### Cost Breakdown: Global Optimization vs. Rerouting Impact
When measuring average total extra cost across closures:
- **LP (All Flows):** 25.2 leg-hours
- **Greedy Baseline:** 50.9 leg-hours
- **Do Nothing:** 538.5 leg-hours

#### Critical Decomposition Analysis:
1. **Starting Baseline Advantage (~22.6 leg-hours):** Out of the 25.7 leg-hour total difference between the LP and greedy, **22.6 leg-hours** stem from global routing efficiency during normal operations (i.e., replacing sub-optimal direct lanes with multi-hop paths even when no closure occurs).
2. **Closure Response Advantage (~3.1 leg-hours):** Only **3.1 leg-hours** of the average gap represent the LP's dynamic response specifically to the closures themselves.
3. **High-Impact Exceptions:** On major bottleneck lanes (e.g., `IND560099AAB -> IND560300AAA`), re-optimizing background flows provides major savings, outperforming greedy by 66.5 leg-hours during a disruption.

## Optimization & Demand Summary (Day 8 Update)

### 1. Demand & Trip Insights
- **Coverage:** Core OD demand derived from `split_trip_ids.csv` covers 4,436 training trips (44.5% of total training trips) across 297 OD pairs inside the core network.
- **Trip Characteristics:** Trips are predominantly single-leg, with a mean of 1.13 legs per trip. 
- **Leg Breakdown:** 237 out of 297 OD pairs (80%) are 1-leg usual routes (2-leg: 43, 3-leg: 14, 4-leg: 3).

### 2. Model Choice & Rationale
- **Primary Model:** Retaining the **lane-flow model** (converting trip demand to daily legs per lane).
- **Rationale:** Because ~80% of trips are single-leg, full hub failures result in mostly unavoidable end-point traffic loss with minimal recoverable rerouting potential. In contrast, single-lane closures allow single-leg flows to detour through intermediate hubs, making lane-closure evaluation much more meaningful and aligned with lane-level risk modeling.

### 3. Plan Definitions & Parameters
- **Evaluated Plans:** 
  1. *Do Nothing:* Baseline unmitigated operational plan.
  2. *Greedy:* Local rerouting/drop heuristic.
  3. *Preserve:* Reroutes affected flows while freezing unaffected baseline flows from the no-closure LP.
  4. *LP:* Global joint LP re-optimization.
- **Units & Constants:**
  - Flow: Daily truck-legs per day.
  - Cost Metric: Leg-hours (median travel time).
  - Unmet Demand Penalty: **48 leg-hours**.

### 4. Validation & Acceptance Checks
- `CHECK: LP <= greedy` → **True**
- `CHECK: LP <= preserve` → **True**
- **Decomposition:** The LP's cost advantage over greedy is primarily driven by the starting-point baseline gap rather than the closure response alone.

### 5. Hub Traffic Analysis (Unavoidable Loss vs. Recoverable)
hub  share_ends_here  share_passes_through
0  IND000000ACB         0.235798              0.015780
1  IND562132AAA         0.183499              0.005861
2  IND421302AAG         0.150135              0.001353
3  IND560099AAB         0.110234              0.005410
4  IND411033AAA         0.095131              0.006312
5  IND560300AAA         0.084085              0.000000
6  IND400072AAB         0.066276              0.000000
7  IND160002AAC         0.055455              0.000000
8  IND600056AAB         0.058161              0.000000
9  IND000000ACT         0.025023              0.000000

"Traffic with share_ends_here represents unavoidable loss during a hub failure because the hub is the trip's origin or destination. Because share_passes_through is very low across top hubs, hub failure scenarios offer minimal recoverable rerouting potential, justifying our focus on lane-closure optimization."

### 6. Viva Prep & Conceptual Q&A

1. **What is a flow, a capacity, and a penalty in your real-graph LP?**
   - **Flow:** Daily truck-legs allocated along a directed lane $(u, v)$ for a specific demand pair.
   - **Capacity:** Maximum estimated leg capacity per day for lane $(u, v)$, derived from historical baseline volume.
   - **Penalty:** Cost incurred per unit of unmet demand (set to **48 leg-hours**), ensuring the LP prefers rerouting over dropping traffic unless rerouting cost exceeds 48 hours.

2. **What does `preserve` (affected flows only) do, and why can the LP never be worse than it?**
   - **Preserve Plan:** Freezes all unaffected baseline flows from the no-closure LP state and only reroutes the flows directly impacted by a lane closure.
   - **LP Dominance:** The LP performs a global joint re-optimization over all flows simultaneously. Because `preserve` is a restricted subset of the LP's feasible decision space, the LP cost is guaranteed to be $\le$ the `preserve` plan cost ($\text{LP} \le \text{preserve}$).

3. **Why was the LP’s advantage over greedy mostly a starting-point gap?**
   - About 22.6 leg-hours of the 25.7 leg-hour advantage came from optimizing the baseline steady-state routing before any closure even occurred, rather than superior real-time detour routing.

4. **Why do hub failures need trip-based demand?**
   - Hub failures require knowing complete multi-leg trip paths because a hub failure drops all originating/terminating trips while allowing intermediate passing-through trips to detour. Without trip-level origin-destination mapping, passing traffic cannot be separated from endpoint traffic.

5. **What are the key simplifying assumptions / limitations of this model?**
   - Independent lane delays (ignores spatial delay correlation).
   - Single-lane closures evaluated in isolation.
   - Optimistic capacity estimates based on observed historical max flow.
   - Heuristic unmet demand penalty ($48$ leg-hours).

   ### 7. Hub Failure vs. Lane Closure Justification
     hub  %_ends_here  %_passes_through
0  IND000000ACB         23.6               1.6
1  IND562132AAA         18.3               0.6
2  IND421302AAG         15.0               0.1
3  IND560099AAB         11.0               0.5
4  IND411033AAA          9.5               0.6
5  IND560300AAA          8.4               0.0
6  IND400072AAB          6.6               0.0
7  IND160002AAC          5.5               0.0
8  IND600056AAB          5.8               0.0
9  IND000000ACT          2.5               0.0
