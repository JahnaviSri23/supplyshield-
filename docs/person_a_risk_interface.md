# Person A — Risk-Adjusted Simulator Interface

## 1. Overview

The SupplyShield simulator supports optional risk-adjusted travel durations while preserving the existing multi-OD simulation interface.

This allows Person B's risk adapter to supply travel-time multipliers without modifying the simulator's internal logic.

## 2. Simulator Interface

```python
from sim.simulator import simulate

result = simulate(graph, scenario, plan=None)
```

Parameters:

- `graph`: Directed NetworkX graph containing hubs and lanes.
- `scenario`: Dictionary containing simulation settings.
- `plan`: Optional optimizer plan using the existing Person C format.

## 3. Passing Risk Multipliers

Person B can supply multipliers through the scenario dictionary.

```python
scenario = {
    "demand_days": 1,
    "horizon": 12,
    "failure_start": 0,
    "failure_days": 0,
    "travel_time_multipliers": {
        ("A", "B"): 1.5,
        ("B", "C"): 2.0,
    },
}

result = simulate(graph, scenario)
```

Each dictionary key identifies a directed lane `(origin, destination)`.

Each value is a positive, finite numeric multiplier.

The adapter must convert lane identifiers into graph edge tuples before calling the simulator. Python tuple keys cannot be used directly as JSON object keys.

## 4. Travel-Duration Calculation

The graph edge attribute `cost` represents baseline travel time in hours.

The simulator calculates:

```python
adjusted_hours = base_hours * multiplier
duration_days = max(1, ceil(adjusted_hours / 24))
```

Examples:

| Adjusted travel time | Simulation duration |
|---|---|
| 6 hours | 1 day |
| 24 hours | 1 day |
| 25 hours | 2 days |
| 30 hours | 2 days |
| 48 hours | 2 days |
| 72 hours | 3 days |

Multipliers are applied once when determining a shipment's travel duration.

They do not modify hub capacity or lane capacity.

The existing shipping-cost calculation remains based on the graph's original edge `cost` attribute.

## 5. Backward Compatibility

If `travel_time_multipliers` is absent or `None`, the simulator preserves its original behavior of one simulation day per traversed edge.

If the dictionary is supplied but a particular edge is missing, that edge uses a multiplier of `1.0` and its baseline travel time.

## 6. Person C Optimizer Compatibility

The simulator continues to accept Person C's multi-OD plans.

Each routing record follows the existing format:

```python
{
    "od": ["A", "C"],
    "edge": ["A", "B"],
    "flow": 5.0
}
```

The risk interface does not require changes to these records.

## 7. Failure and Closure Behavior

- Closed directed lanes block new dispatches during the active failure window.
- Shipments dispatched before a closure continue toward their scheduled arrival.
- Failed hubs can receive shipments, but their outgoing capacity is reduced according to the failure multiplier.
- Final destinations can receive shipments even when their outgoing capacity is zero.
- Intermediate warehouse buffer space is reserved for shipments already in transit.

## 8. Validation Results

The following checks have passed:

| Validation | Result |
|---|---|
| Travel-duration regression tests | 8/8 PASS |
| Risk integration regression tests | 5/5 PASS |
| Person C optimizer plan validation | 40/40 PASS |
| Optimizer validation errors | 0 |
| Optimizer validation warnings | 0 |
| Core simulator flow conservation | PASS |
| Git whitespace check | PASS |

The existing optimizer validation reported 5,357 training departures. Person B's adapter uses the separately approved 5,395-leg population. The demand-population difference must be reconciled before claiming end-to-end dataset alignment.

## 9. Person B Integration Instructions

1. Obtain baseline travel hours from the directed graph's edge `cost` attribute.
2. Generate a positive, finite risk multiplier for each relevant directed lane.
3. Construct `scenario["travel_time_multipliers"]` using directed edge tuples.
4. Call `simulate(graph, scenario, plan)` without modifying Person C's optimizer plan.
5. Inspect the returned simulation metrics and daily history.

No changes to the simulator's function signature are required.