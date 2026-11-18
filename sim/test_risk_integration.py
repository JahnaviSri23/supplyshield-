import networkx as nx
from sim.simulator import simulate


def make_graph():
    graph = nx.DiGraph()

    for node in ["A", "B", "C"]:
        graph.add_node(node, cap=10, buffer=20)

    graph.add_edge("A", "B", cost=30)
    graph.add_edge("B", "C", cost=6)

    graph.graph["demands"] = {("A", "C"): 5}
    graph.graph["waiting_cost"] = 1
    graph.graph["unmet_penalty"] = 96

    return graph


def make_scenario(**changes):
    scenario = {
        "demand_days": 1,
        "horizon": 12,
        "failure_start": 0,
        "failure_days": 0,
        "travel_time_multipliers": {
            ("A", "B"): 1.0,
            ("B", "C"): 1.0,
        },
    }
    scenario.update(changes)
    return scenario


def test_closure():
    graph = make_graph()

    scenario = make_scenario(
        closed_lanes=[["A", "B"]],
        failure_days=2,
    )

    result = simulate(graph, scenario)

    assert result["history"][0]["in_transit"] == 0
    assert result["history"][1]["in_transit"] == 0
    assert result["history"][2]["in_transit"] == 5
    assert result["delivered"] == 5

    print("PASS: Lane closure blocks dispatch until reopening")


def test_in_transit_during_closure():
    graph = make_graph()

    scenario = make_scenario(
        failure_start=1,
        failure_days=3,
        closed_lanes=[["A", "B"]],
    )

    result = simulate(graph, scenario)

    # Shipment leaves A on day 0, before the closure.
    assert result["history"][0]["in_transit"] == 5

    # Shipment remains in transit during the closure.
    assert result["history"][1]["in_transit"] == 5

    # Shipment reaches B on day 2 despite the closed lane.
    assert result["history"][2]["queued"] == 0
    assert result["delivered"] == 5

    print("PASS: Already-dispatched shipments continue during closure")


def test_failed_hub_receiving():
    graph = make_graph()

    scenario = make_scenario(
        failed={"B": 0.0},
        failure_days=3,
    )

    result = simulate(graph, scenario)

    assert result["history"][2]["queued"] == 5
    assert result["delivered"] == 5

    print("PASS: Failed hub receives shipments but cannot dispatch")


def test_zero_capacity_destination():
    graph = make_graph()
    graph.nodes["C"]["cap"] = 0

    result = simulate(graph, make_scenario())

    assert result["delivered"] == 5
    assert result["unmet"] == 0

    print("PASS: Zero-outgoing-capacity destination receives shipments")


def test_queue_and_buffer():
    graph = make_graph()

    graph.nodes["A"]["cap"] = 3
    graph.nodes["A"]["buffer"] = 5

    result = simulate(graph, make_scenario())

    assert result["delivered"] == 5
    assert result["unmet"] == 0

    for record in result["history"]:
        assert record["generated"] >= record["delivered"]

    print("PASS: Queue and buffer handling")


if __name__ == "__main__":
    print("\nRISK INTEGRATION REGRESSION TESTS")

    test_closure()
    test_in_transit_during_closure()
    test_failed_hub_receiving()
    test_zero_capacity_destination()
    test_queue_and_buffer()

    print("\nALL RISK INTEGRATION TESTS: PASS")