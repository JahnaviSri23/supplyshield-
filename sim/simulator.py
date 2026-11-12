from collections import defaultdict
import math

import networkx as nx


EPS = 1e-9


def _routes(graph, demands, plan):
    """Convert default routes or OD-specific edge flows into daily routes.

    plan=None uses shortest paths. A dict preserves the legacy single-OD
    interface. A list contains {"od": [u,v], "edge": [a,b], "flow": number}.
    Unassigned demand is explicitly retained as an unmet route.
    """
    if plan is None:
        routes = []
        for (source, destination), amount in demands.items():
            try:
                path = nx.shortest_path(
                    graph, source, destination, weight="cost"
                )
            except nx.NetworkXNoPath:
                path = None
            routes.append((path, amount))
        return routes

    if isinstance(plan, dict):
        if len(demands) != 1:
            raise ValueError(
                "Dictionary plans support one OD only; use OD-specific records."
            )
        od = next(iter(demands))
        records = [
            {"od": list(od), "edge": list(edge), "flow": flow}
            for edge, flow in plan.items()
        ]
    elif isinstance(plan, list):
        records = plan
    else:
        raise ValueError("Plan must be None, an edge-flow dict, or an OD record list.")

    flows_by_od = defaultdict(lambda: defaultdict(float))
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each flow record must be a dictionary.")
        try:
            od = tuple(record["od"])
            edge = tuple(record["edge"])
            amount = float(record["flow"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid OD flow record.") from exc
        if len(od) != 2 or len(edge) != 2:
            raise ValueError("OD and edge must each have exactly two nodes.")
        if od not in demands:
            raise ValueError(f"Unknown OD pair in plan: {od}")
        if edge not in graph.edges:
            raise ValueError(f"Unknown edge in plan: {edge}")
        if not math.isfinite(amount) or amount < -EPS:
            raise ValueError("Plan flows must be finite and nonnegative.")
        if amount > EPS:
            flows_by_od[od][edge] += amount

    routes = []
    for (source, destination), demand in demands.items():
        residual = nx.DiGraph()
        residual.add_nodes_from(graph.nodes)
        for (u, v), amount in flows_by_od[(source, destination)].items():
            if amount > EPS:
                residual.add_edge(
                    u, v, flow=amount, cost=graph.edges[u, v]["cost"]
                )

        balance = {node: 0.0 for node in graph}
        for u, v, attributes in residual.edges(data=True):
            amount = attributes["flow"]
            balance[u] += amount
            balance[v] -= amount
        for node in graph:
            if node not in (source, destination) and abs(balance[node]) > 1e-6:
                raise ValueError(
                    f"Plan does not conserve {source}->{destination} flow at {node}."
                )

        planned = balance[source]
        if (
            planned < -EPS
            or planned > demand + 1e-6
            or abs(balance[destination] + planned) > 1e-6
        ):
            raise ValueError(f"Invalid planned demand for {source}->{destination}.")

        assigned = 0.0
        while nx.has_path(residual, source, destination):
            path = nx.shortest_path(
                residual, source, destination, weight="cost"
            )
            edges = list(zip(path, path[1:]))
            amount = min(residual.edges[edge]["flow"] for edge in edges)
            routes.append((path, amount))
            assigned += amount
            for edge in edges:
                residual.edges[edge]["flow"] -= amount
                if residual.edges[edge]["flow"] <= EPS:
                    residual.remove_edge(*edge)

        if residual.number_of_edges():
            raise ValueError(
                f"Plan contains cycles or disconnected {source}->{destination} flow."
            )
        if abs(assigned - planned) > 1e-6:
            raise ValueError(f"Cannot decompose {source}->{destination} plan.")
        if demand - assigned > EPS:
            routes.append((None, demand - assigned))
    return routes


def simulate(graph, scenario, plan=None):
    """
    Deterministic daily fluid-flow simulation.

    Required graph metadata:
        demands = {(origin, destination): daily_amount}

    Required attributes:
        nodes: cap
        edges: cost
    Optional attributes:
        nodes: buffer
        edges: cap

    One edge takes one day in this first implementation.
    scenario["closed_lanes"] optionally specifies directed [u, v] pairs
    unavailable during [failure_start, failure_start + failure_days).
    Assigned traffic waits for reopening; routing is fixed per run.
    """
    if not graph.is_directed() or graph.is_multigraph():
        raise ValueError("Use a networkx DiGraph.")

    demands = {
        pair: float(amount)
        for pair, amount in graph.graph["demands"].items()
    }

    for (source, destination), amount in demands.items():
        if source not in graph or destination not in graph:
            raise ValueError("Demand endpoints must exist in the graph.")
        if source == destination:
            raise ValueError("Demand endpoints must differ.")
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Demand must be finite and nonnegative.")

    demand_days = int(scenario.get("demand_days", 7))
    horizon = int(scenario.get("horizon", 40))
    failure_start = int(scenario.get("failure_start", 0))
    failure_days = int(scenario.get("failure_days", 3))
    scale = float(scenario.get("capacity_scale", 1.0))
    failed = dict(scenario.get("failed", {}))
    # Directed lanes closed during the same failure window as failed hubs.
    raw_closed_lanes = scenario.get("closed_lanes", [])
    if not isinstance(raw_closed_lanes, (list, tuple, set)):
        raise ValueError("closed_lanes must be a collection of directed edge pairs.")
    closed_lanes = set()
    for lane in raw_closed_lanes:
        if not isinstance(lane, (list, tuple)) or len(lane) != 2:
            raise ValueError("Each closed lane must be a [source, destination] pair.")
        edge = tuple(lane)
        if edge not in graph.edges:
            raise ValueError(f"Unknown closed lane: {edge}")
        closed_lanes.add(edge)

    if demand_days < 1 or horizon <= demand_days:
        raise ValueError("Horizon must exceed the positive demand period.")
    if failure_start < 0 or failure_days < 0:
        raise ValueError("Failure timing cannot be negative.")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("Capacity scale must be positive and finite.")

    for node, remaining in failed.items():
        if node not in graph or not 0 <= remaining <= 1:
            raise ValueError("Invalid failed hub or remaining capacity.")

    base_capacity = {
        node: float(graph.nodes[node]["cap"]) for node in graph
    }
    buffers = {
        node: float(
            graph.nodes[node].get(
                "buffer", 2 * max(base_capacity[node], 1)
            )
        )
        for node in graph
    }

    for node in graph:
        if (
            not math.isfinite(base_capacity[node])
            or base_capacity[node] < 0
            or not math.isfinite(buffers[node])
            or buffers[node] < 0
        ):
            raise ValueError("Capacities/buffers must be finite and nonnegative.")

    for _, _, attributes in graph.edges(data=True):
        cost = float(attributes["cost"])
        cap = float(attributes.get("cap", math.inf))
        if not math.isfinite(cost) or cost < 0:
            raise ValueError("Edge costs must be finite and nonnegative.")
        if math.isnan(cap) or cap < 0:
            raise ValueError("Edge capacities must be nonnegative.")

    waiting_rate = float(graph.graph.get("waiting_cost", 1.0))
    penalty = float(graph.graph.get("unmet_penalty", 20.0))

    if any(
        not math.isfinite(value) or value < 0
        for value in (waiting_rate, penalty)
    ):
        raise ValueError("Cost rates must be finite and nonnegative.")

    routes = _routes(graph, demands, plan)

    # Jobs are [path, current_path_position, amount].
    queues = {node: [] for node in graph}
    pending = []       # Outside-origin backlog: no warehouse space yet.
    transit = []       # Arrives at the beginning of the following day.

    generated = delivered = shipping = waiting = 0.0
    unassigned = 0.0
    history = []
    drain_day = None

    for day in range(horizon):
        active = failure_start <= day < failure_start + failure_days

        multipliers = {
            node: float(failed.get(node, 1.0)) if active else 1.0
            for node in graph
        }
        capacity_left = {
            node: base_capacity[node] * scale * multipliers[node]
            for node in graph
        }
        edge_left = {
            (u, v): (
                0.0 if active and (u, v) in closed_lanes
                else float(attributes.get("cap", math.inf))
            )
            for u, v, attributes in graph.edges(data=True)
        }

        # Previously dispatched traffic already reserved its storage.
        for path, position, amount in transit:
            if position == len(path) - 1:
                delivered += amount
            else:
                queues[path[position]].append([path, position, amount])
        transit = []

        if day < demand_days:
            for path, amount in routes:
                generated += amount
                if path is None:
                    unassigned += amount
                elif amount > EPS:
                    pending.append([path, 0, amount])

        occupancy = {
            node: sum(job[2] for job in queues[node])
            for node in graph
        }

        # Admit origin demand only when storage is available.
        remaining_pending = []

        for path, position, amount in pending:
            origin = path[0]
            room = max(0.0, buffers[origin] - occupancy[origin])
            admitted = min(amount, room) if multipliers[origin] > 0 else 0.0

            if admitted > EPS:
                queues[origin].append([path, position, admitted])
                occupancy[origin] += admitted

            if amount - admitted > EPS:
                remaining_pending.append([path, position, amount - admitted])

        pending = remaining_pending

        # Freeze receiving space for this step. This prevents node-order
        # effects and reserves space for next-day transit arrivals.
        receiving_room = {
            node: max(0.0, buffers[node] - occupancy[node])
            for node in graph
        }

        next_queues = {node: [] for node in graph}

        for node in sorted(graph.nodes, key=str):
            for path, position, amount in queues[node]:
                destination = path[position + 1]
                edge = (node, destination)
                final_destination = position + 1 == len(path) - 1

                room = (
                    math.inf
                    if final_destination
                    else receiving_room[destination]
                )

                sent = 0.0

                if multipliers[node] > 0:
                    sent = min(
                        amount,
                        capacity_left[node],
                        edge_left[edge],
                        room,
                    )

                if sent > EPS:
                    capacity_left[node] -= sent
                    edge_left[edge] -= sent
                    shipping += sent * graph.edges[edge]["cost"]
                    transit.append([path, position + 1, sent])

                    if not final_destination:
                        receiving_room[destination] -= sent

                if amount - sent > EPS:
                    next_queues[node].append(
                        [path, position, amount - sent]
                    )

        queues = next_queues

        queued = sum(
            job[2] for jobs in queues.values() for job in jobs
        )
        outside = sum(job[2] for job in pending) + unassigned
        moving = sum(job[2] for job in transit)

        waiting += waiting_rate * (queued + outside)

        # Verify that no traffic was created or lost.
        balance_error = abs(
            generated - delivered - queued - outside - moving
        )
        if balance_error > 1e-6 * max(1.0, generated):
            raise AssertionError("Flow conservation failed.")

        # Check warehouse occupancy including reserved incoming traffic.
        reserved = defaultdict(float)
        for path, position, amount in transit:
            if position < len(path) - 1:
                reserved[path[position]] += amount

        for node in graph:
            stored = sum(job[2] for job in queues[node])
            if stored + reserved[node] > buffers[node] + 1e-6:
                raise AssertionError("Warehouse buffer exceeded.")

        history.append({
            "day": day,
            "generated": generated,
            "delivered": delivered,
            "queued": queued,
            "outside_backlog": outside,
            "in_transit": moving,
        })

        if day >= demand_days - 1 and generated - delivered <= EPS:
            drain_day = day
            break

    unmet = max(0.0, generated - delivered)

    # Drain time after demand stops and the specified failure has ended.
    anchor = demand_days - 1
    if (failed or closed_lanes) and failure_days:
        anchor = max(anchor, failure_start + failure_days - 1)

    recovery_days = (
        None if drain_day is None else max(0, drain_day - anchor)
    )

    return {
        "shipping_cost": shipping,
        "waiting_cost": waiting,
        "unmet": unmet,
        "delivered": delivered,
        "generated": generated,
        "recovery_days": recovery_days,
        "recovery_censored": drain_day is None,
        "total_cost": shipping + waiting + penalty * unmet,
        "history": history,
    }