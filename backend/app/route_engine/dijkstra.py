from __future__ import annotations

import heapq
from typing import Dict, List, Tuple

from app.route_engine.graph import Graph


def dijkstra_shortest_path(
    graph: Graph,
    source: str,
    target: str,
    blocked_route_ids: set[str] | None = None,
    max_services: int = 2,
) -> Dict[str, object]:
    if source not in graph.adjacency or target not in graph.adjacency:
        raise ValueError(f"Source or target node not found: {source} -> {target}")

    start_state = (source, ())
    distances: Dict[Tuple[str, Tuple[str, ...]], float] = {start_state: 0.0}
    previous: Dict[Tuple[str, Tuple[str, ...]], Tuple[str, Tuple[str, ...]] | None] = {start_state: None}
    queue: List[Tuple[float, str, Tuple[str, ...]]] = [(0.0, source, ())]
    target_state: Tuple[str, Tuple[str, ...]] | None = None

    while queue:
        current_distance, node, services = heapq.heappop(queue)
        state = (node, services)

        if current_distance > distances.get(state, float("inf")):
            continue

        if node == target:
            target_state = state
            break

        for connection in graph.adjacency.get(node, []):
            if connection.route_id in (blocked_route_ids or set()):
                continue
            next_services = set(services)
            if connection.route_id and connection.mode != "caminata":
                next_services.add(str(connection.route_id))
            if len(next_services) > max_services:
                continue
            next_service_tuple = tuple(sorted(next_services))
            next_state = (connection.destination, next_service_tuple)
            new_distance = current_distance + connection.duration
            if new_distance < distances.get(next_state, float("inf")):
                distances[next_state] = new_distance
                previous[next_state] = state
                heapq.heappush(queue, (new_distance, connection.destination, next_service_tuple))

    if target_state is None:
        raise ValueError(f"No path found from {source} to {target}")

    path: List[str] = []
    cursor: Tuple[str, Tuple[str, ...]] | None = target_state
    while cursor is not None:
        path.append(cursor[0])
        cursor = previous.get(cursor)
    path.reverse()

    total_time = 0
    total_cost = 0.0
    total_walking = 0.0
    total_wait = 0
    total_transfers = 0
    reliability_product = 1.0
    legs: list[Dict[str, object]] = []
    previous_service: str | None = None

    for i in range(len(path) - 1):
        current = path[i]
        nxt = path[i + 1]
        conn = next(
            item for item in graph.adjacency.get(current, []) if item.destination == nxt
        )
        total_time += conn.duration
        total_cost += conn.cost
        total_walking += conn.walking
        total_wait += conn.wait
        service_id = conn.route_id if conn.mode != "caminata" else None
        if service_id and previous_service and service_id != previous_service:
            total_transfers += 1
        if service_id:
            previous_service = service_id
        reliability_product *= conn.reliability
        if legs and legs[-1]["modo"] == conn.mode and legs[-1]["route_id"] == conn.route_id:
            leg = legs[-1]
            leg["destino"] = nxt
            leg["tiempo"] = int(leg["tiempo"]) + conn.duration
            leg["distancia"] = float(leg["distancia"]) + conn.distance
        else:
            legs.append(
                {
                    "origen": current,
                    "destino": nxt,
                    "modo": conn.mode,
                    "route_id": conn.route_id,
                    "tiempo": conn.duration,
                    "distancia": conn.distance,
                }
            )

    return {
        "path": path,
        "total_time": total_time,
        "total_cost": total_cost,
        "walking": total_walking,
        "wait_time": total_wait,
        "transfers": total_transfers,
        "reliability": reliability_product,
        "legs": legs,
    }
