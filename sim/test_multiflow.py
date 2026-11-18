import networkx as nx
from sim.simulator import simulate

# Create a small network
graph = nx.DiGraph()

for node in ["A", "B", "C", "D"]:
    graph.add_node(node, cap=100, buffer=200)

graph.add_edge("A", "B", cost=2)
graph.add_edge("B", "D", cost=3)
graph.add_edge("C", "B", cost=2)

# Two different origin-destination demands
graph.graph["demands"] = {
    ("A", "D"): 10,
    ("C", "D"): 15,
}

graph.graph["waiting_cost"] = 1
graph.graph["unmet_penalty"] = 96

# Multi-OD recovery plan
plan = [
    {"od": ["A", "D"], "edge": ["A", "B"], "flow": 10},
    {"od": ["A", "D"], "edge": ["B", "D"], "flow": 10},
    {"od": ["C", "D"], "edge": ["C", "B"], "flow": 15},
    {"od": ["C", "D"], "edge": ["B", "D"], "flow": 15},
]

scenario = {
    "demand_days": 7,
    "horizon": 30,
    "failure_days": 0,
}

result = simulate(graph, scenario, plan)

print("\nMULTI-OD SIMULATOR TEST")
print("Generated:", result["generated"])
print("Delivered:", result["delivered"])
print("Unmet:", result["unmet"])
print("Shipping cost:", result["shipping_cost"])
print("Total cost:", result["total_cost"])
print("Recovery days:", result["recovery_days"])

assert abs(result["generated"] - 175) < 1e-6
assert abs(result["delivered"] - 175) < 1e-6
assert result["unmet"] == 0

print("\nMULTI-OD TEST: PASS")