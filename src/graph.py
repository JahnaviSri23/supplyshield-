from pathlib import Path

import networkx as nx
import pandas as pd


def build_graph(lanes, min_trips=3):
    """Build a directed network from sufficiently observed lanes."""
    selected = lanes.loc[
        lanes["trip_count"] >= min_trips
    ].copy()

    return nx.from_pandas_edgelist(
        selected,
        source="source_center",
        target="destination_center",
        create_using=nx.DiGraph()
    )


def threshold_summary(legs, lanes):
    """Compare network size and coverage at thresholds 1–30."""
    results = []
    total_legs = len(legs)

    if total_legs == 0:
        raise ValueError("The legs table is empty.")

    if int(lanes["leg_count"].sum()) != total_legs:
        raise ValueError(
            "Lane leg counts do not match the number of journey legs."
        )

    for threshold in range(1, 31):
        selected = lanes.loc[
            lanes["trip_count"] >= threshold
        ]

        graph = build_graph(lanes, threshold)

        hubs = graph.number_of_nodes()
        lane_count = graph.number_of_edges()
        legs_kept = int(selected["leg_count"].sum())

        if hubs:
            largest_weak = max(
                nx.weakly_connected_components(graph),
                key=len
            )
            largest_strong = max(
                nx.strongly_connected_components(graph),
                key=len
            )

            inside_group = (
                selected["source_center"].isin(largest_weak)
                & selected["destination_center"].isin(largest_weak)
            )

            group_legs = int(
                selected.loc[inside_group, "leg_count"].sum()
            )
        else:
            largest_weak = set()
            largest_strong = set()
            group_legs = 0

        results.append({
            "min_trips": threshold,
            "hubs": hubs,
            "lanes": lane_count,
            "legs_kept": legs_kept,
            "legs_kept_pct": 100 * legs_kept / total_legs,
            "largest_weak_hubs": len(largest_weak),
            "largest_weak_hubs_pct": (
                100 * len(largest_weak) / hubs if hubs else 0
            ),
            "largest_strong_hubs_pct": (
                100 * len(largest_strong) / hubs if hubs else 0
            ),
            "largest_weak_legs_pct_of_all": (
                100 * group_legs / total_legs
            ),
        })

    return pd.DataFrame(results)


def main():
    root = Path(__file__).resolve().parents[1]
    processed = root / "data" / "processed"

    legs = pd.read_csv(processed / "legs.csv")
    lanes = pd.read_csv(processed / "lanes.csv")

    summary = threshold_summary(legs, lanes)

    output = processed / "threshold_sensitivity.csv"
    summary.to_csv(output, index=False)

    print(summary.round(2).to_string(index=False))
    print("\nSaved:", output)
        # Calculate critical hubs at the selected threshold
    graph = build_graph(lanes, min_trips=3)
    scores = nx.betweenness_centrality(graph)

    stats = pd.DataFrame({
        "hub": list(graph.nodes()),
        "incoming_lanes": [
            graph.in_degree(hub) for hub in graph.nodes()
        ],
        "outgoing_lanes": [
            graph.out_degree(hub) for hub in graph.nodes()
        ],
        "betweenness": [
            scores[hub] for hub in graph.nodes()
        ],
    })

    stats["total_lanes"] = (
        stats["incoming_lanes"] + stats["outgoing_lanes"]
    )
    stats["min_trips"] = 3

    # Attach location names
    sources = legs[["source_center", "source_name"]].rename(
        columns={"source_center": "hub", "source_name": "name"}
    )
    destinations = legs[
        ["destination_center", "destination_name"]
    ].rename(
        columns={
            "destination_center": "hub",
            "destination_name": "name"
        }
    )

    names = (
        pd.concat([sources, destinations], ignore_index=True)
        .dropna(subset=["name"])
        .drop_duplicates(subset="hub")
    )

    stats = (
        stats.merge(names, on="hub", how="left")
        .sort_values(
            ["betweenness", "hub"],
            ascending=[False, True]
        )
        .reset_index(drop=True)
    )

    stats_file = processed / "hub_stats_threshold3.csv"
    stats.to_csv(stats_file, index=False)

    print("\nTOP 10 HUBS — THRESHOLD 3")
    print(
        stats[
            ["hub", "name", "total_lanes", "betweenness"]
        ].head(10).to_string(index=False)
    )
    print("\nSaved:", stats_file)


if __name__ == "__main__":
    main()