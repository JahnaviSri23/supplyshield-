import json
import math
from collections import defaultdict
from pathlib import Path

from sim.test_core import build_core_graph

PLAN_FILE = Path("experiments/c_multiflow_plans.json")
STRATEGIES = ("do nothing", "greedy", "LP (all flows)")
TOL = 1e-6


def validate():
    graph = build_core_graph()

    with PLAN_FILE.open(encoding="utf-8") as f:
        scenarios = json.load(f)

    errors = []
    warnings = []

    if not isinstance(scenarios, list):
        raise ValueError("Expected a list of scenarios")

    if len(scenarios) != 10:
        errors.append(f"Expected 10 scenarios, found {len(scenarios)}")

    ids = [s.get("id") for s in scenarios]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate scenario IDs")

    for scenario in scenarios:
        sid = scenario["id"]
        demand = {}

        if scenario.get("penalty") != 96.0:
            errors.append(f"{sid}: unexpected penalty")

        for item in scenario["demand"]:
            od = tuple(item["od"])
            quantity = float(item["legs_per_day"])

            if len(od) != 2 or not all(node in graph for node in od):
                errors.append(f"{sid}: invalid demand OD {od}")
                continue

            if not math.isfinite(quantity) or quantity < 0:
                errors.append(f"{sid}: invalid demand quantity {od}")
                continue

            if od in demand:
                errors.append(f"{sid}: duplicate demand OD {od}")

            demand[od] = quantity

        closed = set()

        for lane in scenario["closed_lanes"]:
            edge = tuple(lane)

            if len(edge) != 2 or not graph.has_edge(*edge):
                errors.append(f"{sid}: invalid closed lane {edge}")

            closed.add(edge)

        if len(closed) != len(scenario["closed_lanes"]):
            errors.append(f"{sid}: duplicate closed lanes")

        for strategy in STRATEGIES:
            if strategy not in scenario["plans"]:
                errors.append(f"{sid}: missing strategy {strategy}")
                continue

            plan = scenario["plans"][strategy]
            balances = defaultdict(lambda: defaultdict(float))

            for record in plan:
                od = tuple(record["od"])
                edge = tuple(record["edge"])
                flow = float(record["flow"])

                if od not in demand:
                    errors.append(f"{sid}/{strategy}: unknown OD {od}")
                    continue

                if len(edge) != 2 or not graph.has_edge(*edge):
                    errors.append(f"{sid}/{strategy}: invalid edge {edge}")
                    continue

                if not math.isfinite(flow) or flow < 0:
                    errors.append(f"{sid}/{strategy}: invalid flow")
                    continue

                if edge in closed:
                    warnings.append(
                        f"{sid}/{strategy}: plan uses closed lane {edge}"
                    )

                u, v = edge
                balances[od][u] -= flow
                balances[od][v] += flow

            for od, quantity in demand.items():
                source, destination = od
                balance = balances[od]

                for node, value in balance.items():
                    if node not in (source, destination):
                        if abs(value) > TOL:
                            errors.append(
                                f"{sid}/{strategy}: flow conservation "
                                f"failed at {node} for {od}"
                            )

                routed = balance[destination]

                if routed < -TOL or routed > quantity + TOL:
                    errors.append(
                        f"{sid}/{strategy}: routed demand invalid "
                        f"for {od}: {routed} vs {quantity}"
                    )

                if abs(balance[source] + routed) > TOL:
                    errors.append(
                        f"{sid}/{strategy}: source/destination "
                        f"balance mismatch for {od}"
                    )

            print(
                f"{sid:>3} | {strategy:<15} | "
                f"{len(plan):>4} routing records checked"
            )

    print("\n=== Validation summary ===")
    print("Scenarios:", len(scenarios))
    print("Errors:", len(errors))
    print("Warnings:", len(warnings))

    for message in errors[:20]:
        print("ERROR:", message)

    for message in warnings[:10]:
        print("WARNING:", message)

    if errors:
        print("\nRESULT: FAIL")
        raise SystemExit(1)

    print("\nRESULT: PASS")


if __name__ == "__main__":
    validate()
