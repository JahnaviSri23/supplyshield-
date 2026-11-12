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
_app_dir = str(Path(__file__).resolve().parent)
if sys.path[0] != _app_dir:
    sys.path.insert(0, _app_dir)

try:
    import data
    if not hasattr(data, "get_hub_coordinates"):
        from app import data
except Exception:
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
        Node sizes reflect estimated hub capacity (95th percentile outgoing legs/day).
        """
    )

    nodes_df = data.load_core_nodes()
    edges_df = data.load_core_edges()
    plans_data = data.load_multiflow_plans()
    hub_map = get_hub_name_map(nodes_df)

    # Hub coordinates (lat/lon with NetworkX spring layout fallback for unlocated hubs)
    coords, is_approx = data.get_hub_coordinates()

    # Controls: Select Closure Scenario and Recovery Plan
    st.markdown("---")
    st.subheader("Interactive Scenario & Plan Inspection")

    col_ctrl1, col_ctrl2 = st.columns([3, 2])

    closure_options = []
    for p in plans_data:
        cid = p["id"]
        u, v = p["closed_lanes"][0]
        u_name = hub_map.get(u, u)
        v_name = hub_map.get(v, v)
        closure_options.append(f"{cid}: {u_name} → {v_name} ({u} → {v})")

    with col_ctrl1:
        selected_closure_idx = st.selectbox(
            "Select Simulated Lane Closure:",
            range(len(closure_options)),
            format_func=lambda idx: closure_options[idx],
        )

    selected_test = plans_data[selected_closure_idx]
    closed_u, closed_v = selected_test["closed_lanes"][0]
    closed_u_name = hub_map.get(closed_u, closed_u)
    closed_v_name = hub_map.get(closed_v, closed_v)

    available_plans = list(selected_test.get("plans", {}).keys())

    with col_ctrl2:
        selected_plan = st.selectbox(
            "Select Recovery Plan:",
            available_plans,
            index=available_plans.index("LP (all flows)") if "LP (all flows)" in available_plans else 0,
        )

    # Filter detour edges carrying flow for the closed OD pair (od == closed lane)
    raw_flows = selected_test.get("plans", {}).get(selected_plan, [])
    detour_items = [
        item for item in raw_flows
        if item.get("od") == [closed_u, closed_v] and item.get("flow", 0) > 0
    ]

    # Plotly Figure
    fig_map = go.Figure()

    # 1. Base Core Network Edges (light grey)
    edge_lons: List[Any] = []
    edge_lats: List[Any] = []
    for _, row in edges_df.iterrows():
        u = row["source_center"] if "source_center" in row and pd.notna(row["source_center"]) else row["source"]
        v = row["destination_center"] if "destination_center" in row and pd.notna(row["destination_center"]) else row["destination"]
        if u in coords and v in coords:
            edge_lons.extend([coords[u][0], coords[v][0], None])
            edge_lats.extend([coords[u][1], coords[v][1], None])

    fig_map.add_trace(
        go.Scattergeo(
            locationmode="country names",
            lon=edge_lons,
            lat=edge_lats,
            mode="lines",
            line=dict(width=1.0, color="rgba(203, 213, 225, 0.45)"),
            name="Core Network Edges (292)",
            hoverinfo="none",
        )
    )

    # 2. Closed Lane (Red)
    if closed_u in coords and closed_v in coords:
        fig_map.add_trace(
            go.Scattergeo(
                locationmode="country names",
                lon=[coords[closed_u][0], coords[closed_v][0]],
                lat=[coords[closed_u][1], coords[closed_v][1]],
                mode="lines+markers",
                line=dict(width=4.5, color="#ef4444"),
                marker=dict(size=8, color="#ef4444", symbol="x"),
                name=f"Closed Lane ({closed_u} → {closed_v})",
                hoverinfo="text",
                text=(
                    f"<b>CLOSED LANE</b><br>{closed_u} ({closed_u_name}) → {closed_v} ({closed_v_name})<br>"
                    f"Status: Blocked corridor"
                ),
            )
        )

    # 3. Detour Edges carrying flow for closed OD pair (Blue with width proportional to flow)
    max_detour_flow = max([item["flow"] for item in detour_items], default=1.0)
    for idx, item in enumerate(detour_items):
        u, v = item["edge"]
        flow_val = item["flow"]
        if u in coords and v in coords:
            # Width proportional to flow: scale between 2.5 and 9.0 px
            line_w = max(2.5, min(9.0, 2.5 + 6.0 * (flow_val / max_detour_flow)))
            u_name = hub_map.get(u, u)
            v_name = hub_map.get(v, v)
            fig_map.add_trace(
                go.Scattergeo(
                    locationmode="country names",
                    lon=[coords[u][0], coords[v][0]],
                    lat=[coords[u][1], coords[v][1]],
                    mode="lines",
                    line=dict(width=line_w, color="#2563eb"),
                    name="Detour Edges (Closed OD flow)" if idx == 0 else "",
                    showlegend=(idx == 0),
                    hoverinfo="text",
                    text=(
                        f"<b>DETOUR CORRIDOR</b><br>{u} ({u_name}) → {v} ({v_name})<br>"
                        f"Detour Flow: {flow_val:.4f} legs/day"
                    ),
                )
            )

    # 4. Hub Nodes (Node size = capacity_est)
    known_nodes = nodes_df[~nodes_df["hub"].map(is_approx)].copy()
    approx_nodes = nodes_df[nodes_df["hub"].map(is_approx)].copy()

    # Known coordinates hubs trace
    known_lons = [coords[h][0] for h in known_nodes["hub"]]
    known_lats = [coords[h][1] for h in known_nodes["hub"]]
    known_sizes = [float(cap) * 0.35 + 5 for cap in known_nodes["capacity_est"]]
    known_hover = [
        f"<b>{row['hub']}</b><br>{row['name']}<br>State: {row['state']}<br>Capacity: {row['capacity_est']} legs/day"
        for _, row in known_nodes.iterrows()
    ]

    fig_map.add_trace(
        go.Scattergeo(
            locationmode="country names",
            lon=known_lons,
            lat=known_lats,
            text=known_hover,
            hoverinfo="text",
            mode="markers",
            name="Hubs (Known Coordinates)",
            marker=dict(
                size=known_sizes,
                color="#1e3a8a",
                line=dict(width=1, color="#0f172a"),
                symbol="circle",
            ),
        )
    )

    # Approximate position hubs trace (NetworkX spring layout, seed=42)
    approx_lons = [coords[h][0] for h in approx_nodes["hub"]]
    approx_lats = [coords[h][1] for h in approx_nodes["hub"]]
    approx_sizes = [float(cap) * 0.4 + 7 for cap in approx_nodes["capacity_est"]]
    approx_hover = [
        f"<b>{row['hub']} (approximate position)</b><br>{row['name']}<br>State: {row['state']}<br>"
        f"Capacity: {row['capacity_est']} legs/day<br><i>Position estimated via NetworkX spring layout (seed=42)</i>"
        for _, row in approx_nodes.iterrows()
    ]

    fig_map.add_trace(
        go.Scattergeo(
            locationmode="country names",
            lon=approx_lons,
            lat=approx_lats,
            text=approx_hover,
            hoverinfo="text",
            mode="markers",
            name="Hubs (approximate position, seed=42)",
            marker=dict(
                size=approx_sizes,
                color="#f59e0b",
                line=dict(width=1.5, color="#b45309"),
                symbol="diamond",
            ),
        )
    )

    fig_map.update_layout(
        geo=dict(
            scope="asia",
            center=dict(lat=22.5, lon=80.0),
            projection_scale=3.85,
            showland=True,
            landcolor="#f8fafc",
            showcountries=True,
            countrycolor="#cbd5e1",
            showsubunits=True,
            subunitcolor="#e2e8f0",
        ),
        title=(
            f"Core Logistics Network: {closed_u_name} → {closed_v_name} Disruption "
            f"under '{selected_plan}'"
        ),
        height=620,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
    )

    st.plotly_chart(fig_map, use_container_width=True)

    # Detour Edges Clean Table
    st.markdown("### Detour Edges Carrying Disrupted OD Flow")
    st.markdown(
        f"Edges carrying redirected traffic for closed OD pair **{closed_u} → {closed_v}** "
        f"under policy **`{selected_plan}`**:"
    )

    if detour_items:
        detour_table_data = []
        for item in detour_items:
            u, v = item["edge"]
            detour_table_data.append(
                {
                    "Edge Source": u,
                    "Origin Facility": hub_map.get(u, u),
                    "Edge Destination": v,
                    "Destination Facility": hub_map.get(v, v),
                    "Detour Corridor": f"{u} → {v}",
                    "Flow (legs/day)": round(item["flow"], 4),
                }
            )
        detour_df = pd.DataFrame(detour_table_data)
        fmt_detour_df = detour_df.copy()
        fmt_detour_df["Flow (legs/day)"] = fmt_detour_df["Flow (legs/day)"].map(lambda x: f"{x:,.4f}")
        render_table(fmt_detour_df)

        total_detour_flow = sum(item["flow"] for item in detour_items)
        st.caption(
            f"Total active detour flow: **{total_detour_flow:,.4f} legs/day** "
            f"allocated across **{len(detour_items)}** network edges."
        )
    else:
        st.info(
            f"ℹ️ Under the **'{selected_plan}'** recovery policy, no alternative edges carry flow "
            f"for closed OD pair **{closed_u} → {closed_v}**; all disrupted shipments are stranded as unmet demand."
        )

    # Network Directory & Hub Capacity Summary
    st.markdown("---")
    st.subheader("Core Network Topology & Capacity Distribution")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
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
            title="Top 10 Hubs by Capacity (95th Percentile Outgoing Legs)",
        )
        fig_th.update_layout(yaxis=dict(autorange="reversed"), height=350, showlegend=False)
        st.plotly_chart(fig_th, use_container_width=True)

    with col_t2:
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
            title="Top 10 Lanes by Baseline Traffic Volume",
        )
        fig_te.update_layout(yaxis=dict(autorange="reversed"), height=350, showlegend=False)
        st.plotly_chart(fig_te, use_container_width=True)

    # Searchable Hubs Directory
    with st.expander("📋 Searchable 100-Hub Facility Directory"):
        search_query = st.text_input("Filter Hubs by Name, Code, or State:", "")
        filtered_nodes = nodes_df[
            nodes_df["hub"].str.contains(search_query, case=False, na=False)
            | nodes_df["name"].str.contains(search_query, case=False, na=False)
            | nodes_df["state"].str.contains(search_query, case=False, na=False)
        ].copy()
        filtered_nodes["Coordinate Status"] = filtered_nodes["hub"].map(
            lambda h: "Approximate (Spring Layout seed=42)" if is_approx.get(h, False) else "Verified Lat/Lon"
        )
        render_table(
            filtered_nodes[["hub", "name", "state", "capacity_est", "lat", "lon", "Coordinate Status"]].rename(
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
        Empirical evaluation of recovery policies under **transit time uncertainty**, comparing 
        deterministic planning against distribution-aware point estimates, expected-cost optimization, 
        and risk-averse CVaR (Conditional Value-at-Risk) optimization.
        """
    )

    summary_df = data.load_uncertainty_summary()
    intervals_df = data.load_uncertainty_intervals()
    results_df = data.load_uncertainty_results()

    st.markdown("---")
    st.subheader("Uncertainty Recovery Plans Comparison")
    st.markdown(
        """
        Comparison of the four uncertainty recovery plans (**`deterministic`**, **`point`**, **`expected`**, **`CVaR`**) 
        across simulated evaluation costs and out-of-sample realized scores (`experiments/c_uncertainty_summary.csv`):
        """
    )

    # 1. Comparison Table
    plan_comp_table = summary_df[
        [
            "plan",
            "eval_mean",
            "eval_cvar",
            "eval_worst",
            "realized_primary",
            "realized_sens_pred",
            "realized_sens_5legs",
        ]
    ].copy()

    plan_comp_table = plan_comp_table.rename(
        columns={
            "plan": "Plan",
            "eval_mean": "Avg Simulated Cost (eval_mean) [leg-hrs]",
            "eval_cvar": "CVaR 80% (eval_cvar) [leg-hrs]",
            "eval_worst": "Worst Scenario Cost (eval_worst) [leg-hrs]",
            "realized_primary": "Realized Primary [leg-hrs]",
            "realized_sens_pred": "Realized Sens Pred [leg-hrs]",
            "realized_sens_5legs": "Realized Sens 5-legs [leg-hrs]",
        }
    )

    fmt_comp_table = plan_comp_table.copy()
    for col in [
        "Avg Simulated Cost (eval_mean) [leg-hrs]",
        "CVaR 80% (eval_cvar) [leg-hrs]",
        "Worst Scenario Cost (eval_worst) [leg-hrs]",
        "Realized Primary [leg-hrs]",
        "Realized Sens Pred [leg-hrs]",
        "Realized Sens 5-legs [leg-hrs]",
    ]:
        fmt_comp_table[col] = fmt_comp_table[col].map(lambda x: f"{x:,.2f}")

    render_table(fmt_comp_table)

    # 2. Plotly Bar Charts
    st.markdown("### Cost Metrics Comparison Across Uncertainty Plans")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        fig_sim = go.Figure()
        fig_sim.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["eval_mean"],
                name="Avg Simulated (eval_mean)",
                marker_color="#3b82f6",
                text=summary_df["eval_mean"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_sim.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["eval_cvar"],
                name="CVaR 80% (eval_cvar)",
                marker_color="#f59e0b",
                text=summary_df["eval_cvar"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_sim.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["eval_worst"],
                name="Worst Scenario (eval_worst)",
                marker_color="#ef4444",
                text=summary_df["eval_worst"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_sim.update_layout(
            title="Simulated Cost & Tail Risk Profiles (leg-hours)",
            yaxis_title="Cost (leg-hours)",
            barmode="group",
            height=390,
            margin=dict(l=40, r=20, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_sim, use_container_width=True)

    with col_c2:
        fig_real = go.Figure()
        fig_real.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["realized_primary"],
                name="Realized Primary",
                marker_color="#10b981",
                text=summary_df["realized_primary"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_real.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["realized_sens_pred"],
                name="Realized Sens Pred",
                marker_color="#6366f1",
                text=summary_df["realized_sens_pred"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_real.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["realized_sens_5legs"],
                name="Realized Sens 5-legs",
                marker_color="#8b5cf6",
                text=summary_df["realized_sens_5legs"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_real.update_layout(
            title="Out-of-Sample Realized Scores (leg-hours)",
            yaxis_title="Cost (leg-hours)",
            barmode="group",
            height=390,
            margin=dict(l=40, r=20, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_real, use_container_width=True)

    # 3. Interval Diagnostics Table
    st.markdown("---")
    st.subheader("Conformal Prediction Interval Diagnostics")
    st.markdown(
        """
        Interval diagnostic validation metrics from `experiments/c_uncertainty_intervals.csv`:
        """
    )

    disp_int = intervals_df[
        [
            "population",
            "interval",
            "lanes",
            "test_legs",
            "coverage_of_realized",
            "mean_width",
            "share_of_samples_inside",
        ]
    ].copy()

    disp_int = disp_int.rename(
        columns={
            "population": "Population",
            "interval": "Interval",
            "lanes": "Lanes",
            "test_legs": "Test Legs",
            "coverage_of_realized": "Coverage of Realized",
            "mean_width": "Mean Width",
            "share_of_samples_inside": "Share of Samples Inside",
        }
    )

    fmt_int = disp_int.copy()
    fmt_int["Coverage of Realized"] = fmt_int["Coverage of Realized"].map(lambda x: f"{x * 100:.2f}%")
    fmt_int["Share of Samples Inside"] = fmt_int["Share of Samples Inside"].map(lambda x: f"{x * 100:.2f}%")
    fmt_int["Mean Width"] = fmt_int["Mean Width"].map(lambda x: f"{x:.4f}")

    render_table(fmt_int)

    # 4. Explicit Methodological Note
    st.info(
        "ℹ️ **Note on Interval Calibration & Sampling Spread**: "
        "Lane intervals are weighted averages of representative-route conformal intervals "
        "(not formally calibrated at the lane level) and sampling spread is derived from the "
        "90% interval with the 50% interval used as a diagnostic consistency check."
    )

    # 5. Detailed Per-Seed Realization Explorer
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
        Comprehensive documentation of the mathematical modeling, experimental parameters, cost decomposition, 
        hub failure scope justification, and structural limitations of the SupplyShield research project, 
        drawn directly from `docs/c_notes.md`.
        """
    )

    st.markdown("---")

    # 1. Model Assumptions & Units
    st.subheader("1. Core Network Assumptions & Units")
    st.markdown(
        """
        - **Core Network**: 100 logistics hubs and 292 directed lanes extracted from the Delhivery India dataset 
          (3 weeks of 2018 operations; 14 training days used for baseline estimation).
        - **Flow & Demand Units**: Steady-state **legs per day** (`trips / 14` from `data/processed/core_edges.csv`).
        - **Time & Cost Units**: Transit times are measured in **hours**; objective and routing costs are measured in 
          **leg-hours per day** ($\\sum_{e} \\text{base\\_hours}_e \\cdot \\text{mult}_e \\cdot f_e$).
        - **Time Horizon**: One steady-state day (static single-period network flow).
        - **Node Capacity Constraint**: Outgoing capacity per hub is set to the **95th percentile of historical outgoing legs per day** 
          (`capacity_est` in `data/processed/core_nodes.csv`).
        - **Undelivered-Leg Penalty**: **96 leg-hours per undelivered leg** (`PENALTY_HOURS = 96.0`). 
          *(Note: an earlier sensitivity run at penalty 48 and 24 produced the exact same plan ranking).*
        - **Disruption Scope**: Single-lane closures evaluated one lane at a time (`L01`–`L10`).
        - **Lane Risk Independence**: In stochastic evaluation, lane travel-time multipliers are sampled independently per lane.
        """
    )

    # 2. The Four Recovery Plans
    st.markdown("---")
    st.subheader("2. Formal Recovery Plan Definitions")
    st.markdown(
        """
        1. **`do nothing`**: Keeps all normal-day baseline flows fixed; any flow previously routed over the closed lane $(u^*, v^*)$ 
           becomes unmet demand and incurs the **96 leg-hours/leg** penalty.
        2. **`greedy`**: Reroutes only the affected flows from the closed lane sequentially onto shortest available residual-capacity 
           detour paths without re-optimizing unaffected flows.
        3. **`preserve (affected flows only)`**: Keeps all unaffected OD flows locked at their normal-day baseline routing and solves an LP 
           to optimally reroute only the OD pairs affected by the closed lane within remaining hub capacities.
        4. **`LP (all flows)`**: Solves a global multi-OD linear program across all 292 directed lanes simultaneously to minimize 
           total shipping leg-hours plus unmet-demand penalties.
        """
    )

    # 3. Starting-Point Decomposition
    st.markdown("---")
    st.subheader("3. Cost Decomposition: Global Optimization vs. Closure Response")
    st.markdown(
        """
        Across the 10 tested single-lane closures (`experiments/c_multiflow_closures.csv`):
        - **Normal-Day Baseline Cost**: **2,045.3 leg-hours/day** (minimum-cost LP baseline).
        - **Mean Extra Cost over Own Baseline (`extra_cost`)**:
          - `LP (all flows)`: **25.2 leg-hours/day**
          - `greedy`: **28.3 leg-hours/day**
          - `do nothing`: **515.9 leg-hours/day**
        - **Fair Comparison Against Best Normal Baseline (`extra_vs_best_normal`)**:
          - `LP (all flows)`: **25.2 leg-hours/day**
          - `greedy`: **51.6 leg-hours/day**
        """
    )

    st.markdown(
        """
        $$\\text{Total Gap } (26.4) = \\underbrace{\\text{Starting-Point Gap } (23.3)}_{\\text{baseline routing inefficiency unrelated to closures}} + \\underbrace{\\text{Closure Response } (3.1)}_{\\text{true rerouting advantage under closure}}$$
        
        - **Starting-Point Gap (23.3 leg-hours/day)**: Out of the 26.4 leg-hour difference between greedy and global LP, 
          **23.3 leg-hours/day** stem from historical baseline flow assignments already being slightly suboptimal relative to 
          a global LP before any lane closes.
        - **Closure Response (3.1 leg-hours/day)**: Only **3.1 leg-hours/day** represent the genuine incremental benefit of 
          global LP optimization over greedy detouring during a single-lane closure.
        - **High-Impact Bottleneck Exceptions**: On major bottleneck corridors (such as `IND560099AAB -> IND560300AAA`), 
          re-optimizing background flows provides major savings, outperforming greedy by **66.5 leg-hours** during disruption.
        """
    )

    # 4. Hub Failure vs. Lane Closure Justification
    st.markdown("---")
    st.subheader("4. Why Full Hub Failures Are Out of Scope")
    st.markdown(
        """
        - Out of **9,969** total training trips in the dataset, **4,436** have both origin and destination inside the 100-hub core.
        - Within the core, **237 of 297 OD pairs (80%)** are served by a direct single-leg route (mean of 1.13 legs per trip).
        - Because the optimizer models demand as aggregated steady-state lane flows (`legs/day`) rather than end-to-end multi-leg itineraries, 
          shutting down an entire intermediate hub cannot accurately propagate multi-leg trip cancellations upstream or downstream 
          without switching to a full trip-based formulation. Single-lane closures isolate capacity and detour trade-offs cleanly within the lane-flow model.
        """
    )

    hub_traffic_table = pd.DataFrame(
        [
            {"Hub Code": "IND000000ACB", "Facility Name": "Gurgaon Bilaspur HB", "% Ends Here (Unavoidable Loss)": "23.6%", "% Passes Through (Reroutable)": "1.6%"},
            {"Hub Code": "IND562132AAA", "Facility Name": "Bangalore Nelamangala H", "% Ends Here (Unavoidable Loss)": "18.3%", "% Passes Through (Reroutable)": "0.6%"},
            {"Hub Code": "IND421302AAG", "Facility Name": "Bhiwandi Mankoli HB", "% Ends Here (Unavoidable Loss)": "15.0%", "% Passes Through (Reroutable)": "0.1%"},
            {"Hub Code": "IND560099AAB", "Facility Name": "Bangalore Bommasandra", "% Ends Here (Unavoidable Loss)": "11.0%", "% Passes Through (Reroutable)": "0.5%"},
            {"Hub Code": "IND411033AAA", "Facility Name": "Pune Dighi", "% Ends Here (Unavoidable Loss)": "9.5%", "% Passes Through (Reroutable)": "0.6%"},
            {"Hub Code": "IND560300AAA", "Facility Name": "Bangalore Attibele H", "% Ends Here (Unavoidable Loss)": "8.4%", "% Passes Through (Reroutable)": "0.0%"},
            {"Hub Code": "IND400072AAB", "Facility Name": "Mumbai Sakinaka", "% Ends Here (Unavoidable Loss)": "6.6%", "% Passes Through (Reroutable)": "0.0%"},
            {"Hub Code": "IND160002AAC", "Facility Name": "Chandigarh Mehmudpur", "% Ends Here (Unavoidable Loss)": "5.5%", "% Passes Through (Reroutable)": "0.0%"},
            {"Hub Code": "IND600056AAB", "Facility Name": "Chennai Poonamallee", "% Ends Here (Unavoidable Loss)": "5.8%", "% Passes Through (Reroutable)": "0.0%"},
            {"Hub Code": "IND000000ACT", "Facility Name": "Delhi Okhla", "% Ends Here (Unavoidable Loss)": "2.5%", "% Passes Through (Reroutable)": "0.0%"},
        ]
    )
    render_table(hub_traffic_table)
    st.caption(
        "Traffic with `% Ends Here` represents unavoidable volume loss during hub failure because the facility is the shipment's origin or destination. "
        "Because `% Passes Through` is near zero across top hubs, hub failure offers minimal recoverable rerouting potential."
    )

    # 5. Structural Limitations
    st.markdown("---")
    st.subheader("5. Model Limitations & Assumptions")
    st.markdown(
        """
        1. **Static Steady-State Horizon**: Models a single representative 24-hour day without multi-day queue spillover, rollover freight, or compounding backlog across consecutive days.
        2. **Independent Lane Multipliers**: Stochastic scenarios sample lane travel-time multipliers independently per lane, ignoring spatial weather or regional corridor correlation.
        3. **Deterministic Outgoing Hub Capacities**: Uses a fixed 95th-percentile outgoing leg cap per hub and does not model receiving-dock bottlenecks, sorting equipment breakdowns, or dynamic shift staffing.
        4. **Core Subgraph Boundary**: Results apply strictly to the 100-hub, 292-lane core network; external regional feeder branches and last-mile delivery legs outside the core are excluded.
        5. **Read-Only Architecture**: All recovery plans and optimization matrices were precomputed offline; the dashboard operates exclusively in read-only mode without executing solvers in real time.
        """
    )

    # 6. Viva / Defense Q&A
    st.markdown("---")
    st.subheader("6. Defense & Viva Conceptual Q&A")

    with st.expander("Q1: What is a flow, a capacity, and a penalty in your real-graph LP?"):
        st.markdown(
            """
            - **Flow**: Daily truck-legs allocated along a directed lane $(u, v)$ for a specific demand pair.
            - **Capacity**: Maximum estimated leg capacity per day for lane $(u, v)$ / outgoing hub, derived from historical baseline volume (`capacity_est`).
            - **Penalty**: Cost incurred per unit of unmet demand (**96 leg-hours per undelivered leg**), ensuring the LP prefers rerouting over dropping traffic unless rerouting cost exceeds 96 hours.
            """
        )

    with st.expander("Q2: What does `preserve` (affected flows only) do, and why can the LP never be worse than it?"):
        st.markdown(
            """
            - **Preserve Plan**: Freezes all unaffected baseline flows from the no-closure LP state and only reroutes the flows directly impacted by a lane closure within remaining capacity.
            - **LP Dominance**: The LP performs a global joint re-optimization over all flows simultaneously. Because `preserve` is a restricted subset of the LP's feasible decision space, the LP cost is guaranteed to be $\\le$ the `preserve` plan cost ($\\text{LP} \\le \\text{preserve}$).
            """
        )

    with st.expander("Q3: Why was the LP's advantage over `greedy` mostly a starting-point gap?"):
        st.markdown(
            """
            - Out of the 26.4 leg-hours/day total advantage (`51.6` vs `25.2`), **23.3 leg-hours** already exist on a normal day because historical baseline flows aren't globally LP-optimal; only **3.1 leg-hours/day** represent the genuine incremental benefit of global LP optimization over greedy detouring during a single-lane closure.
            """
        )

    with st.expander("Q4: Why do hub failures need trip-based demand instead of lane-flow demand?"):
        st.markdown(
            """
            - Hub failures require complete multi-leg trip itineraries because a hub failure cancels all originating and terminating shipments while allowing intermediate passing-through trips to detour. Without trip-level origin-destination mapping, passing traffic cannot be separated from endpoint traffic.
            """
        )

    with st.expander("Q5: What is unrealistic about the optimization model?"):
        st.markdown(
            """
            - It assumes a single steady-state day with no multi-day queue carryover, treats lane congestion multipliers as statistically independent rather than spatially correlated, and uses a deterministic 95th-percentile hub capacity cap.
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
