"""Rebuild SupplyShield's training-only connected core."""

from pathlib import Path

import networkx as nx
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CONFIG = ROOT / "config"
DOCS = ROOT / "docs"

CORE_SIZE = 100
MIN_TRIPS = 3
TRAIN_DAYS = 14

ACCEPTED_LOCATION_STATUSES = {"city+state", "reviewed_city_proxy"}


def pair_index(frame):
    return pd.MultiIndex.from_frame(
        frame[["source_center", "destination_center"]]
    )


def edge_index(graph):
    return pd.MultiIndex.from_tuples(
        list(graph.edges()),
        names=["source_center", "destination_center"],
    )


def connected_order(graph, maximum=150):
    """Grow a weakly connected core using observed training traffic."""
    component = max(
        nx.weakly_connected_components(graph),
        key=lambda group: (len(group), tuple(sorted(group))),
    )
    graph = graph.subgraph(component).copy()
    undirected = graph.to_undirected()

    traffic = {
        hub: (
            sum(d["leg_count"] for _, _, d
                in graph.in_edges(hub, data=True))
            + sum(d["leg_count"] for _, _, d
                  in graph.out_edges(hub, data=True))
        )
        for hub in graph
    }

    seed = sorted(graph, key=lambda hub: (-traffic[hub], hub))[0]
    selected = {seed}
    order = [seed]

    while len(order) < min(maximum, len(graph)):
        candidates = set()
        for hub in selected:
            candidates.update(undirected.neighbors(hub))
        candidates -= selected

        def added_legs(hub):
            incoming = sum(
                graph[other][hub]["leg_count"]
                for other in graph.predecessors(hub)
                if other in selected
            )
            outgoing = sum(
                graph[hub][other]["leg_count"]
                for other in graph.successors(hub)
                if other in selected
            )
            return incoming + outgoing

        chosen = sorted(
            candidates,
            key=lambda hub: (-added_legs(hub), -traffic[hub], hub),
        )[0]
        selected.add(chosen)
        order.append(chosen)

    return graph, order


def update_assumptions(text):
    """Replace our section while preserving other documentation."""
    DOCS.mkdir(parents=True, exist_ok=True)
    path = DOCS / "assumptions.md"
    existing = (
        path.read_text(encoding="utf-8")
        if path.exists()
        else "# SupplyShield assumptions\n"
    )

    start = "<!-- CORE_SELECTION_START -->"
    end = "<!-- CORE_SELECTION_END -->"
    section = f"{start}\n{text}\n{end}"

    if start in existing and end in existing:
        before, remainder = existing.split(start, 1)
        _, after = remainder.split(end, 1)
        result = before + section + after
    else:
        result = existing.rstrip() + "\n\n" + section + "\n"

    path.write_text(result, encoding="utf-8")


