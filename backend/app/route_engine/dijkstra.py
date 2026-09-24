from __future__ import annotations

import heapq
from typing import Dict, List, Tuple

from app.route_engine.graph import Graph


def dijkstra_shortest_path(graph: Graph, source: str, target: str) -> Dict[str, object]:
    if source not in graph.adjacency or target not in graph.adjacency:
        raise ValueError(f"Source or target node not found: {source} -> {target}")

    distances: Dict[str, float] = {source: 0.0}
    previous: Dict[str, str | None] = {source: None}
    queue: List[Tuple[float, str]] = [(0.0, source)]

    while queue:
        current_distance, node = heapq.heappop(queue)

        if current_distance > distances.get(node, float("inf")):
            continue

        if node == target:
            break

        for connection in graph.adjacency.get(node, []):
            new_distance = current_distance + connection.duration
            if new_distance < distances.get(connection.destination, float("inf")):
                distances[connection.destination] = new_distance
                previous[connection.destination] = node
                heapq.heappush(queue, (new_distance, connection.destination))

    if target not in previous:
        raise ValueError(f"No path found from {source} to {target}")

    path: List[str] = []
    cursor = target
    while cursor is not None:
        path.append(cursor)
        cursor = previous.get(cursor)
    path.reverse()

    total_time = 0
    total_cost = 0.0
    total_walking = 0.0
    total_wait = 0
    total_transfers = 0
    reliability_product = 1.0
    legs: list[Dict[str, object]] = []

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
        total_transfers += conn.transfers
        reliability_product *= conn.reliability
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
