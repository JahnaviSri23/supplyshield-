from pathlib import Path
from time import perf_counter

import networkx as nx
import numpy as np
import pandas as pd

from sim.simulator import simulate


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "experiments"

START = pd.Timestamp("2018-09-12")
CUTOFF = pd.Timestamp("2018-09-26")
OBSERVATION_DAYS = 14

KEYS = ["source_center", "destination_center"]


def build_core_graph():
    nodes = pd.read_csv(PROCESSED / "core_nodes.csv")
    edges = pd.read_csv(PROCESSED / "core_edges.csv")
    legs = pd.read_csv(PROCESSED / "core_train_legs.csv")

    if not nodes["hub"].is_unique:
        raise ValueError("Duplicate core hubs.")

    if edges.duplicated(["source", "destination"]).any():
        raise ValueError("Duplicate core lanes.")

    created = pd.to_datetime(
        legs["trip_creation_time"], format="mixed", errors="raise"
    )
    departure = pd.to_datetime(
        legs["od_start_time"], format="mixed", errors="raise"
    )
    arrival = pd.to_datetime(
        legs["od_end_time"], format="mixed", errors="raise"
    )

    in_window = (
        created.ge(START)
        & created.lt(CUTOFF)
        & departure.ge(START)
        & departure.lt(CUTOFF)
    )

    # Demand uses departures during the same 14 days as capacity.
    demand_counts = legs.loc[in_window].groupby(KEYS).size()

    # Cost estimates use only outcomes completed before the cutoff.
    # This avoids using later outcomes to set training-period costs.
    actual = pd.to_numeric(legs["actual_time_min"], errors="coerce")
    completed = (
        in_window
        & arrival.ge(departure)
        & arrival.lt(CUTOFF)
        & np.isfinite(actual)
        & actual.gt(0)
    )

    cost_data = legs.loc[completed, KEYS].copy()
    cost_data["actual_minutes"] = actual.loc[completed]

    costs = cost_data.groupby(KEYS)["actual_minutes"].median()

    graph = nx.DiGraph()

    for row in nodes.itertuples(index=False):
        capacity = float(row.capacity_est)

        if not np.isfinite(capacity) or capacity < 0:
            raise ValueError(f"Invalid capacity for {row.hub}")

        graph.add_node(
            row.hub,
            name=row.name,
            cap=capacity,
            # Storage assumption, held fixed across capacity tests.
            buffer=2 * max(capacity, 1.0),
        )

    missing_costs = []

    for row in edges.itertuples(index=False):
        lane = (row.source, row.destination)

        if row.source not in graph or row.destination not in graph:
            raise ValueError(f"Unknown endpoint: {lane}")

        if lane not in costs.index:
            missing_costs.append(lane)
            continue

        graph.add_edge(
            row.source,
            row.destination,
            cost=float(costs.loc[lane]) / 60.0,
            # No measured lane capacity: only hub dispatch is limited.
            cap=float("inf"),
        )

    if missing_costs:
        raise ValueError(
            "These core lanes lack a valid completed-training cost. "
            "Do not fill them using test-period outcomes: "
            f"{missing_costs}"
        )

    demands = {
        (source, destination): float(count) / OBSERVATION_DAYS
        for (source, destination), count in demand_counts.items()
    }

    if any(not graph.has_edge(*lane) for lane in demands):
        raise ValueError("A demand lane is absent from the frozen core.")

    graph.graph["demands"] = demands

    # Common hour-equivalent accounting units, NOT monetary prices.
    graph.graph["waiting_cost"] = 24.0
    graph.graph["unmet_penalty"] = 96.0

    print("Core hubs:", graph.number_of_nodes())
    print("Core lanes:", graph.number_of_edges())
    print("Training departures counted:", int(demand_counts.sum()))
    print("Daily demand:", round(sum(demands.values()), 4))
    print(
        "Routing: original shortest-cost paths; "
        "these are simulated routes, not observed parcel itineraries."
    )

    return graph


