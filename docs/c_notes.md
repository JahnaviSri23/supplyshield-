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