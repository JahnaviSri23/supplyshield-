from collections import defaultdict
import math

import networkx as nx


EPS = 1e-9


def _routes(graph, demands, plan):
    """Return fixed routes and the daily demand assigned to each route."""
    routes = []

    if plan is None:
        for (source, destination), amount in demands.items():
            try:
                path = nx.shortest_path(
                    graph, source, destination, weight="cost"
                )
            except nx.NetworkXNoPath:
                path = None

            routes.append((path, amount))

        return routes

    # Aggregate edge flows cannot identify multiple OD commodities.
    if len(demands) != 1:
        raise ValueError(
            "An edge-flow plan currently supports one origin/destination. "
            "Multiple commodities require a commodity-specific plan."
        )

    (source, destination), demand = next(iter(demands.items()))
    residual = nx.DiGraph()
    residual.add_nodes_from(graph.nodes)

    for edge, amount in plan.items():
        amount = float(amount)

        if not math.isfinite(amount) or amount < -EPS:
            raise ValueError("Plan flows must be finite and nonnegative.")

        if edge not in graph.edges:
            raise ValueError(f"Plan contains an unknown edge: {edge}")

        if amount > EPS:
            u, v = edge
            residual.add_edge(
                u, v, flow=amount, cost=graph.edges[edge]["cost"]
            )

    # Check that the supplied static plan conserves flow.
    balance = {node: 0.0 for node in graph}

    for u, v, attributes in residual.edges(data=True):
        balance[u] += attributes["flow"]
        balance[v] -= attributes["flow"]

    for node in graph:
        if node not in (source, destination):
            if abs(balance[node]) > 1e-6:
                raise ValueError(f"Plan does not conserve flow at {node}.")

    planned = balance[source]

    if (
        planned < -EPS
        or planned > demand + 1e-6
        or abs(balance[destination] + planned) > 1e-6
    ):
        raise ValueError("Plan source/destination totals are invalid.")

    # Decompose the edge-flow plan into complete routes.
    assigned = 0.0

    while nx.has_path(residual, source, destination):
        path = nx.shortest_path(
            residual, source, destination, weight="cost"
        )
        edges = list(zip(path, path[1:]))
        amount = min(residual.edges[e]["flow"] for e in edges)

        routes.append((path, amount))
        assigned += amount

        for edge in edges:
            residual.edges[edge]["flow"] -= amount
            if residual.edges[edge]["flow"] <= EPS:
                residual.remove_edge(*edge)

    if residual.number_of_edges():
        raise ValueError("Plan contains cycles or disconnected flow.")

    if abs(assigned - planned) > 1e-6:
        raise ValueError("Unable to decompose the supplied plan.")

    # Unassigned demand remains unmet; it must not disappear.
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
            (u, v): float(attributes.get("cap", math.inf))
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

                if multipliers[node] > 0 and multipliers[destination] > 0:
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
    if failed and failure_days:
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