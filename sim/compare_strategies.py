import csv
import json
import time
from pathlib import Path

from sim.test_core import build_core_graph
from sim.simulator import simulate


OUTPUT = Path("experiments/person_a_strategy_comparison.csv")


def main():
    graph = build_core_graph()

    with open("experiments/c_multiflow_plans.json", encoding="utf-8") as f:
        scenarios = json.load(f)

    results = []

    for item in scenarios:
        graph.graph["demands"] = {
            tuple(record["od"]): float(record["legs_per_day"])
            for record in item["demand"]
        }

        graph.graph["unmet_penalty"] = float(item["penalty"])

        scenario = {
            "demand_days": 7,
            "horizon": 120,
            "failure_start": 0,
            "failure_days": 3,
            "capacity_scale": 1.0,
            "closed_lanes": item["closed_lanes"],
        }

        print("\nScenario:", item["id"])

        for strategy, plan in item["plans"].items():
            print("  Running:", strategy)

            start = time.perf_counter()
            result = simulate(graph, scenario, plan)
            runtime = time.perf_counter() - start

            final_day = result["history"][-1]

            row = {
                "scenario": item["id"],
                "strategy": strategy,
                "generated": result["generated"],
                "delivered": result["delivered"],
                "unmet": result["unmet"],
                "shipping_cost": result["shipping_cost"],
                "waiting_cost": result["waiting_cost"],
                "total_cost": result["total_cost"],
                "recovery_days": result["recovery_days"],
                "recovery_censored": result["recovery_censored"],
                "queued": final_day["queued"],
                "outside_backlog": final_day["outside_backlog"],
                "in_transit": final_day["in_transit"],
                "runtime_seconds": runtime,
            }

            results.append(row)

            print(
                "    Total cost:",
                round(result["total_cost"], 4),
                "| Unmet:",
                round(result["unmet"], 4),
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print("\n--------------------------------")
    print("Simulations completed:", len(results))
    print("Results saved:", OUTPUT)
    print("--------------------------------")


if __name__ == "__main__":
    main()