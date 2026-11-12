"""
SupplyShield Streamlit Application
Multipage interactive dashboard for express logistics disruption recovery.

Pages:
1. Overview
2. Closure explorer
3. Network view
4. Uncertainty
5. Method and limitations
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure app directory and repo root are in sys.path to prevent import issues
_app_dir = Path(__file__).resolve().parent
if str(_app_dir) not in sys.path:
    sys.path.insert(0, str(_app_dir))
if str(_app_dir.parent) not in sys.path:
    sys.path.insert(0, str(_app_dir.parent))

try:
    import data
except ImportError:
    from app import data

st.set_page_config(
    page_title="SupplyShield — Disruption Recovery",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 18px 14px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 12px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3a8a;
        line-height: 1.2;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .custom-table-wrapper {
        overflow-x: auto;
        margin: 1rem 0;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
    }
    table.custom-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.92rem;
        text-align: left;
    }
    table.custom-table th {
        background-color: #f8fafc;
        color: #1e293b;
        font-weight: 600;
        padding: 10px 14px;
        border-bottom: 2px solid #cbd5e1;
    }
    table.custom-table td {
        padding: 10px 14px;
        border-bottom: 1px solid #f1f5f9;
        color: #334155;
    }
    table.custom-table tr:hover {
        background-color: #f1f5f9;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_table(df: pd.DataFrame) -> None:
    """
    Renders dataframe using st.dataframe when pyarrow is available,
    falling back seamlessly to a responsive HTML table when pyarrow native library is blocked.
    """
    try:
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        html = df.to_html(classes="custom-table", index=False, escape=False)
        st.markdown(f'<div class="custom-table-wrapper">{html}</div>', unsafe_allow_html=True)


def get_hub_name_map(nodes_df: pd.DataFrame) -> Dict[str, str]:
    """Maps hub code to descriptive hub name and state."""
    mapping = {}
    for _, row in nodes_df.iterrows():
        name = row["name"] if pd.notna(row["name"]) else row["hub"]
        state = f" ({row['state']})" if pd.notna(row["state"]) else ""
        mapping[row["hub"]] = f"{name}{state}"
    return mapping


def page_overview() -> None:
    data.render_banner()
    st.title("SupplyShield: Disruption Recovery in Express Freight")
    st.markdown(
        """
        **SupplyShield** benchmarks automated recovery strategies when critical freight corridors fail 
        in a large-scale express parcel logistics network. Using real shipment data from Delhivery 
        (100 core hubs and 292 directed lanes across 3 weeks in 2018), we evaluate how four distinct recovery 
        policies absorb disruptions across 10 high-impact lane closures.
        """
    )

    st.markdown("---")

    # 3 Metric Cards Computed Directly From Data
    num_hubs, num_lanes, num_closures = data.get_overview_metrics()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Core Network Hubs</div>
                <div class="metric-value">{num_hubs}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Directed Corridors (Lanes)</div>
                <div class="metric-value">{num_lanes}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Tested Lane Closures</div>
                <div class="metric-value">{num_closures}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Recovery Strategy Benchmark Summary
    st.subheader("Recovery Strategy Performance Benchmark")
    st.markdown(
        """
        Average performance across all 10 tested lane closure scenarios computed from 
        `experiments/c_multiflow_closures.csv`.
        """
    )

    summary_df = data.get_overview_summary_table()

    # Clean, formatted summary table
    display_df = summary_df.copy()
    display_df = display_df.rename(
        columns={
            "plan": "Recovery Plan",
            "total_cost": "Avg Total Cost (leg-hrs)",
            "extra_vs_best_normal": "Avg Extra vs Best Normal (leg-hrs)",
            "unmet": "Avg Unmet Demand (legs/day)",
            "lp_seconds": "Avg Solver Time (s)",
        }
    )

    # Format numeric columns cleanly
    formatted_table = display_df.copy()
    formatted_table["Avg Total Cost (leg-hrs)"] = formatted_table["Avg Total Cost (leg-hrs)"].map(
        lambda x: f"{x:,.2f}"
    )
    formatted_table["Avg Extra vs Best Normal (leg-hrs)"] = formatted_table[
        "Avg Extra vs Best Normal (leg-hrs)"
    ].map(lambda x: f"{x:,.2f}")
    formatted_table["Avg Unmet Demand (legs/day)"] = formatted_table[
        "Avg Unmet Demand (legs/day)"
    ].map(lambda x: f"{x:,.3f}")
    formatted_table["Avg Solver Time (s)"] = formatted_table["Avg Solver Time (s)"].map(
        lambda x: f"{x:,.3f}"
    )

    render_table(formatted_table)

    # Visualizations
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        fig_cost = go.Figure()
        fig_cost.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["total_cost"],
                name="Total Cost",
                marker_color="#1e3a8a",
                text=summary_df["total_cost"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_cost.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["extra_vs_best_normal"],
                name="Extra vs Best Normal",
                marker_color="#f59e0b",
                text=summary_df["extra_vs_best_normal"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_cost.update_layout(
            title="Average Cost Comparison by Recovery Plan",
            yaxis_title="Leg-Hours",
            barmode="group",
            height=380,
            margin=dict(l=40, r=20, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_cost, use_container_width=True)

    with col_chart2:
        fig_unmet = px.bar(
            summary_df,
            x="plan",
            y="unmet",
            color="plan",
            color_discrete_sequence=["#ef4444", "#3b82f6", "#10b981", "#6366f1"],
            title="Average Unmet Demand by Recovery Plan",
            labels={"plan": "Recovery Plan", "unmet": "Unmet Demand (legs/day)"},
            text=summary_df["unmet"].map(lambda x: f"{x:,.3f}"),
        )
        fig_unmet.update_traces(textposition="auto")
        fig_unmet.update_layout(
            height=380,
            showlegend=False,
            margin=dict(l=40, r=20, t=50, b=40),
            yaxis_title="Legs / Day",
        )
        st.plotly_chart(fig_unmet, use_container_width=True)

    # Key Findings Callout
    st.subheader("Key Findings")
    st.markdown(
        """
        - **Global LP Cuts Disruption Penalty by >50%**: Jointly re-optimizing all flows (`LP (all flows)`) reduces 
          extra cost vs best normal to **25.19 leg-hours**, compared to **51.64 leg-hours** for greedy and 
          isolated rerouting (`preserve`) — a **51.2% cost reduction**.
        - **Greedy and Preserve Fail to Free Bottlenecks**: `greedy` and `preserve (affected flows only)` 
          achieve identical average costs (2096.99 leg-hours) because displaced parcels compete for the same 
          immediate spare capacity without shifting unaffected flows to unlock alternate corridors.
        - **Cost of Inaction**: Doing nothing (`do nothing`) leaves an average of **5.50 legs/day undelivered**, 
          generating **539.22 extra leg-hours** of penalty and delay per disrupted day.
        - **Real-Time Solvability**: Multi-commodity LP re-optimization executes in an average of **0.81 seconds**, 
          making it fully practical for real-time dispatch systems.
        """
    )


def page_closure_explorer() -> None:
    data.render_banner()
    st.title("Closure Explorer 🔍")
    st.markdown(
        """
        Explore detailed recovery metrics and rerouted shipment flows across the **10 simulated 
        lane closure benchmarks**.
        """
    )

    closures_df = data.load_multiflow_closures()
    nodes_df = data.load_core_nodes()
    plans_data = data.load_multiflow_plans()
    hub_map = get_hub_name_map(nodes_df)

    # A selectbox lists the closed lanes from experiments/c_multiflow_closures.csv,
    # labelled with hub names from data/processed/core_nodes.csv where available.
    unique_lanes = closures_df["lane"].unique().tolist()
    closure_labels = []
    for lane in unique_lanes:
        src, dst = lane.split("->")
        src_name = hub_map.get(src, src)
        dst_name = hub_map.get(dst, dst)
        closure_labels.append(f"{src_name} → {dst_name} ({src} → {dst})")

    selected_idx = st.selectbox(
        "Select Closed Lane from Benchmark Scenarios:",
        range(len(unique_lanes)),
        format_func=lambda idx: closure_labels[idx],
    )
    selected_lane = unique_lanes[selected_idx]
    src_hub, dst_hub = selected_lane.split("->")
    src_name = hub_map.get(src_hub, src_hub)
    dst_name = hub_map.get(dst_hub, dst_hub)

    lane_rows = closures_df[closures_df["lane"] == selected_lane].copy()

    # Enforce standard plan order
    plan_order = ["do nothing", "greedy", "preserve (affected flows only)", "LP (all flows)"]
    lane_rows["order"] = lane_rows["plan"].apply(lambda p: plan_order.index(p) if p in plan_order else 99)
    lane_rows = lane_rows.sort_values("order").drop(columns=["order"])

    closed_legs = lane_rows["closed_lane_legs_per_day"].iloc[0]

    st.markdown("---")
    st.subheader(f"Closed Lane: {src_name} → {dst_name}")
    st.caption(f"Corridor Hubs: `{src_hub}` → `{dst_hub}`")

    # Compute Badge from Data: "LP total <= greedy total: PASS/FAIL"
    lp_row = lane_rows[lane_rows["plan"] == "LP (all flows)"]
    greedy_row = lane_rows[lane_rows["plan"] == "greedy"]
    lp_total = lp_row["total_cost"].iloc[0] if not lp_row.empty else float("inf")
    greedy_total = greedy_row["total_cost"].iloc[0] if not greedy_row.empty else float("-inf")
    is_pass = lp_total <= greedy_total
    status_text = "PASS" if is_pass else "FAIL"

    badge_bg = "#dcfce7" if is_pass else "#fee2e2"
    badge_color = "#15803d" if is_pass else "#b91c1c"
    badge_border = "#86efac" if is_pass else "#fca5a5"

    col_meta1, col_meta2 = st.columns([1, 2])
    with col_meta1:
        st.metric(
            label="Closed Lane Legs per Day",
            value=f"{closed_legs:.2f} legs/day",
        )
    with col_meta2:
        st.markdown(
            f"""
            <div style="margin-top: 10px;">
                <span style="display: inline-block; padding: 8px 18px; border-radius: 24px; font-weight: 700; font-size: 1.05rem; background-color: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border};">
                    LP total &le; greedy total: {status_text}
                </span>
                <span style="margin-left: 14px; color: #64748b; font-size: 0.95rem;">
                    (LP: {lp_total:,.1f} leg-hrs &le; Greedy: {greedy_total:,.1f} leg-hrs)
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Table with one row per plan (total_cost, extra_vs_best_normal, unmet legs)
    st.markdown("### Plan Comparison Table")
    plan_table = lane_rows[["plan", "total_cost", "extra_vs_best_normal", "unmet"]].copy()
    plan_table = plan_table.rename(
        columns={
            "plan": "Plan",
            "total_cost": "Total Cost (leg-hrs)",
            "extra_vs_best_normal": "Extra vs Best Normal (leg-hrs)",
            "unmet": "Unmet Legs (legs/day)",
        }
    )

    fmt_plan_table = plan_table.copy()
    fmt_plan_table["Total Cost (leg-hrs)"] = fmt_plan_table["Total Cost (leg-hrs)"].map(lambda x: f"{x:,.2f}")
    fmt_plan_table["Extra vs Best Normal (leg-hrs)"] = fmt_plan_table["Extra vs Best Normal (leg-hrs)"].map(
        lambda x: f"{x:,.2f}"
    )
    fmt_plan_table["Unmet Legs (legs/day)"] = fmt_plan_table["Unmet Legs (legs/day)"].map(lambda x: f"{x:,.3f}")

    render_table(fmt_plan_table)

    # Plotly bar chart of extra_vs_best_normal per plan
    st.markdown("### Extra Cost vs Best Normal per Plan")
    fig_bar = px.bar(
        lane_rows,
        x="plan",
        y="extra_vs_best_normal",
        color="plan",
        color_discrete_sequence=["#ef4444", "#3b82f6", "#10b981", "#6366f1"],
        title=f"Extra Cost vs Best Normal by Plan — {src_name} → {dst_name}",
        labels={"plan": "Recovery Plan", "extra_vs_best_normal": "Extra Cost vs Best Normal (leg-hours)"},
        text=lane_rows["extra_vs_best_normal"].map(lambda x: f"{x:,.1f}"),
    )
    fig_bar.update_traces(textposition="auto")
    fig_bar.update_layout(
        height=380,
        showlegend=False,
        margin=dict(l=40, r=20, t=50, b=40),
        yaxis_title="Extra Cost (leg-hours)",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # One-line definition of each plan
    st.markdown("### Recovery Plan Definitions")
    st.markdown(
        """
        - **`do nothing`**: Disrupted flow cannot traverse the closed lane and is stranded as unmet demand, incurring a 96 leg-hour penalty per undelivered leg.
        - **`greedy`**: Reroutes disrupted shipments locally along alternative shortest paths with available capacity, without adjusting any unaffected flows.
        - **`preserve (affected flows only)`**: Locks all unaffected shipments into their baseline routes and re-optimizes paths strictly for the displaced shipments.
        - **`LP (all flows)`**: Global multi-commodity flow linear program that re-optimizes all network flows jointly to unlock capacity and minimize total system cost.
        """
    )

    # Flow routing inspector (optional deep-dive)
    scenario_plan_obj = next(
        (p for p in plans_data if p["closed_lanes"][0][0] == src_hub and p["closed_lanes"][0][1] == dst_hub),
        None,
    )
    if scenario_plan_obj:
        with st.expander("🔍 Inspect Underlying Commodity Flow Allocations"):
            plans_dict = scenario_plan_obj.get("plans", {})
            chosen_plan = st.radio(
                "Select Plan to Inspect Routed Edge Flows:",
                list(plans_dict.keys()),
                horizontal=True,
            )
            flow_records = plans_dict.get(chosen_plan, [])
            flow_df = pd.DataFrame(
                [
                    {
                        "Origin Hub": item["od"][0],
                        "Origin Facility": hub_map.get(item["od"][0], item["od"][0]),
                        "Destination Hub": item["od"][1],
                        "Destination Facility": hub_map.get(item["od"][1], item["od"][1]),
                        "Traversed Edge": f"{item['edge'][0]} → {item['edge'][1]}",
                        "Allocated Flow (legs/day)": round(item["flow"], 4),
                    }
                    for item in flow_records
                ]
            )
            st.caption(f"Showing **{len(flow_df)}** active edge allocations for plan `{chosen_plan}`.")
            render_table(flow_df)


def page_network_view() -> None:
    data.render_banner()
    st.title("Network View 🗺️")
    st.markdown(
        """
        Geographic and topological view of the **100-hub core logistics network** and **292 directed lanes**.
        Markers are sized by estimated hub capacity (95th percentile outgoing legs/day).
        """
    )

    nodes_df = data.load_core_nodes()
    edges_df = data.load_core_edges()
    closures_df = data.load_multiflow_closures()
    hub_map = get_hub_name_map(nodes_df)

    # Coordinates lookup
    coords = {}
    for _, row in nodes_df.iterrows():
        if pd.notna(row["lat"]) and pd.notna(row["lon"]):
            coords[row["hub"]] = (float(row["lat"]), float(row["lon"]))

    closed_lanes_set = set(closures_df["lane"].unique())

    # Map with Plotly Scattergeo
    fig_map = go.Figure()

    # Add network lanes (edges)
    edge_lat = []
    edge_lon = []
    closed_lat = []
    closed_lon = []

    for _, row in edges_df.iterrows():
        u = row["source_center"] if "source_center" in row and pd.notna(row["source_center"]) else row["source"]
        v = row["destination_center"] if "destination_center" in row and pd.notna(row["destination_center"]) else row["destination"]
        lane_key = f"{u}->{v}"

        if u in coords and v in coords:
            lat1, lon1 = coords[u]
            lat2, lon2 = coords[v]
            if lane_key in closed_lanes_set:
                closed_lat.extend([lat1, lat2, None])
                closed_lon.extend([lon1, lon2, None])
            else:
                edge_lat.extend([lat1, lat2, None])
                edge_lon.extend([lon1, lon2, None])

    # Regular lanes trace
    fig_map.add_trace(
        go.Scattergeo(
            locationmode="country names",
            lon=edge_lon,
            lat=edge_lat,
            mode="lines",
            line=dict(width=1, color="rgba(75, 85, 99, 0.3)"),
            name="Network Lanes (292)",
            hoverinfo="none",
        )
    )

    # Disrupted lanes trace
    fig_map.add_trace(
        go.Scattergeo(
            locationmode="country names",
            lon=closed_lon,
            lat=closed_lat,
            mode="lines",
            line=dict(width=3, color="#ef4444"),
            name="Tested Closure Lanes (10)",
            hoverinfo="none",
        )
    )

    # Nodes trace
    located_nodes = nodes_df[nodes_df["lat"].notna() & nodes_df["lon"].notna()].copy()
    node_hover = [
        f"<b>{row['hub']}</b><br>{row['name']}<br>State: {row['state']}<br>Capacity: {row['capacity_est']} legs/day"
        for _, row in located_nodes.iterrows()
    ]

    fig_map.add_trace(
        go.Scattergeo(
            locationmode="country names",
            lon=located_nodes["lon"],
            lat=located_nodes["lat"],
            text=node_hover,
            hoverinfo="text",
            mode="markers",
            name="Core Hubs",
            marker=dict(
                size=located_nodes["capacity_est"] / 2.5 + 4,
                color=located_nodes["capacity_est"],
                colorscale="Blues",
                showscale=True,
                colorbar=dict(title="Capacity (legs/day)", x=1.02),
                line=dict(width=1, color="#1e293b"),
            ),
        )
    )

    fig_map.update_layout(
        geo=dict(
            scope="asia",
            center=dict(lat=22.5, lon=80.0),
            projection_scale=3.8,
            showland=True,
            landcolor="#f8fafc",
            showcountries=True,
            countrycolor="#cbd5e1",
            showsubunits=True,
            subunitcolor="#e2e8f0",
        ),
        title="Delhivery Core Freight Network Topology (100 Hubs & Tested Closures)",
        height=600,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )

    st.plotly_chart(fig_map, use_container_width=True)

    # Top Hubs and Lanes
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Top Hubs by Capacity")
        top_hubs = nodes_df.sort_values("capacity_est", ascending=False).head(10)
        fig_th = px.bar(
            top_hubs,
            x="capacity_est",
            y="hub",
            orientation="h",
            labels={"capacity_est": "Capacity (legs/day)", "hub": "Hub Code"},
            text="name",
            color="capacity_est",
            color_continuous_scale="Blues",
        )
        fig_th.update_layout(yaxis=dict(autorange="reversed"), height=360, showlegend=False)
        st.plotly_chart(fig_th, use_container_width=True)

    with col_t2:
        st.subheader("Top Lanes by Traffic Volume")
        top_edges = edges_df.sort_values("leg_count", ascending=False).head(10).copy()
        top_edges["lane"] = top_edges["source_center"] + " → " + top_edges["destination_center"]
        fig_te = px.bar(
            top_edges,
            x="leg_count",
            y="lane",
            orientation="h",
            labels={"leg_count": "Leg Count (3 weeks)", "lane": "Corridor"},
            color="leg_count",
            color_continuous_scale="Purples",
        )
        fig_te.update_layout(yaxis=dict(autorange="reversed"), height=360, showlegend=False)
        st.plotly_chart(fig_te, use_container_width=True)

    # Hubs Directory
    st.markdown("---")
    st.subheader("Hubs Directory & Metadata")
    search_query = st.text_input("Filter Hubs by Name, Code, or State:", "")
    filtered_nodes = nodes_df[
        nodes_df["hub"].str.contains(search_query, case=False, na=False)
        | nodes_df["name"].str.contains(search_query, case=False, na=False)
        | nodes_df["state"].str.contains(search_query, case=False, na=False)
    ]
    render_table(
        filtered_nodes[["hub", "name", "state", "capacity_est", "lat", "lon"]].rename(
            columns={
                "hub": "Hub Code",
                "name": "Facility Name",
                "state": "State",
                "capacity_est": "Est. Capacity (legs/day)",
                "lat": "Latitude",
                "lon": "Longitude",
            }
        )
    )


def page_uncertainty() -> None:
    data.render_banner()
    st.title("Uncertainty & Robust Optimization 🎲")
    st.markdown(
        """
        Transit times in real logistics operations are stochastic due to road congestion, vehicle maintenance, 
        and weather delays. This page presents empirical results from evaluating recovery policies under 
        **conformal prediction intervals** and **Conditional Value-at-Risk (CVaR)** optimization.
        """
    )

    summary_df = data.load_uncertainty_summary()
    intervals_df = data.load_uncertainty_intervals()
    results_df = data.load_uncertainty_results()

    st.markdown("---")
    st.subheader("Policy Comparison Under Transit Time Uncertainty")
    st.markdown(
        """
        Performance of 4 optimization policies across stochastic transit time realizations 
        (`experiments/c_uncertainty_summary.csv`):
        - **deterministic**: Solves assuming nominal expected transit times.
        - **point**: Optimization using point estimates from the machine-learned transit time model.
        - **expected**: Risk-neutral stochastic optimization minimizing expected total cost across scenarios.
        - **CVaR**: Risk-averse optimization penalizing the worst 10% tail outcomes (Conditional Value-at-Risk).
        """
    )

    disp_sum = summary_df.copy()
    disp_sum = disp_sum.rename(
        columns={
            "plan": "Policy",
            "eval_mean": "Eval Mean Cost (leg-hrs)",
            "eval_cvar": "Eval CVaR Worst 10% (leg-hrs)",
            "eval_worst": "Eval Worst-Case Cost (leg-hrs)",
            "unmet": "Unmet Flow (legs/day)",
            "plan_change_vs_det": "Plan Shift vs Det (L1)",
            "realized_primary": "Realized Cost (Primary)",
            "realized_sens_pred": "Realized Cost (Sens Pred)",
            "realized_sens_5legs": "Realized Cost (Sens 5-legs)",
        }
    )

    # Formatted display
    fmt_sum = disp_sum.copy()
    for col in [
        "Eval Mean Cost (leg-hrs)",
        "Eval CVaR Worst 10% (leg-hrs)",
        "Eval Worst-Case Cost (leg-hrs)",
        "Realized Cost (Primary)",
        "Realized Cost (Sens Pred)",
        "Realized Cost (Sens 5-legs)",
    ]:
        fmt_sum[col] = fmt_sum[col].map(lambda x: f"{x:,.2f}")
    fmt_sum["Unmet Flow (legs/day)"] = fmt_sum["Unmet Flow (legs/day)"].map(lambda x: f"{x:,.4f}")
    fmt_sum["Plan Shift vs Det (L1)"] = fmt_sum["Plan Shift vs Det (L1)"].map(lambda x: f"{x:,.4f}")

    render_table(fmt_sum)

    # Chart comparing Mean vs Tail Risk
    fig_unc = go.Figure()
    fig_unc.add_trace(
        go.Bar(
            x=summary_df["plan"],
            y=summary_df["eval_mean"],
            name="Mean Cost",
            marker_color="#3b82f6",
            text=summary_df["eval_mean"].map(lambda x: f"{x:,.1f}"),
            textposition="auto",
        )
    )
    fig_unc.add_trace(
        go.Bar(
            x=summary_df["plan"],
            y=summary_df["eval_cvar"],
            name="CVaR (Worst 10%)",
            marker_color="#f59e0b",
            text=summary_df["eval_cvar"].map(lambda x: f"{x:,.1f}"),
            textposition="auto",
        )
    )
    fig_unc.add_trace(
        go.Bar(
            x=summary_df["plan"],
            y=summary_df["eval_worst"],
            name="Worst-Case Cost",
            marker_color="#ef4444",
            text=summary_df["eval_worst"].map(lambda x: f"{x:,.1f}"),
            textposition="auto",
        )
    )
    fig_unc.update_layout(
        title="Cost Profiles Under Uncertainty (Mean vs Tail Risk)",
        yaxis_title="Leg-Hours",
        barmode="group",
        height=380,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_unc, use_container_width=True)

    st.markdown("---")
    st.subheader("Conformal Prediction Interval Calibration")
    st.markdown(
        """
        To guarantee reliable uncertainty envelopes without unrealistic distributional assumptions, 
        SupplyShield constructs **conformal prediction intervals** (`experiments/c_uncertainty_intervals.csv`).
        """
    )

    disp_int = intervals_df.rename(
        columns={
            "population": "Population",
            "interval": "Nominal Interval",
            "lanes": "Lanes Evaluated",
            "test_legs": "Test Legs Evaluated",
            "coverage_of_realized": "Empirical Coverage",
            "mean_width": "Mean Interval Width",
            "share_of_samples_inside": "Share Samples Inside",
        }
    )
    fmt_int = disp_int.copy()
    fmt_int["Empirical Coverage"] = fmt_int["Empirical Coverage"].map(lambda x: f"{x * 100:.2f}%")
    fmt_int["Share Samples Inside"] = fmt_int["Share Samples Inside"].map(lambda x: f"{x * 100:.2f}%")
    fmt_int["Mean Interval Width"] = fmt_int["Mean Interval Width"].map(lambda x: f"{x:.4f}")

    render_table(fmt_int)

    # Detailed Per-Seed Realization Explorer
    st.markdown("---")
    st.subheader("Scenario-Level Stochastic Simulation Results")
    st.markdown(
        f"Detailed evaluation records across **{results_df['seed'].nunique()} random seeds** "
        f"and **{results_df['closure'].nunique()} closures** from `experiments/c_uncertainty_results.csv`."
    )

    c_closures = results_df["closure"].unique().tolist()
    chosen_c = st.selectbox("Filter by Closure ID:", c_closures)
    subset_res = results_df[results_df["closure"] == chosen_c].copy()

    fig_box = px.box(
        subset_res,
        x="plan",
        y="eval_mean",
        color="plan",
        points="all",
        title=f"Evaluation Cost Distribution Across Seeds ({chosen_c})",
        labels={"plan": "Policy", "eval_mean": "Simulated Cost (leg-hrs)"},
    )
    fig_box.update_layout(height=360, showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)


def page_method_and_limitations() -> None:
    data.render_banner()
    st.title("Methodology & Limitations 📖")
    st.markdown(
        """
        This page details the mathematical formulation, experimental design, operational assumptions, 
        and research boundaries of the SupplyShield project.
        """
    )

    st.markdown("---")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.subheader("1. Core Network Formulation")
        st.markdown(
            """
            - **Network Core Extraction**: Extracted from 3 weeks of continuous telemetry from Delhivery (2018). 
              The core consists of **100 high-volume consolidation hubs** and **292 directed freight lanes**.
            - **Node Capacity Constraint**: Estimated as the **95th percentile of daily outgoing legs** observed 
              during baseline operation. Hubs cannot dispatch more flow than their demonstrated sorting capacity.
            - **Directed Corridors**: Each lane is characterized by median travel transit time and distance.
            """
        )

        st.subheader("2. Multi-Commodity Flow Optimization")
        st.markdown(
            """
            - **Objective Function**:
              $$\\min \\sum_{(u,v) \\in E} c_{uv} \\cdot f_{uv} + p \\sum_{(s,t) \\in OD} u_{st}$$
              Where $c_{uv}$ is transit time (hours), $f_{uv}$ is aggregated flow (legs/day), $u_{st}$ is undelivered flow, 
              and $p = 96\\text{ leg-hours}$ is the unmet delivery penalty.
            - **Conservation Constraints**: Enforces flow balance at every node for each origin-destination pair.
            - **Capacity Constraints**: Outgoing leg constraints per hub $v$: $\\sum_{w} f_{vw} \\le C_v$.
            """
        )

    with col_m2:
        st.subheader("3. Recovery Policies Benchmark")
        st.markdown(
            """
            1. **`do nothing`**: Disrupted flow on the severed link cannot proceed and is marked as unmet demand. 
               All unaffected flows continue on their baseline routes.
            2. **`greedy`**: Displaced shipments are greedily routed along the shortest available paths with remaining capacity, 
               without re-evaluating unaffected traffic.
            3. **`preserve (affected flows only)`**: Enforces strict operational continuity by freezing unaffected shipments, 
               solving an LP re-optimization strictly for the displaced commodity flows.
            4. **`LP (all flows)`**: Complete joint re-optimization. Enables unaffected flows to shift to alternate routes, 
               freeing critical capacity for the disrupted flows.
            """
        )

        st.subheader("4. Transit Time Uncertainty Framework")
        st.markdown(
            """
            - **Conformal Prediction**: Produces distribution-free, finite-sample prediction intervals for lane transit times.
            - **CVaR Optimization**: Minimizes Conditional Value-at-Risk at $\\alpha = 0.10$ to hedge against catastrophic tail delays.
            """
        )

    st.markdown("---")
    st.subheader("Modeling Units & Global Parameters")
    param_data = [
        {"Parameter": "Network Scope", "Value": "100 hubs, 292 directed lanes", "Source": "core_nodes.csv & core_edges.csv"},
        {"Parameter": "Flow Unit", "Value": "legs per day", "Source": "Steady-state daily volume"},
        {"Parameter": "Cost Unit", "Value": "leg-hours", "Source": "Transit time × flow"},
        {"Parameter": "Time Horizon", "Value": "One steady-state day", "Source": "Static 24-hour dispatch"},
        {"Parameter": "Penalty for Unmet Demand", "Value": "96 leg-hours / undelivered leg", "Source": "4 days equivalent shipping penalty"},
        {"Parameter": "Hub Capacity Threshold", "Value": "95th percentile outgoing legs", "Source": "Baseline empirical traffic"},
        {"Parameter": "Number of Closures Evaluated", "Value": "10 high-impact lanes", "Source": "c_multiflow_closures.csv"},
    ]
    render_table(pd.DataFrame(param_data))

    st.markdown("---")
    st.subheader("Assumptions & Research Limitations")
    st.markdown(
        """
        > [!IMPORTANT]
        > **Scope of Applicability**:
        > 1. **Core Network Only**: Results reflect the 100-hub inter-facility backbone. Regional feeder branches, 
        >    local delivery centers, and last-mile legs are excluded from this core model.
        > 2. **Steady-State Approximation**: Optimization assumes daily aggregated flows in steady-state equilibrium. 
        >    Dynamic intra-day dispatch schedules, driver shift limits, and multi-day compounding backlogs are omitted.
        > 3. **Single Complete Corridor Failures**: Tested disruptions model total lane cutoffs. Partial capacity degradation 
        >    and correlated multi-corridor weather catastrophes are subjects for future modeling.
        > 4. **Read-Only Architecture**: All recovery plans and optimization matrices were computed offline to ensure 
        >    instantaneous interactive demonstration without dynamic solver dependencies.
        """
    )


def main() -> None:
    st.sidebar.title("SupplyShield 🛡️")
    st.sidebar.markdown("**Express Logistics Disruption Recovery**")

    # Multipage Navigation
    pages = {
        "Overview": page_overview,
        "Closure explorer": page_closure_explorer,
        "Network view": page_network_view,
        "Uncertainty": page_uncertainty,
        "Method and limitations": page_method_and_limitations,
    }

    selection = st.sidebar.radio(
        "Navigation",
        list(pages.keys()),
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("📦 **Dataset**: Delhivery (3 weeks, 2018)")
    st.sidebar.caption("🌐 **Network**: 100 Hubs | 292 Lanes")
    st.sidebar.caption("⚡ **Optimization**: Multi-commodity Flow")

    # Render selected page
    page_func = pages[selection]
    page_func()


if __name__ == "__main__":
    main()