def main():
    graph = build_core_graph()

    # Highest-betweenness hub in the previously reported core analysis.
    busy_hub = "IND000000ACB"
    if busy_hub not in graph:
        raise ValueError("Expected busy hub is missing from the core.")

    # Select the smallest-degree hub with positive observed traffic.
    # Report its degree rather than assuming a degree-one leaf exists.
    incident_demand = {
        node: sum(
            amount
            for (source, destination), amount
            in graph.graph["demands"].items()
            if node in (source, destination)
        )
        for node in graph
    }

    candidates = [
        node for node in graph
        if node != busy_hub and incident_demand[node] > 0
    ]

    leaf_hub = min(
        candidates,
        key=lambda node: (
            graph.degree(node),
            incident_demand[node],
            str(node),
        ),
    )

    print("\nBusy hub:", busy_hub, graph.nodes[busy_hub]["name"])
    print("Small hub:", leaf_hub, graph.nodes[leaf_hub]["name"])
    print("Small hub total degree:", graph.degree(leaf_hub))

    rows = []

    for scale in [1.0, 1.2, 1.5]:
        cases = [
            ("no_failure", {}),
            ("busy_hub_failure", {busy_hub: 0.0}),
            ("small_hub_failure", {leaf_hub: 0.0}),
        ]

        for name, failed in cases:
            scenario = {
                "failed": failed,
                "failure_start": 2,
                "failure_days": 3,
                "demand_days": 7,
                "horizon": 60,
                "capacity_scale": scale,
                "seed": 0,
            }

            started = perf_counter()
            result = simulate(graph, scenario, plan=None)
            runtime = perf_counter() - started

            expected = 7 * sum(graph.graph["demands"].values())
            assert abs(result["generated"] - expected) < 1e-6

            for day in result["history"]:
                accounted = (
                    day["delivered"]
                    + day["queued"]
                    + day["outside_backlog"]
                    + day["in_transit"]
                )
                assert abs(day["generated"] - accounted) < 1e-6

            rows.append({
                "case": name,
                "capacity_scale": scale,
                "generated": result["generated"],
                "delivered": result["delivered"],
                "unmet": result["unmet"],
                "shipping_cost": result["shipping_cost"],
                "waiting_cost": result["waiting_cost"],
                "recovery_days": result["recovery_days"],
                "recovery_censored": result["recovery_censored"],
                "total_cost": result["total_cost"],
                "runtime_seconds": runtime,
            })

    results = pd.DataFrame(rows)

    comparisons = []

    for scale in [1.0, 1.2, 1.5]:
        subset = results.loc[
            results["capacity_scale"].eq(scale)
        ].set_index("case")

        baseline = subset.loc["no_failure"]
        busy = subset.loc["busy_hub_failure"]
        small = subset.loc["small_hub_failure"]

        comparisons.append({
            "capacity_scale": scale,
            "busy_hub": busy_hub,
            "small_hub": leaf_hub,
            "small_hub_degree": graph.degree(leaf_hub),
            "no_failure_drained": (
                baseline["unmet"] < 1e-6
                and not baseline["recovery_censored"]
            ),
            "busy_failure_extra_cost": (
                busy["total_cost"] - baseline["total_cost"]
            ),
            "small_failure_extra_cost": (
                small["total_cost"] - baseline["total_cost"]
            ),
            "busy_cost_greater_than_small": (
                busy["total_cost"] > small["total_cost"]
            ),
        })

        print(
            f"\nCapacity {scale:.1f}x — busy costs more than small:",
            bool(busy["total_cost"] > small["total_cost"]),
            round(float(busy["total_cost"]), 4),
            round(float(small["total_cost"]), 4),
        )

    checks = pd.DataFrame(comparisons)

    OUTPUT.mkdir(exist_ok=True)
    results.to_csv(OUTPUT / "core_simulator_checks.csv", index=False)
    checks.to_csv(OUTPUT / "core_simulator_comparisons.csv", index=False)

    print("\nCORE SIMULATION RESULTS")
    print(results.round(4).to_string(index=False))

    print("\nSANITY CHECKS")
    print(checks.to_string(index=False))

    print("\nFlow conservation: PASS")
    print(
        "No-failure drain and busy-versus-small results must be "
        "reviewed above; they are not forced to pass."
    )
    print("\nSaved:")
    print("experiments/core_simulator_checks.csv")
    print("experiments/core_simulator_comparisons.csv")


if __name__ == "__main__":
    main()