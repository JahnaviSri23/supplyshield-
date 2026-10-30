import os
import pandas as pd
import c_toy_recovery as c

def safe_evaluate(G, flows, delivered):
    """Helper function to cleanly unpack c.evaluate output regardless of return format."""
    res = c.evaluate(G, flows, delivered)
    if isinstance(res, tuple):
        # If evaluate returns (total_cost, unmet, ...) or (total_cost, unmet)
        return res[0], res[1]
    elif isinstance(res, dict):
        # If evaluate returns a dictionary
        return res.get("total_cost", res.get("cost")), res.get("unmet", res.get("unmet_demand"))
    return res, 0

def run_scenarios():
    os.makedirs("experiments", exist_ok=True)
    rows = []
    
    # -------------------------------------------------------------
    # 1. Single Hub Failures (Full & Partial) across Penalty Costs
    # -------------------------------------------------------------
    for penalty in [8, 20, 40]:
        c.PENALTY = penalty
        
        for node in ["A", "B", "C", "D", "E", "F"]:
            for remaining in [0.0, 0.5]:
                G0 = c.build_toy_graph()
                G1 = c.fail_node(G0, node, remaining)
                
                # Do Nothing
                dn_flows, dn_delivered = c.do_nothing(G0, G1)
                dn_cost, dn_unmet = safe_evaluate(G1, dn_flows, dn_delivered)
                rows.append({
                    "scenario_type": "single_hub",
                    "penalty": penalty,
                    "failed_hubs": f"{node} ({int((1-remaining)*100)}% down)",
                    "van_cost": 12,
                    "plan": "Do Nothing",
                    "total_cost": dn_cost,
                    "unmet": dn_unmet
                })
                
                # Greedy
                gr_flows, gr_delivered = c.greedy(G1)
                gr_cost, gr_unmet = safe_evaluate(G1, gr_flows, gr_delivered)
                rows.append({
                    "scenario_type": "single_hub",
                    "penalty": penalty,
                    "failed_hubs": f"{node} ({int((1-remaining)*100)}% down)",
                    "van_cost": 12,
                    "plan": "Greedy",
                    "total_cost": gr_cost,
                    "unmet": gr_unmet
                })
                
                # Optimizer
                lp_flows, lp_delivered = c.solve_lp(G1)
                lp_cost, lp_unmet = safe_evaluate(G1, lp_flows, lp_delivered)
                rows.append({
                    "scenario_type": "single_hub",
                    "penalty": penalty,
                    "failed_hubs": f"{node} ({int((1-remaining)*100)}% down)",
                    "van_cost": 12,
                    "plan": "Optimizer",
                    "total_cost": lp_cost,
                    "unmet": lp_unmet
                })

    # -------------------------------------------------------------
    # 2. Double Hub Failures (Simultaneous Outages)
    # -------------------------------------------------------------
    c.PENALTY = 20
    double_failure_pairs = [("A", "E"), ("B", "D"), ("C", "F"), ("A", "C")]
    
    for n1, n2 in double_failure_pairs:
        G0 = c.build_toy_graph()
        G1 = c.fail_node(c.fail_node(G0, n1, 0.0), n2, 0.0)
        
        dn_flows, dn_delivered = c.do_nothing(G0, G1)
        dn_cost, dn_unmet = safe_evaluate(G1, dn_flows, dn_delivered)
        rows.append({
            "scenario_type": "double_hub",
            "penalty": 20,
            "failed_hubs": f"{n1}+{n2} (100% down)",
            "van_cost": 12,
            "plan": "Do Nothing",
            "total_cost": dn_cost,
            "unmet": dn_unmet
        })
        
        gr_flows, gr_delivered = c.greedy(G1)
        gr_cost, gr_unmet = safe_evaluate(G1, gr_flows, gr_delivered)
        rows.append({
            "scenario_type": "double_hub",
            "penalty": 20,
            "failed_hubs": f"{n1}+{n2} (100% down)",
            "van_cost": 12,
            "plan": "Greedy",
            "total_cost": gr_cost,
            "unmet": gr_unmet
        })
        
        lp_flows, lp_delivered = c.solve_lp(G1)
        lp_cost, lp_unmet = safe_evaluate(G1, lp_flows, lp_delivered)
        rows.append({
            "scenario_type": "double_hub",
            "penalty": 20,
            "failed_hubs": f"{n1}+{n2} (100% down)",
            "van_cost": 12,
            "plan": "Optimizer",
            "total_cost": lp_cost,
            "unmet": lp_unmet
        })

    # -------------------------------------------------------------
    # 3. Express Van Cost Variations
    # -------------------------------------------------------------
    for van_cost in [12, 18, 25, 30, 35]:
        G0 = c.build_toy_graph()
        G0.edges[("S", "T")]["cost"] = van_cost
        
        G1 = c.fail_node(G0, "C", 0.0)
        
        lp_flows, lp_delivered = c.solve_lp(G1)
        lp_cost, lp_unmet = safe_evaluate(G1, lp_flows, lp_delivered)
        
        express_used = lp_flows.get(("S", "T"), 0)
        rows.append({
            "scenario_type": "van_cost_sensitivity",
            "penalty": 20,
            "failed_hubs": f"C (Express flow: {express_used})",
            "van_cost": van_cost,
            "plan": "Optimizer",
            "total_cost": lp_cost,
            "unmet": lp_unmet
        })

    df = pd.DataFrame(rows)
    output_path = "experiments/c_toy_scenarios.csv"
    df.to_csv(output_path, index=False)
    
    print(f"Successfully saved {len(df)} scenarios to '{output_path}'!\n")
    
    print("=== AVERAGE TOTAL COST PER PLAN ===")
    avg_costs = df[df["scenario_type"] != "van_cost_sensitivity"].groupby("plan")["total_cost"].mean()
    print(avg_costs.round(2).to_string())
    
    print("\n=== EXPRESS VAN SENSITIVITY (Hub C Failure) ===")
    express_df = df[df["scenario_type"] == "van_cost_sensitivity"][["van_cost", "total_cost", "unmet", "failed_hubs"]]
    print(express_df.to_string(index=False))

if __name__ == "__main__":
    run_scenarios()