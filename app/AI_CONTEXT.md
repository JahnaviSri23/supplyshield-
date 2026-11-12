You are building a read-only demo website for a research project called SupplyShield.
Use Python + Streamlit + Plotly. Work ONLY inside the folder app/. Do not modify opt/, sim/, models/, src/, data/ or experiments/.
The app only reads precomputed result files. It never runs a solver.
Project: Delhivery-based Indian e-commerce logistics network (a core of 100 hubs and 292 directed lanes, 3 weeks of 2018 data). We compare recovery plans after one lane closes: "do nothing", "greedy", "preserve (affected flows only)" and "LP (all flows)".
Units: flow = legs per day, cost = leg-hours, one steady-state day, penalty = 96 leg-hours per undelivered leg.
Show this banner on every page: "Real network and transit times (Delhivery, 3 weeks, 2018). Closures are simulated. Capacity = 95th percentile of outgoing legs per day. Results apply only to the 100-hub core."
Data files (repo-relative):
- experiments/c_multiflow_closures.csv: lane, closed_lane_legs_per_day, plan, total_cost, extra_cost, extra_vs_best_normal, unmet, lp_seconds (lane looks like "IND000000ACB->IND131028AAB")
- experiments/c_real_lane_closures.csv: lane, daily_legs, normal_cost, plan, shipping, unmet, total_cost, seconds
- experiments/c_multiflow_plans.json: a list of tests, each {id, closed_lanes [[u,v]], penalty, demand [{od:[o,d], legs_per_day}], plans {plan name: [{od:[o,d], edge:[u,v], flow}]}, expected {plan name: {shipping, unmet, total_cost}}}
- experiments/c_uncertainty_summary.csv: plan, eval_mean, eval_cvar, eval_worst, unmet, plan_change_vs_det, realized_primary, realized_sens_pred, realized_sens_5legs
- experiments/c_uncertainty_intervals.csv: population, interval, lanes, test_legs, coverage_of_realized, mean_width, share_of_samples_inside
- experiments/c_uncertainty_results.csv: per-closure, per-seed detailed uncertainty results
- data/processed/core_nodes.csv: hub, name, state, lat, lon (some lat/lon empty), capacity_est
- data/processed/core_edges.csv: source_center, destination_center, leg_count, trip_count
Rules: validate that files and columns exist and show a clear error message if not; cache data loading; never invent numbers; every number on a page must come from a file.