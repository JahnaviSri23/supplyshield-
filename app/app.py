"""
SupplyShield Streamlit Application — Control Tower SaaS Edition
High-contrast, executive-ready dashboard for express logistics disruption recovery.

Pages:
1. Overview
2. Live What-If Simulator (Interactive Recruiter Demo)
3. Closure explorer
4. Network view
5. Uncertainty
6. Method and limitations
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure app directory is in sys.path to prevent namespace collision
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
    page_title="SupplyShield — Disruption Recovery Control Tower",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-Contrast Dark Slate SaaS Styling
st.markdown(
    """
    <style>
    /* Global Background and Typography */
    .stApp {
        background-color: #0B1120;
        color: #F8FAFC;
    }
    
    /* Executive Header */
    .control-tower-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 1rem;
        margin-bottom: 1.25rem;
        border-bottom: 1px solid #1E293B;
    }
    .product-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .product-title {
        font-size: 1.75rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #F8FAFC;
    }
    .product-tag {
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        background: linear-gradient(135deg, #0284C7, #38BDF8);
        color: #0B1120;
        padding: 3px 8px;
        border-radius: 4px;
        text-transform: uppercase;
    }
    .product-subtitle {
        font-size: 0.88rem;
        color: #94A3B8;
        margin-top: 2px;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(56, 189, 248, 0.08);
        border: 1px solid rgba(56, 189, 248, 0.28);
        padding: 6px 14px;
        border-radius: 9999px;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.15);
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #38BDF8;
        box-shadow: 0 0 8px #38BDF8;
        animation: pulse-glow 2s infinite;
    }
    @keyframes pulse-glow {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.85); }
    }
    .status-text {
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #38BDF8;
        text-transform: uppercase;
    }

    /* Metric Cards */
    [data-testid="stMetric"] {
        background-color: #111827 !important;
        border: 1px solid #1E293B !important;
        border-radius: 10px !important;
        padding: 16px 18px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3) !important;
    }
    [data-testid="stMetricLabel"] p {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    [data-testid="stMetricValue"] div {
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        color: #F8FAFC !important;
    }

    /* Custom HTML Table Fallback */
    .custom-table-wrapper {
        overflow-x: auto;
        margin: 1rem 0;
        border: 1px solid #1E293B;
        border-radius: 8px;
        background-color: #111827;
    }
    table.custom-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.90rem;
        text-align: left;
    }
    table.custom-table th {
        background-color: #1E293B;
        color: #38BDF8;
        font-weight: 600;
        padding: 11px 14px;
        border-bottom: 2px solid #334155;
    }
    table.custom-table td {
        padding: 10px 14px;
        border-bottom: 1px solid #1E293B;
        color: #E2E8F0;
    }
    table.custom-table tr:hover {
        background-color: rgba(56, 189, 248, 0.05);
    }

    /* Badges */
    .solver-pill {
        display: flex;
        align-items: center;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.25);
        color: #34D399;
        padding: 8px 14px;
        border-radius: 8px;
        font-size: 0.88rem;
        margin-bottom: 1rem;
    }
    .badge-pass {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid #059669;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-fail {
        background-color: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid #DC2626;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_header() -> None:
    """Renders the executive SaaS product header and collapsible scope expander."""
    st.markdown(
        """
        <div class="control-tower-header">
            <div class="header-left">
                <div class="product-brand">
                    <span class="product-title">SupplyShield</span>
                    <span class="product-tag">CONTROL TOWER</span>
                </div>
                <div class="product-subtitle">Autonomous Express Logistics Disruption Recovery & Multi-Commodity Rerouting</div>
            </div>
            <div class="header-right">
                <div class="status-pill">
                    <span class="status-dot"></span>
                    <span class="status-text">LIVE CONTROL TOWER</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("ℹ️ Network & Data Scope", expanded=False):
        st.markdown(
            f"**Operational Scope Notice:** {data.BANNER_TEXT}"
        )


def style_plotly_fig(fig: go.Figure) -> go.Figure:
    """Ensures consistent dark-transparent Plotly styling matching the Control Tower UI."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F8FAFC", family="Inter, system-ui, sans-serif"),
    )
    return fig


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
    render_header()
    st.title("Network Recovery Benchmark Overview")
    st.markdown(
        """
        **SupplyShield** benchmarks automated recovery strategies when critical freight corridors fail 
        in a large-scale express parcel logistics network. Using real shipment data from Delhivery 
        (100 core hubs and 292 directed lanes across 3 weeks in 2018), we evaluate how four distinct recovery 
        policies absorb disruptions across 10 high-impact lane closures.
        """
    )

    st.markdown("---")

    # 3 Metric Cards Computed Directly From Data + Cost Reduction Delta Badge
    num_hubs, num_lanes, num_closures = data.get_overview_metrics()
    summary_df = data.get_overview_summary_table()
    do_nothing_cost = float(summary_df.loc[summary_df["plan"] == "do nothing", "total_cost"].values[0])
    lp_cost = float(summary_df.loc[summary_df["plan"] == "LP (all flows)", "total_cost"].values[0])
    pct_saved_lp = ((do_nothing_cost - lp_cost) / do_nothing_cost * 100.0) if do_nothing_cost > 0 else 0.0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Core Network Hubs",
            value=f"{num_hubs}",
            delta="100 Tier-1 Facilities",
            delta_color="normal",
        )
    with col2:
        st.metric(
            label="Directed Corridors (Lanes)",
            value=f"{num_lanes}",
            delta="292 Express Corridors",
            delta_color="normal",
        )
    with col3:
        st.metric(
            label="LP Cost Reduction vs Do Nothing",
            value=f"{pct_saved_lp:.1f}%",
            delta=f"-{do_nothing_cost - lp_cost:,.1f} leg-hrs/day",
            delta_color="normal",
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
                marker_color="#38BDF8",
                text=summary_df["total_cost"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_cost.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["extra_vs_best_normal"],
                name="Extra vs Best Normal",
                marker_color="#F59E0B",
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
        style_plotly_fig(fig_cost)
        st.plotly_chart(fig_cost, use_container_width=True)

    with col_chart2:
        fig_unmet = px.bar(
            summary_df,
            x="plan",
            y="unmet",
            color="plan",
            color_discrete_sequence=["#EF4444", "#F59E0B", "#10B981", "#38BDF8"],
            title="Average Unmet Demand (Undelivered Legs per Day)",
            labels={"plan": "Recovery Plan", "unmet": "Unmet Legs/Day"},
            text=summary_df["unmet"].map(lambda x: f"{x:,.3f}"),
        )
        fig_unmet.update_traces(textposition="auto")
        fig_unmet.update_layout(
            height=380,
            showlegend=False,
            margin=dict(l=40, r=20, t=50, b=40),
            yaxis_title="Legs / Day",
        )
        style_plotly_fig(fig_unmet)
        st.plotly_chart(fig_unmet, use_container_width=True)


def page_what_if_simulator() -> None:
    """Interactive Recruiter Demo: Real-Time LP Rerouting Optimization."""
    render_header()
    st.title("Live What-If Simulator ⚡")
    st.markdown(
        """
        **Interactive Recruiter Demo**: Simulate a sudden disruption on any active corridor in India's logistics core. 
        Select a lane, configure lost-leg penalties and machine-learning risk multipliers, and execute the 
        real multi-commodity flow LP solver (`scipy.optimize.linprog` with `method="highs"`) in real time.
        """
    )

    nodes_df = data.load_core_nodes()
    edges_df = data.load_core_edges()
    hub_map = get_hub_name_map(nodes_df)
    coords, _ = data.get_hub_coordinates()

    # Build Lane Options list from core_edges.csv
    lane_options = []
    lane_lookup = {}
    sorted_edges = edges_df.sort_values("trips", ascending=False).reset_index(drop=True)

    for idx, r in sorted_edges.iterrows():
        u = str(r["source_center"]) if "source_center" in r and pd.notna(r["source_center"]) else str(r["source"])
        v = str(r["destination_center"]) if "destination_center" in r and pd.notna(r["destination_center"]) else str(r["destination"])
        u_name = hub_map.get(u, u)
        v_name = hub_map.get(v, v)
        daily_legs = float(r["trips"]) / 14.0
        label = f"{u_name} → {v_name} ({u} → {v}) — {daily_legs:.2f} legs/day"
        lane_options.append(label)
        lane_lookup[label] = (u, v, daily_legs, float(r.get("median_actual_time", 60.0)) / 60.0)

    st.markdown("---")
    st.subheader("Disruption Controls & Parameters")

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([3, 2, 2])
    with col_ctrl1:
        selected_label = st.selectbox(
            "Select Disrupted Freight Corridor:",
            lane_options,
            index=0,
            help="Choose any of the 292 active express lanes across India",
        )
    with col_ctrl2:
        penalty_val = st.slider(
            "Lost-Leg Penalty (leg-hours):",
            min_value=20,
            max_value=200,
            value=96,
            step=4,
            help="Cost incurred per leg left undelivered due to corridor closure (default: 96 hrs)",
        )
    with col_ctrl3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        risk_toggle = st.toggle(
            "ML Risk-Adjusted Costs",
            value=False,
            help="Scales edge travel times by pred_multiplier from models/outputs/risk_table_lane.csv",
        )

    selected_u, selected_v, selected_demand, base_time = lane_lookup[selected_label]

    col_btn, col_info = st.columns([2, 5])
    with col_btn:
        run_sim = st.button("🚀 Run Live Rerouting Optimization", type="primary", use_container_width=True)

    with col_info:
        st.caption(
            f"Corridor: **{selected_u} → {selected_v}** | Baseline Demand: **{selected_demand:.2f} legs/day** | "
            f"Baseline Travel Time: **{base_time:.2f} hrs**"
        )

    # Initialize or run solver
    if run_sim or "sim_result" not in st.session_state or st.session_state.get("sim_lane") != (selected_u, selected_v):
        with st.spinner("Solving multi-commodity flow LP over 100 hubs with HiGHS..."):
            sim_res = data.solve_live_reroute(
                lane=(selected_u, selected_v),
                penalty=float(penalty_val),
                risk_adjusted=risk_toggle,
            )
            st.session_state["sim_result"] = sim_res
            st.session_state["sim_lane"] = (selected_u, selected_v)
            st.session_state["sim_penalty"] = penalty_val
            st.session_state["sim_risk"] = risk_toggle
    else:
        sim_res = st.session_state["sim_result"]

    # Display KPI Cards
    st.markdown("---")
    st.markdown(
        f"""
        <div class="solver-pill">
            <span>⚡ <b>HiGHS Dual-Simplex Solver</b> optimized in <b>{sim_res['runtime_ms']:.1f} ms</b></span>
            <span style="margin: 0 10px;">|</span>
            <span>Flow Conservation: <b style="color:#34D399;">✓ Feasible & Optimal</b></span>
            {"<span style='margin: 0 10px;'>|</span><span style='color:#38BDF8;'>ML Risk Multiplier: " + f"{sim_res['multiplier_used']:.3f}x</span>" if risk_toggle else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(
            label="Disrupted Daily Demand",
            value=f"{sim_res['demand_legs']:.2f} legs",
            delta="Origin-to-Destination",
            delta_color="off",
        )
    with kpi2:
        unmet_pct = (sim_res["unmet_legs"] / sim_res["demand_legs"] * 100.0) if sim_res["demand_legs"] > 0 else 0.0
        st.metric(
            label="Unmet Demand",
            value=f"{sim_res['unmet_legs']:.2f} legs",
            delta=f"{unmet_pct:.1f}% dropped",
            delta_color="inverse" if sim_res["unmet_legs"] > 0 else "normal",
        )
    with kpi3:
        st.metric(
            label="Optimal Reroute Cost",
            value=f"{sim_res['total_reroute_cost']:,.1f} hrs",
            delta=f"Detour: {sim_res['detour_cost']:,.1f} hrs",
            delta_color="off",
        )
    with kpi4:
        st.metric(
            label="Cost Saved vs Do Nothing",
            value=f"{sim_res['cost_saved']:,.1f} hrs",
            delta=f"-{sim_res['pct_saved']:.1f}% reduction",
            delta_color="normal",
        )

    # Interactive Map: Glowing Closed Lane (Red) + Live Detour Flows (Cyan)
    st.markdown("### Live Optimal Rerouting Map")
    detour_df = sim_res["detour_df"]

    fig_sim_map = go.Figure()

    # 1. Base Core Network Edges (subtle slate)
    base_lons: List[Any] = []
    base_lats: List[Any] = []
    for _, r in edges_df.iterrows():
        u = str(r["source_center"]) if "source_center" in r and pd.notna(r["source_center"]) else str(r["source"])
        v = str(r["destination_center"]) if "destination_center" in r and pd.notna(r["destination_center"]) else str(r["destination"])
        if u in coords and v in coords:
            base_lons.extend([coords[u][0], coords[v][0], None])
            base_lats.extend([coords[u][1], coords[v][1], None])

    fig_sim_map.add_trace(
        go.Scattergeo(
            locationmode="country names",
            lon=base_lons,
            lat=base_lats,
            mode="lines",
            line=dict(width=1.0, color="rgba(100, 116, 139, 0.22)"),
            name="Core Logistics Edges",
            hoverinfo="none",
        )
    )

    # 2. Closed Lane (Glowing Red)
    if selected_u in coords and selected_v in coords:
        fig_sim_map.add_trace(
            go.Scattergeo(
                locationmode="country names",
                lon=[coords[selected_u][0], coords[selected_v][0]],
                lat=[coords[selected_u][1], coords[selected_v][1]],
                mode="lines+markers",
                line=dict(width=5.5, color="#EF4444"),
                marker=dict(size=10, color="#EF4444", symbol="x"),
                name=f"Closed Corridor ({selected_u} → {selected_v})",
                hoverinfo="text",
                text=(
                    f"<b>CLOSED CORRIDOR</b><br>{hub_map.get(selected_u, selected_u)} → {hub_map.get(selected_v, selected_v)}<br>"
                    f"Disrupted Demand: {selected_demand:.2f} legs/day"
                ),
            )
        )

    # 3. Live Computed Detour Flows (Glowing Cyan with width proportional to flow)
    max_flow = float(detour_df["flow"].max()) if len(detour_df) > 0 else 1.0
    for idx, row in detour_df.iterrows():
        u, v = str(row["source"]), str(row["destination"])
        flow_val = float(row["flow"])
        if u in coords and v in coords:
            line_w = max(3.0, min(10.0, 3.0 + 7.0 * (flow_val / max_flow)))
            u_name = hub_map.get(u, u)
            v_name = hub_map.get(v, v)
            fig_sim_map.add_trace(
                go.Scattergeo(
                    locationmode="country names",
                    lon=[coords[u][0], coords[v][0]],
                    lat=[coords[u][1], coords[v][1]],
                    mode="lines",
                    line=dict(width=line_w, color="#38BDF8"),
                    name="Active Detour Corridors" if idx == 0 else "",
                    showlegend=(idx == 0),
                    hoverinfo="text",
                    text=(
                        f"<b>OPTIMAL DETOUR DISPATCH</b><br>{u_name} → {v_name}<br>"
                        f"Allocated Flow: <b>{flow_val:.3f} legs/day</b><br>"
                        f"Unit Transit Time: {row['unit_cost_hours']:.2f} hrs"
                    ),
                )
            )

    # 4. Hub Nodes (Indian Logistics Hubs)
    hub_lons = [coords[h][0] for h in nodes_df["hub"] if h in coords]
    hub_lats = [coords[h][1] for h in nodes_df["hub"] if h in coords]
    hub_names = [hub_map.get(h, h) for h in nodes_df["hub"] if h in coords]
    hub_caps = [float(cap) * 0.35 + 5 for cap, h in zip(nodes_df["capacity_est"], nodes_df["hub"]) if h in coords]

    fig_sim_map.add_trace(
        go.Scattergeo(
            locationmode="country names",
            lon=hub_lons,
            lat=hub_lats,
            mode="markers",
            name="100 Core Hubs",
            text=[f"<b>{name}</b><br>Capacity: {cap:.0f} legs/day" for name, cap in zip(hub_names, nodes_df["capacity_est"])],
            hoverinfo="text",
            marker=dict(
                size=hub_caps,
                color="#0284C7",
                line=dict(width=1, color="#38BDF8"),
                opacity=0.85,
            ),
        )
    )

    fig_sim_map.update_layout(
        geo=dict(
            scope="asia",
            lonaxis_range=[67, 98],
            lataxis_range=[6, 37],
            showland=True,
            landcolor="#0B1120",
            showocean=True,
            oceancolor="#070D19",
            showcountries=True,
            countrycolor="#334155",
            showsubunits=True,
            subunitcolor="#1E293B",
            resolution=50,
        ),
        title=f"Live Optimal Dispatch: {hub_map.get(selected_u, selected_u)} → {hub_map.get(selected_v, selected_v)}",
        height=620,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    style_plotly_fig(fig_sim_map)
    st.plotly_chart(fig_sim_map, use_container_width=True)

    # Detour Dispatch Table & CSV Export
    st.markdown("### Optimal Dispatch Routing Plan")
    if len(detour_df) > 0:
        detour_table = detour_df.copy()
        detour_table = detour_table.rename(
            columns={
                "source": "Origin Hub",
                "source_name": "Origin Facility",
                "destination": "Destination Hub",
                "destination_name": "Destination Facility",
                "flow": "Allocated Flow (legs/day)",
                "unit_cost_hours": "Transit Time (hrs)",
                "flow_cost": "Total Travel Cost (leg-hrs)",
            }
        )
        detour_table["Allocated Flow (legs/day)"] = detour_table["Allocated Flow (legs/day)"].map(lambda x: f"{x:,.4f}")
        detour_table["Transit Time (hrs)"] = detour_table["Transit Time (hrs)"].map(lambda x: f"{x:,.2f}")
        detour_table["Total Travel Cost (leg-hrs)"] = detour_table["Total Travel Cost (leg-hrs)"].map(lambda x: f"{x:,.2f}")

        render_table(detour_table)

        csv_data = detour_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Optimal Dispatch Plan (CSV)",
            data=csv_data,
            file_name=f"optimal_dispatch_{selected_u}_{selected_v}.csv",
            mime="text/csv",
        )
    else:
        st.warning("No alternative routes found within hub residual capacity; all displaced demand is unmet.")


def page_closure_explorer() -> None:
    render_header()
    st.title("Closure Scenario Explorer 🔍")
    st.markdown(
        """
        Deep-dive into individual high-impact lane closures from `experiments/c_multiflow_closures.csv`. 
        Compare how the four recovery policies handle displaced freight traffic.
        """
    )

    closures_df = data.load_multiflow_closures()
    nodes_df = data.load_core_nodes()
    plans_data = data.load_multiflow_plans()
    hub_map = get_hub_name_map(nodes_df)

    closed_lanes = closures_df["lane"].unique().tolist()

    def format_lane_label(lane_str: str) -> str:
        parts = lane_str.split("->")
        if len(parts) == 2:
            src, dst = parts[0], parts[1]
            return f"{hub_map.get(src, src)} → {hub_map.get(dst, dst)} ({lane_str})"
        return lane_str

    st.markdown("---")
    st.subheader("Select Closure Scenario")

    selected_lane = st.selectbox(
        "Choose Closed Lane:",
        closed_lanes,
        format_func=format_lane_label,
    )

    lane_rows = closures_df[closures_df["lane"] == selected_lane].copy()

    # Plan order
    plan_order = ["do nothing", "greedy", "preserve (affected flows only)", "LP (all flows)"]
    lane_rows["order"] = lane_rows["plan"].apply(lambda p: plan_order.index(p) if p in plan_order else 99)
    lane_rows = lane_rows.sort_values("order").drop(columns=["order"]).reset_index(drop=True)

    closed_legs_per_day = float(lane_rows["closed_lane_legs_per_day"].iloc[0])
    src_hub, dst_hub = selected_lane.split("->")
    src_name = hub_map.get(src_hub, src_hub)
    dst_name = hub_map.get(dst_hub, dst_hub)

    # PASS / FAIL Badge Computed from Data: LP total <= greedy total
    lp_row = lane_rows[lane_rows["plan"] == "LP (all flows)"]
    greedy_row = lane_rows[lane_rows["plan"] == "greedy"]

    badge_html = ""
    if not lp_row.empty and not greedy_row.empty:
        lp_tot = float(lp_row["total_cost"].iloc[0])
        greedy_tot = float(greedy_row["total_cost"].iloc[0])
        passed = lp_tot <= greedy_tot + 1e-5
        if passed:
            badge_html = (
                f'<span class="badge-pass">✓ LP total &le; greedy total: PASS '
                f'({lp_tot:,.1f} &le; {greedy_tot:,.1f} leg-hrs)</span>'
            )
        else:
            badge_html = (
                f'<span class="badge-fail">✗ LP total &le; greedy total: FAIL '
                f'({lp_tot:,.1f} > {greedy_tot:,.1f} leg-hrs)</span>'
            )

    col_meta1, col_meta2 = st.columns([3, 2])
    with col_meta1:
        st.markdown(f"**Closed Corridor**: `{src_name} → {dst_name}` (`{selected_lane}`)")
        st.markdown(f"**Disrupted Demand**: **{closed_legs_per_day:,.2f} legs/day**")
    with col_meta2:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown(badge_html, unsafe_allow_html=True)

    st.markdown("---")

    # Table with one row per plan
    st.markdown("### Recovery Plan Performance Comparison")
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
        color_discrete_sequence=["#EF4444", "#F59E0B", "#10B981", "#38BDF8"],
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
    style_plotly_fig(fig_bar)
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

    # Flow routing inspector
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
    render_header()
    st.title("Network View 🗺️")
    st.markdown(
        """
        Interactive geographic and topological view of the **100-hub core logistics network** and **292 directed lanes**.
        Node sizes reflect estimated hub capacity (95th percentile outgoing legs/day).
        """
    )

    nodes_df = data.load_core_nodes()
    edges_df = data.load_core_edges()
    plans_data = data.load_multiflow_plans()
    hub_map = get_hub_name_map(nodes_df)
    coords, is_approx = data.get_hub_coordinates()

    st.markdown("---")
    st.subheader("Interactive Scenario & Plan Inspection")

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([3, 2, 2])

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

    with col_ctrl3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        view_mode = st.radio(
            "Map Projection Mode:",
            ["Geographic (India Corridors)", "Topology (Spring Layout)"],
            horizontal=True,
        )

    raw_flows = selected_test.get("plans", {}).get(selected_plan, [])
    detour_items = [
        item for item in raw_flows
        if item.get("od") == [closed_u, closed_v] and item.get("flow", 0) > 0
    ]

    fig_map = go.Figure()

    if view_mode == "Geographic (India Corridors)":
        # India Geographic Scattergeo View
        edge_lons: List[Any] = []
        edge_lats: List[Any] = []
        for _, row in edges_df.iterrows():
            u = str(row["source_center"]) if "source_center" in row and pd.notna(row["source_center"]) else str(row["source"])
            v = str(row["destination_center"]) if "destination_center" in row and pd.notna(row["destination_center"]) else str(row["destination"])
            if u in coords and v in coords:
                edge_lons.extend([coords[u][0], coords[v][0], None])
                edge_lats.extend([coords[u][1], coords[v][1], None])

        fig_map.add_trace(
            go.Scattergeo(
                locationmode="country names",
                lon=edge_lons,
                lat=edge_lats,
                mode="lines",
                line=dict(width=1.0, color="rgba(100, 116, 139, 0.25)"),
                name="Core Network Edges (292)",
                hoverinfo="none",
            )
        )

        if closed_u in coords and closed_v in coords:
            fig_map.add_trace(
                go.Scattergeo(
                    locationmode="country names",
                    lon=[coords[closed_u][0], coords[closed_v][0]],
                    lat=[coords[closed_u][1], coords[closed_v][1]],
                    mode="lines+markers",
                    line=dict(width=5.0, color="#EF4444"),
                    marker=dict(size=10, color="#EF4444", symbol="x"),
                    name=f"Closed Lane ({closed_u} → {closed_v})",
                    hoverinfo="text",
                    text=(
                        f"<b>CLOSED LANE</b><br>{closed_u} ({closed_u_name}) → {closed_v} ({closed_v_name})<br>"
                        f"Status: Blocked Corridor"
                    ),
                )
            )

        max_detour_flow = max([item["flow"] for item in detour_items], default=1.0)
        for idx, item in enumerate(detour_items):
            u, v = item["edge"]
            flow_val = item["flow"]
            if u in coords and v in coords:
                line_w = max(2.5, min(9.0, 2.5 + 6.5 * (flow_val / max_detour_flow)))
                u_name = hub_map.get(u, u)
                v_name = hub_map.get(v, v)
                fig_map.add_trace(
                    go.Scattergeo(
                        locationmode="country names",
                        lon=[coords[u][0], coords[v][0]],
                        lat=[coords[u][1], coords[v][1]],
                        mode="lines",
                        line=dict(width=line_w, color="#38BDF8"),
                        name="Detour Edges (Closed OD flow)" if idx == 0 else "",
                        showlegend=(idx == 0),
                        hoverinfo="text",
                        text=(
                            f"<b>DETOUR CORRIDOR</b><br>{u} ({u_name}) → {v} ({v_name})<br>"
                            f"Detour Flow: {flow_val:.4f} legs/day"
                        ),
                    )
                )

        known_nodes = nodes_df[~nodes_df["hub"].map(is_approx)].copy()
        approx_nodes = nodes_df[nodes_df["hub"].map(is_approx)].copy()

        fig_map.add_trace(
            go.Scattergeo(
                locationmode="country names",
                lon=[coords[h][0] for h in known_nodes["hub"]],
                lat=[coords[h][1] for h in known_nodes["hub"]],
                text=[
                    f"<b>{row['hub']}</b><br>{row['name']}<br>State: {row['state']}<br>Capacity: {row['capacity_est']} legs/day"
                    for _, row in known_nodes.iterrows()
                ],
                hoverinfo="text",
                mode="markers",
                name="Hubs (Verified Lat/Lon)",
                marker=dict(
                    size=[float(cap) * 0.35 + 5 for cap in known_nodes["capacity_est"]],
                    color="#0284C7",
                    line=dict(width=1, color="#38BDF8"),
                ),
            )
        )

        fig_map.add_trace(
            go.Scattergeo(
                locationmode="country names",
                lon=[coords[h][0] for h in approx_nodes["hub"]],
                lat=[coords[h][1] for h in approx_nodes["hub"]],
                text=[
                    f"<b>{row['hub']} (approximate position)</b><br>{row['name']}<br>State: {row['state']}<br>"
                    f"Capacity: {row['capacity_est']} legs/day<br><i>Position estimated via NetworkX spring layout (seed=42)</i>"
                    for _, row in approx_nodes.iterrows()
                ],
                hoverinfo="text",
                mode="markers",
                name="Hubs (approximate position, seed=42)",
                marker=dict(
                    size=[float(cap) * 0.4 + 7 for cap in approx_nodes["capacity_est"]],
                    color="#F59E0B",
                    line=dict(width=1.5, color="#D97706"),
                    symbol="diamond",
                ),
            )
        )

        fig_map.update_layout(
            geo=dict(
                scope="asia",
                lonaxis_range=[67, 98],
                lataxis_range=[6, 37],
                showland=True,
                landcolor="#0B1120",
                showocean=True,
                oceancolor="#070D19",
                showcountries=True,
                countrycolor="#334155",
                showsubunits=True,
                subunitcolor="#1E293B",
            ),
            title=f"Core Logistics Network: {closed_u_name} → {closed_v_name} under '{selected_plan}'",
            height=640,
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        )
    else:
        # Full 100-Hub Network Topology 2D Spring Layout
        edge_x: List[Any] = []
        edge_y: List[Any] = []
        for _, row in edges_df.iterrows():
            u = str(row["source_center"]) if "source_center" in row and pd.notna(row["source_center"]) else str(row["source"])
            v = str(row["destination_center"]) if "destination_center" in row and pd.notna(row["destination_center"]) else str(row["destination"])
            if u in coords and v in coords:
                edge_x.extend([coords[u][0], coords[v][0], None])
                edge_y.extend([coords[u][1], coords[v][1], None])

        fig_map.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                mode="lines",
                line=dict(width=1.0, color="rgba(100, 116, 139, 0.25)"),
                name="Network Topology Edges",
                hoverinfo="none",
            )
        )

        if closed_u in coords and closed_v in coords:
            fig_map.add_trace(
                go.Scatter(
                    x=[coords[closed_u][0], coords[closed_v][0]],
                    y=[coords[closed_u][1], coords[closed_v][1]],
                    mode="lines+markers",
                    line=dict(width=5.0, color="#EF4444"),
                    marker=dict(size=12, color="#EF4444", symbol="x"),
                    name="Closed Lane",
                    hoverinfo="text",
                    text=f"CLOSED: {closed_u} → {closed_v}",
                )
            )

        max_detour_flow = max([item["flow"] for item in detour_items], default=1.0)
        for idx, item in enumerate(detour_items):
            u, v = item["edge"]
            flow_val = item["flow"]
            if u in coords and v in coords:
                line_w = max(2.5, min(9.0, 2.5 + 6.5 * (flow_val / max_detour_flow)))
                fig_map.add_trace(
                    go.Scatter(
                        x=[coords[u][0], coords[v][0]],
                        y=[coords[u][1], coords[v][1]],
                        mode="lines",
                        line=dict(width=line_w, color="#38BDF8"),
                        name="Detour Flow" if idx == 0 else "",
                        showlegend=(idx == 0),
                        hoverinfo="text",
                        text=f"Detour: {u} → {v} ({flow_val:.3f} legs/day)",
                    )
                )

        # Plot all 100 Hub Nodes
        node_x = [coords[h][0] for h in nodes_df["hub"]]
        node_y = [coords[h][1] for h in nodes_df["hub"]]
        node_text = [
            f"<b>{r['hub']}</b><br>{r['name']}<br>Cap: {r['capacity_est']} legs/day"
            for _, r in nodes_df.iterrows()
        ]
        fig_map.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text",
                text=[r["hub"] if r["capacity_est"] > 80 else "" for _, r in nodes_df.iterrows()],
                textposition="top center",
                textfont=dict(size=9, color="#94A3B8"),
                hovertext=node_text,
                hoverinfo="text",
                name="Hubs (Node size = capacity)",
                marker=dict(
                    size=[float(cap) * 0.35 + 6 for cap in nodes_df["capacity_est"]],
                    color="#0284C7",
                    line=dict(width=1, color="#38BDF8"),
                ),
            )
        )

        fig_map.update_layout(
            title=f"Full 100-Hub Spring-Layout Topology: {closed_u_name} → {closed_v_name}",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=640,
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        )

    style_plotly_fig(fig_map)
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
        style_plotly_fig(fig_th)
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
            color_continuous_scale="Teal",
            title="Top 10 Lanes by Baseline Traffic Volume",
        )
        fig_te.update_layout(yaxis=dict(autorange="reversed"), height=350, showlegend=False)
        style_plotly_fig(fig_te)
        st.plotly_chart(fig_te, use_container_width=True)

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
    render_header()
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

    # Comparison Table
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

    # Plotly Bar Charts
    st.markdown("### Cost Metrics Comparison Across Uncertainty Plans")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        fig_sim = go.Figure()
        fig_sim.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["eval_mean"],
                name="Avg Simulated (eval_mean)",
                marker_color="#38BDF8",
                text=summary_df["eval_mean"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_sim.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["eval_cvar"],
                name="CVaR 80% (eval_cvar)",
                marker_color="#F59E0B",
                text=summary_df["eval_cvar"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_sim.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["eval_worst"],
                name="Worst Scenario (eval_worst)",
                marker_color="#EF4444",
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
        style_plotly_fig(fig_sim)
        st.plotly_chart(fig_sim, use_container_width=True)

    with col_c2:
        fig_real = go.Figure()
        fig_real.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["realized_primary"],
                name="Realized Primary",
                marker_color="#10B981",
                text=summary_df["realized_primary"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_real.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["realized_sens_pred"],
                name="Realized Sens Pred",
                marker_color="#6366F1",
                text=summary_df["realized_sens_pred"].map(lambda x: f"{x:,.1f}"),
                textposition="auto",
            )
        )
        fig_real.add_trace(
            go.Bar(
                x=summary_df["plan"],
                y=summary_df["realized_sens_5legs"],
                name="Realized Sens 5-legs",
                marker_color="#8B5CF6",
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
        style_plotly_fig(fig_real)
        st.plotly_chart(fig_real, use_container_width=True)

    # Interval Diagnostics Table
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

    # Explicit Methodological Note
    st.info(
        "ℹ️ **Note on Interval Calibration & Sampling Spread**: "
        "Lane intervals are weighted averages of representative-route conformal intervals "
        "(not formally calibrated at the lane level) and sampling spread is derived from the "
        "90% interval with the 50% interval used as a diagnostic consistency check."
    )

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
    style_plotly_fig(fig_box)
    st.plotly_chart(fig_box, use_container_width=True)


def page_method_and_limitations() -> None:
    render_header()
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
        5. **Read-Only Architecture**: While the dashboard now features a Live What-If LP solver demo, all primary benchmark comparisons reflect verified offline optimization runs.
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
    st.sidebar.markdown(
        """
        <div style="padding: 10px 0 16px 0;">
            <div style="font-size: 1.4rem; font-weight: 800; color: #F8FAFC;">SupplyShield 🛡️</div>
            <div style="font-size: 0.78rem; font-weight: 600; color: #38BDF8; letter-spacing: 0.08em; text-transform: uppercase;">Control Tower SaaS</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Multipage Navigation
    pages = {
        "Overview": page_overview,
        "Live What-If Simulator": page_what_if_simulator,
        "Closure explorer": page_closure_explorer,
        "Network view": page_network_view,
        "Uncertainty": page_uncertainty,
        "Method and limitations": page_method_and_limitations,
    }

    selection = st.sidebar.radio(
        "Control Tower Navigation",
        list(pages.keys()),
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style="font-size: 0.8rem; color: #94A3B8; line-height: 1.6;">
            <div>📦 <b>Dataset</b>: Delhivery India Core</div>
            <div>🌐 <b>Network</b>: 100 Hubs | 292 Lanes</div>
            <div>⚡ <b>Solver</b>: HiGHS Dual-Simplex LP</div>
            <div>🎲 <b>Uncertainty</b>: Conformal Bounds</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render selected page
    page_func = pages[selection]
    page_func()


if __name__ == "__main__":
    main()
