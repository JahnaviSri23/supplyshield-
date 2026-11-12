import networkx as nx
from sim.simulator import simulate


def test_travel_duration(base_hours, multiplier, expected_days):
    graph = nx.DiGraph()

    graph.add_node("A", cap=10, buffer=100)
    graph.add_node("B", cap=10, buffer=100)

    graph.add_edge("A", "B", cost=base_hours)

    graph.graph["demands"] = {("A", "B"): 5}
    graph.graph["waiting_cost"] = 1
    graph.graph["unmet_penalty"] = 96

    scenario = {
        "demand_days": 1,
        "horizon": 10,
        "failure_days": 0,
        "travel_time_multipliers": {
            ("A", "B"): multiplier
        },
    }

    result = simulate(graph, scenario)

    history = result["history"]

    assert result["delivered"] == 5, (
        f"Expected 5 delivered, got {result['delivered']}"
    )

    # Shipment dispatched on day 0 must arrive on expected_days.
    for day in range(expected_days):
        assert history[day]["delivered"] == 0, (
            f"Shipment arrived too early for {base_hours} hours"
        )

    assert history[expected_days]["delivered"] == 5, (
        f"Shipment did not arrive on day {expected_days}"
    )

    print(
        f"PASS: {base_hours}h × {multiplier} "
        f"→ arrival day {expected_days}"
    )


test_cases = [
    (6, 1.0, 1),
    (24, 1.0, 1),
    (25, 1.0, 2),
    (30, 1.0, 2),
    (48, 1.0, 2),
    (72, 1.0, 3),
    (30, 2.0, 3),
    (48, 1.5, 3),
]

print("\nRISK-ADJUSTED TRAVEL DURATION TESTS")

for base_hours, multiplier, expected_days in test_cases:
    test_travel_duration(base_hours, multiplier, expected_days)

print("\nALL TRAVEL DURATION TESTS: PASS")