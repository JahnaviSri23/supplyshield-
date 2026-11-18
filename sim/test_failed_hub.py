import networkx as nx
from sim.simulator import simulate

# Small network: A -> B -> C
graph = nx.DiGraph()

for node in ["A", "B", "C"]:
    graph.add_node(node, cap=10, buffer=100)

graph.add_edge("A", "B", cost=1)
graph.add_edge("B", "C", cost=1)

graph.graph["demands"] = {
    ("A", "C"): 5
}
graph.graph["waiting_cost"] = 1
graph.graph["unmet_penalty"] = 96

plan = [
    {"od": ["A", "C"], "edge": ["A", "B"], "flow": 5},
    {"od": ["A", "C"], "edge": ["B", "C"], "flow": 5},
]

# B has zero outgoing capacity during days 0 and 1.
scenario = {
    "demand_days": 1,
    "horizon": 6,
    "failure_start": 0,
    "failure_days": 2,
    "failed": {"B": 0.0},
}

result = simulate(graph, scenario, plan)

print("\nFAILED-HUB REGRESSION TEST")
print("Generated:", result["generated"])
print("Delivered:", result["delivered"])
print("Unmet:", result["unmet"])

# A must be able to send shipments into failed hub B.
# B cannot dispatch until its capacity recovers.
history = result["history"]

assert history[0]["in_transit"] == 5, (
    "Failed hub B should still accept incoming shipments."
)

assert history[1]["queued"] == 5, (
    "Shipments should wait at B while outgoing capacity is zero."
)

assert abs(result["delivered"] - 5) < 1e-6, (
    "All shipments should be delivered after B recovers."
)

assert abs(result["unmet"]) < 1e-6

print("\nFAILED-HUB TEST: PASS")