def main():
    legs = pd.read_csv(PROCESSED / "legs.csv")
    hubs = pd.read_csv(CONFIG / "hub_location_snapshot.csv")

    if not hubs["hub"].is_unique:
        raise ValueError("Location snapshot contains duplicate hub IDs.")

    legs["trip_created"] = pd.to_datetime(
        legs["trip_creation_time"], errors="raise"
    )
    if legs["trip_created"].isna().any():
        raise ValueError("Missing trip creation timestamps.")

    dates_per_trip = legs.groupby("trip_uuid")["trip_created"].nunique()
    if not dates_per_trip.eq(1).all():
        raise ValueError("Conflicting creation timestamps within a trip.")

    train_start = legs["trip_created"].min().normalize()
    cutoff = train_start + pd.Timedelta(days=TRAIN_DAYS)

    train = legs.loc[legs["trip_created"] < cutoff].copy()
    later = legs.loc[legs["trip_created"] >= cutoff].copy()

    if set(train["trip_uuid"]) & set(later["trip_uuid"]):
        raise ValueError("A trip appears in both periods.")

    lanes = (
        train.groupby(
            ["source_center", "destination_center"], as_index=False
        )
        .agg(
            leg_count=("trip_uuid", "size"),
            trip_count=("trip_uuid", "nunique"),
        )
    )
    lanes = lanes.loc[lanes["trip_count"] >= MIN_TRIPS].copy()

    graph = nx.from_pandas_edgelist(
        lanes,
        source="source_center",
        target="destination_center",
        edge_attr=["trip_count", "leg_count"],
        create_using=nx.DiGraph(),
    )
    if graph.number_of_nodes() == 0:
        raise ValueError("No eligible training lanes.")

    graph, order = connected_order(graph)

    if len(order) < CORE_SIZE:
        raise ValueError("Largest component is too small for the core.")

    for column in ["latitude", "longitude"]:
        hubs[column] = pd.to_numeric(hubs[column], errors="coerce")

    hubs["located"] = (
        hubs["match"].isin(ACCEPTED_LOCATION_STATUSES)
        & hubs["latitude"].between(-90, 90)
        & hubs["longitude"].between(-180, 180)
    )
    located_ids = set(hubs.loc[hubs["located"], "hub"])

    training_pairs = pair_index(train)
    comparison = []

    for size in [50, 100, 150]:
        if size > len(order):
            continue

        ids = set(order[:size])
        candidate = graph.subgraph(ids).copy()
        candidate_legs = train.loc[
            training_pairs.isin(edge_index(candidate))
        ]
        both = (
            candidate_legs["source_center"].isin(located_ids)
            & candidate_legs["destination_center"].isin(located_ids)
        )

        comparison.append({
            "hubs": size,
            "directed_lanes": candidate.number_of_edges(),
            "training_legs": len(candidate_legs),
            "training_legs_kept_pct": round(
                100 * len(candidate_legs) / len(train), 2
            ),
            "weakly_connected": nx.is_weakly_connected(candidate),
            "largest_strong_group_pct": round(
                100 * max(
                    len(group)
                    for group in nx.strongly_connected_components(candidate)
                ) / size, 2
            ),
            "located_hubs": len(ids & located_ids),
            "both_ends_located_pct": round(100 * both.mean(), 2),
        })

    ids = set(order[:CORE_SIZE])
    core_graph = graph.subgraph(ids).copy()
    frozen_edges = edge_index(core_graph)

    missing_ids = ids - set(hubs["hub"])
    if missing_ids:
        raise ValueError(f"Missing hub metadata: {sorted(missing_ids)}")

    nodes = hubs.loc[hubs["hub"].isin(ids)].copy()
    edges = lanes.loc[pair_index(lanes).isin(frozen_edges)].copy()
    core_train = train.loc[training_pairs.isin(frozen_edges)].copy()
    core_later = later.loc[
        pair_index(later).isin(frozen_edges)
    ].copy()

    assert nx.is_weakly_connected(core_graph)
    assert len(nodes) == CORE_SIZE
    assert int(edges["leg_count"].sum()) == len(core_train)

    # Check against previous outputs before replacing the frozen selection.
    previous_nodes = PROCESSED / "core_nodes.csv"
    previous_edges = PROCESSED / "core_edges.csv"

    if previous_nodes.exists():
        old = pd.read_csv(previous_nodes)
        if set(old["hub"]) != ids:
            raise ValueError(
                "Rebuilt hub selection differs from saved core. "
                "No core files were replaced."
            )

    if previous_edges.exists():
        old = pd.read_csv(previous_edges)
        old_pairs = set(map(tuple, old[
            ["source_center", "destination_center"]
        ].to_numpy()))
        if old_pairs != set(core_graph.edges()):
            raise ValueError(
                "Rebuilt lanes differ from saved core. "
                "No core files were replaced."
            )

    coverage_rows = []
    for period, frame in [("training", core_train), ("later", core_later)]:
        both = (
            frame["source_center"].isin(located_ids)
            & frame["destination_center"].isin(located_ids)
        )
        coverage_rows.append({
            "period": period,
            "core_legs": len(frame),
            "both_ends_located": int(both.sum()),
            "both_ends_located_pct": round(100 * both.mean(), 2),
        })

    coverage = pd.DataFrame(coverage_rows)
    comparison = pd.DataFrame(comparison)

    # Preserve unrelated existing columns, such as later capacity estimates.
    if previous_nodes.exists():
        old = pd.read_csv(previous_nodes)
        extra = [c for c in old.columns if c not in nodes.columns]
        if extra:
            nodes = nodes.merge(
                old[["hub"] + extra],
                on="hub", how="left", validate="one_to_one"
            )

    outputs = {
        "core_nodes.csv": nodes,
        "core_edges.csv": edges,
        "core_train_legs.csv": core_train,
        "core_later_legs.csv": core_later,
        "core_training_comparison.csv": comparison,
        "core_location_coverage.csv": coverage,
        "core_location_review.csv": nodes.loc[~nodes["located"]],
    }
    for filename, frame in outputs.items():
        frame.to_csv(PROCESSED / filename, index=False)

    train_share = 100 * len(core_train) / len(train)
    later_share = (
        100 * len(core_later) / len(later) if len(later) else float("nan")
    )

    update_assumptions(f"""
## Core network selection and location limitations

- Selection uses trip_creation_time and keeps whole trips together.
- Training starts {train_start.date()} and ends before {cutoff.date()}.
- Person B must use the same split for compatible evaluation.
- Lane eligibility: at least {MIN_TRIPS} distinct training trips.
- Core size was chosen from training-only comparisons.
- Traffic-based connected growth is a heuristic, not an optimal solution.
- Frozen core: {len(nodes)} hubs and {len(edges)} directed lanes.
- Training legs retained: {len(core_train)} ({train_share:.2f}%).
- Later legs retained on frozen lanes: {len(core_later)} ({later_share:.2f}%).
- Later-period results do not influence the frozen selection.
- Locations available: {int(nodes['located'].sum())}; unresolved:
  {int((~nodes['located']).sum())}.
- Locations are city approximations, not verified warehouse coordinates.
- Reviewed city proxies and their evidence are preserved in
  config/hub_location_snapshot.csv.
- Postal validation remains incomplete.
- Unknown coordinates and weather remain missing, never zero rainfall.
- Endpoint weather does not measure weather along the entire route.
- Historical daily weather is retrospective, not a departure-time forecast.
- Capacity estimates, when added, are traffic proxies rather than measured
  physical warehouse capacities.

### Core journey-leg location coverage

{coverage.to_string(index=False)}
""")

    print("Verified and saved training-only core.")
    print(f"Hubs: {len(nodes)}; directed lanes: {len(edges)}")
    print(f"Training legs: {len(core_train)}; later legs: {len(core_later)}")
    print(f"Located hubs: {int(nodes['located'].sum())}")
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()