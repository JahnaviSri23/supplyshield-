# Person A: Dynamic Simulation and Strategy Evaluation

## Overview

SupplyShield uses a dynamic, multi-day logistics simulator to evaluate how delivery networks respond to disruptions.

The simulator is implemented in `sim/simulator.py`. It supports multiple origin-destination (OD) demands, hub capacity constraints, warehouse buffers, temporary lane closures, and recovery strategy plans.

## Network and Demand

The simulation uses a directed core network containing 100 hubs and 292 lanes.

Hub dispatch capacities are estimated from training data. Warehouse buffer capacities are modelling assumptions, calculated as:

`buffer = 2 × max(hub_capacity, 1)`

The simulator supports multiple OD flows and tracks generated, delivered, queued, in-transit, and unmet demand.

## Disruption Scenarios

The strategy comparison uses 10 lane-closure scenarios from `experiments/c_multiflow_plans.json`.

Each scenario is evaluated using:

- Demand generation: 7 days.
- Simulation horizon: 120 days.
- Failure start: Day 0.
- Lane closure duration: 3 days.
- Capacity scaling: 1.0.
- Unmet-demand penalty: 96 cost units per undelivered unit.

Lane closures are temporary. Closed lanes reopen after the disruption period.

## Recovery Strategies

Three strategies are evaluated under each scenario:

1. **Do Nothing:** Baseline routing without proactive recovery optimization.
2. **Greedy:** Recovery routing generated using a greedy approach.
3. **LP (All Flows):** Recovery routing generated using linear programming across multiple OD flows.

The simulator evaluates the supplied plans using the same demand and disruption settings within each scenario.

## Cost Model

The simulator reports:

- Shipping cost.
- Waiting cost.
- Unmet-demand penalty.
- Total simulated cost.

Total cost is calculated as:

`total_cost = shipping_cost + waiting_cost + unmet_penalty × unmet`

Costs are simulation cost units and should not be interpreted as actual currency.

Unassigned demand is included in outside backlog and contributes to waiting cost until the simulation ends.

## Results

A total of 30 simulations were completed: 10 scenarios × 3 strategies.

Results are stored in:

`experiments/person_a_strategy_comparison.csv`

The LP strategy achieved the lowest simulated total cost in all 10 evaluated scenarios.

Flow conservation validation passed across all 30 simulations.

The maximum observed numerical balance error was approximately `9.09 × 10⁻¹³`.

Recovery was censored in 16 simulations, meaning complete delivery was not achieved within the 120-day horizon. Unassigned routes were confirmed as the cause of remaining unmet demand in scenario L01; other scenarios require separate diagnosis before attributing their unmet demand to the same cause.

## Limitations

- Hub capacities are training-derived estimates rather than measured physical capacities.
- Warehouse buffers are modelling assumptions.
- Shipping and waiting costs are simulation cost units.
- Recovery results depend on the supplied routing plans and disruption assumptions.
- Some demand may remain unassigned when no valid route is available.
- Results should not be interpreted as real-world delivery guarantees.
- The 10 lane closures are evaluation scenarios, not probabilistic forecasts of future disruptions.

## Reproduction

Run the simulator tests:

`python -m sim.test_toy`

`python -m sim.test_core`

`python -m sim.test_multiflow`

Run all strategy comparisons:

`python -m sim.compare_strategies`

Validate the exported CSV using the flow conservation identity:

`generated = delivered + unmet`