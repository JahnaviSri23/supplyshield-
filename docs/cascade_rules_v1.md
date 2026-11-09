# SupplyShield: Cascade Simulator Rules and Scope

## B04 structural cascade mode

`sim/simulate.py::simulate_cascade` is a structural stress abstraction over hub-level scalar loads.

1. `capacity` maps hubs to the dispatch-capacity proxy; `load` maps hubs to baseline scalar load.
2. An initial set of hubs fails. Unless `check_initial=False`, an initially overloaded state raises an error.
3. `build_neighbors` symmetrizes input lanes. The graph used by B04 is therefore undirected even though the frozen core network has 292 directed lanes.
4. The entire accumulated scalar load at each failed hub is redistributed among alive neighbors in proportion to `max(capacity - current_load, 0)`. If all such spare-room weights are zero, the implementation falls back to capacity-proportional weights. If no usable neighbor weight exists, load is marked unserved.
5. A hub fails when updated scalar load exceeds `tolerance * capacity`; rounds repeat until no new failures or `max_rounds` is reached.

This is not physical or operational OD rerouting. It does not preserve origin-destination flows, respect direction, or reroute only traffic above capacity. The implementation uses a dispatch-capacity proxy to calculate receiving spare room. That is a modeling rule of this structural abstraction, not a receiving-capacity measurement or an agreed operational constraint. The three destination-only hubs with zero dispatch estimates may receive final deliveries in an operational model, but B04's scalar cascade does not represent that behavior.

## B04 baseline lineage

- Baseline load is mean daily outgoing departures per hub over 12–25 September 2018 inclusive.
- All 14 calendar dates are represented for each core hub, including zero-departure days.
- `hub_daily_departures.csv` is reproducible from `core_train_legs.csv`, restricted to the 292 directed lane pairs in `core_edges.csv`.
- The traffic trip IDs map to the `train` partition in `split_trip_ids.csv`; calibration and test traffic are excluded.
- `core_nodes.csv::legs_per_day_p95` is the linearly interpolated 95th percentile of these daily counts; `capacity_est` is its ceiling. Both are outgoing dispatch proxies, not receiving capacities.
- This B04 14-day structural traffic window is separate from the B02/B03 master trip-level split and does not change it.

Legacy outputs produced from `data/datasplit/train_legs_v1.csv`, inconsistent windows or a zero-capacity-to-one workaround are superseded and are not current B04 evidence. Existing historical artifacts are retained; they must not be combined with the master-split prediction or calibration pipeline.

## Operational recovery scope

Directed OD rerouting and daily queues belong to the separate optimizer and queue-simulator workflow. Dispatch capacity is shared across outgoing traffic there; queue storage buffers are assumed waiting space, not measured receiving throughput. B04 does not validate or replace that operational workflow.
