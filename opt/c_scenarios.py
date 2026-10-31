import os
import pandas as pd
import c_toy_recovery as c

def safe_eval(G, flows, delivered):
    res = c.evaluate(G, flows, delivered)
    return (res[0], res[1]) if isinstance(res, tuple) else (res.get("total_cost", res), res.get("unmet", 0))

def run_scenarios():
    os.makedirs("experiments", exist_ok=True)
    rows = []

    # 1. Single Hub Failures (Full & Partial) across Penalty Costs
    for penalty in [8, 20, 40]:
        c.PENALTY = penalty
        for node in ["A", "B", "C", "D", "E", "F"]:
            for remaining in [0.0, 0.5]:
                G0 = c.build_toy_graph()
                G1 = c.fail_node(G0, node, remaining)

                for name, func in [("Do Nothing", lambda: c.do_nothing(G0, G1)), 
                                   ("Greedy", lambda: c.greedy(G1)), 
                                   ("Optimizer", lambda: c.solve_lp(G1))]:
                    fl, deliv = func()
                    cost, unmet = safe_eval(G1, fl, deliv)
                    rows.append({
                        "scenario_type": "single_hub",
                        "penalty": penalty,
                        "failed_hubs": f"{node} ({int((1-remaining)*100)}% down)",
                        "van_cost": 12,
                        "plan": name,
                        "total_cost": cost,
                        "unmet": unmet
                    })

    # 2. Double Hub Failures
    c.PENALTY = 20
    for n1, n2 in [("A", "E"), ("B", "D"), ("C", "F"), ("A", "C")]:
        G0 = c.build_toy_graph()
        G1 = c.fail_node(c.fail_node(G0, n1, 0.0), n2, 0.0)

        for name, func in [("Do Nothing", lambda: c.do_nothing(G0, G1)), 
                           ("Greedy", lambda: c.greedy(G1)), 
                           ("Optimizer", lambda: c.solve_lp(G1))]:
            fl, deliv = func()
            cost, unmet = safe_eval(G1, fl, deliv)
            rows.append({
                "scenario_type": "double_hub",
                "penalty": 20,
                "failed_hubs": f"{n1}+{n2} (100% down)",
                "van_cost": 12,
                "plan": name,
                "total_cost": cost,
                "unmet": unmet
            })

    # 3. Express Van Cost Variations (Tested on Hub D Failure)
    c.PENALTY = 20
    for van_cost in [12, 18, 19, 21, 25]:
        G0 = c.build_toy_graph()
        G0.edges[("S", "T")]["cost"] = van_cost
        G1 = c.fail_node(G0, "D", 0.0)

        for name, func in [("Do Nothing", lambda: c.do_nothing(G0, G1)), 
                           ("Greedy", lambda: c.greedy(G1)), 
                           ("Optimizer", lambda: c.solve_lp(G1))]:
            fl, deliv = func()
            cost, unmet = safe_eval(G1, fl, deliv)
            express_used = fl.get(("S", "T"), 0)
            rows.append({
                "scenario_type": "van_cost_sensitivity",
                "penalty": 20,
                "failed_hubs": f"D (van_cost={van_cost})",
                "van_cost": van_cost,
                "plan": name,
                "total_cost": cost,
                "unmet": unmet,
                "express_flow": express_used
            })

    df = pd.DataFrame(rows)
    output_path = "experiments/c_toy_scenarios.csv"
    df.to_csv(output_path, index=False)
    print(f"Successfully saved {len(df)} scenarios to '{output_path}'!\n")

    # --- PRINT SUMMARY TABLES ---
    print("=== AVERAGE TOTAL COST PER PLAN ===")
    avg_costs = df[df["scenario_type"] != "van_cost_sensitivity"].groupby("plan")["total_cost"].mean()
    print(avg_costs.round(2).to_string())
    
    print("\n=== EXPRESS VAN SENSITIVITY (Hub D Failure - Optimizer) ===")
    express_df = df[(df["scenario_type"] == "van_cost_sensitivity") & (df["plan"] == "Optimizer")][["van_cost", "express_flow", "total_cost"]]
    print(express_df.to_string(index=False))

if __name__ == "__main__":
    run_scenarios()