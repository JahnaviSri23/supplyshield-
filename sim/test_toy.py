from pathlib import Path
from time import perf_counter

import networkx as nx
import pandas as pd

from opt.c_toy_recovery import (
    build_toy_graph,
    fail_node,
    solve_lp,
    SRC,
    DST,
    DEMAND,
    PENALTY,
)
from sim.simulator import simulate


ROOT = Path(__file__).resolve().parents[1]


def main():
    graph = build_toy_graph()

    graph.graph["demands"] = {(SRC, DST): DEMAND}
    graph.graph["waiting_cost"] = 1.0
    graph.graph["unmet_penalty"] = PENALTY

    # Original route used by the "do nothing" strategy.
    original_path = nx.shortest_path(
        graph, SRC, DST, weight="cost"
    )

    internal_hubs = original_path[1:-1]
    if not internal_hubs:
        raise ValueError("Original route has no intermediate hub to fail.")

    affected_hub = internal_hubs[0]

    # Both plans are computed once and held fixed across capacity tests.
    normal_plan, normal_delivery = solve_lp(graph)

    failed_graph = fail_node(graph, "D", remaining=0.0)
    recovery_plan, recovery_delivery = solve_lp(failed_graph)

    print("Original route:", " -> ".join(original_path))
    print("On-route failure hub:", affected_hub)
    print("Normal plan daily delivery:", normal_delivery)
    print("Recovery plan daily delivery with D failed:", recovery_delivery)

    demand_days = 7
    expected_demand = DEMAND * demand_days
    rows = []

    for scale in [1.0, 1.2, 1.5]:
        cases = [
            ("no_failure", {}, None),
            ("on_route_failure", {affected_hub: 0.0}, None),
            ("D_fails_keep_routes", {"D": 0.0}, None),
            ("normal_plan_no_failure", {}, normal_plan),
            ("normal_plan_D_fails", {"D": 0.0}, normal_plan),
            ("recovery_plan_no_failure", {}, recovery_plan),
            ("D_fails_optimizer_plan", {"D": 0.0}, recovery_plan),
        ]

        for name, failed, plan in cases:
            scenario = {
                "failed": failed,
                "failure_start": 0,
                "failure_days": 3,
                "demand_days": demand_days,
                "horizon": 40,
                "capacity_scale": scale,
                "seed": 0,
            }

            started = perf_counter()
            result = simulate(graph, scenario, plan)
            seconds = perf_counter() - started

            assert abs(
                result["generated"] - expected_demand
            ) < 1e-6, f"Incorrect generated demand: {name}"

            assert abs(
                result["generated"]
                - result["delivered"]
                - result["unmet"]
            ) < 1e-6, f"Final accounting failed: {name}"

            # Check every day's traffic accounting.
            for day in result["history"]:
                accounted = (
                    day["delivered"]
                    + day["queued"]
                    + day["outside_backlog"]
                    + day["in_transit"]
                )
                assert abs(
                    day["generated"] - accounted
                ) < 1e-6, f"Daily accounting failed: {name}"

            # Check every no-failure plan, not just the original route.
            if not failed:
                assert result["unmet"] < 1e-6, (
                    f"No-failure traffic did not drain: {name}"
                )
                assert not result["recovery_censored"], (
                    f"No-failure drain time is censored: {name}"
                )

            rows.append({
                "case": name,
                "capacity_scale": scale,
                "shipping_cost": result["shipping_cost"],
                "waiting_cost": result["waiting_cost"],
                "delivered": result["delivered"],
                "unmet": result["unmet"],
                "recovery_days": result["recovery_days"],
                "recovery_censored": result["recovery_censored"],
                "total_cost": result["total_cost"],
                "runtime_seconds": seconds,
            })

    table = pd.DataFrame(rows)

    # Compare like-for-like cases at the same capacity scale.
    comparisons = []

    for scale in [1.0, 1.2, 1.5]:
        results = table.loc[
            table["capacity_scale"].eq(scale)
        ].set_index("case")

        def cost(case):
            return float(results.loc[case, "total_cost"])

        comparisons.append({
            "capacity_scale": scale,

            # Same original route, with and without on-route failure.
            "on_route_failure_extra_cost": (
                cost("on_route_failure") - cost("no_failure")
            ),

            # Same original route, with and without D failure.
            "D_failure_original_route_extra_cost": (
                cost("D_fails_keep_routes") - cost("no_failure")
            ),

            # Same normal optimized plan, with and without D failure.
            "D_failure_normal_plan_extra_cost": (
                cost("normal_plan_D_fails")
                - cost("normal_plan_no_failure")
            ),

            # Same recovery plan, with and without D failure.
            "D_failure_recovery_plan_extra_cost": (
                cost("D_fails_optimizer_plan")
                - cost("recovery_plan_no_failure")
            ),

            # Different plans under the SAME D-failure scenario.
            # Positive means the recovery plan costs less.
            "recovery_saving_during_D_failure": (
                cost("normal_plan_D_fails")
                - cost("D_fails_optimizer_plan")
            ),
        })

    comparison_table = pd.DataFrame(comparisons)

    output = ROOT / "experiments"
    output.mkdir(exist_ok=True)

    table.to_csv(
        output / "toy_simulator_checks.csv",
        index=False,
    )
    comparison_table.to_csv(
        output / "toy_simulator_comparisons.csv",
        index=False,
    )

    print("\nDAILY SIMULATOR RESULTS")
    print(table.round(4).to_string(index=False))

    print("\nMATCHED COMPARISONS")
    print(comparison_table.round(4).to_string(index=False))

    print("\nFlow-conservation and no-failure drain checks: PASS")
    print(
        "Recovery days measure backlog-drain time after demand "
        "stops and the specified failure ends."
    )
    print(
        "Negative recovery savings mean the recovery plan was "
        "more expensive in that scenario; results are not forced."
    )
    print("\nSaved:")
    print("experiments/toy_simulator_checks.csv")
    print("experiments/toy_simulator_comparisons.csv")


if __name__ == "__main__":
    main()