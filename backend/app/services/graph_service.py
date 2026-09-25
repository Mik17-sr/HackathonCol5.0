from __future__ import annotations

import math
from typing import Any
import asyncio
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.ingestion.normalizar_datos import normalize_route_records, route_vertex_records, simplify_route_records
from app.integrations.datos_abiertos.gtfs_client import GTFSClient
from app.route_engine.graph import Graph
from app.route_engine.graph_builder import GraphBuilder
from app.services.open_data_service import fetch_rutas_zonales
from app.services.mobility_persistence import persist_open_data
from app.models.parada import Parada
from app.models.ruta import Ruta

_PERSISTED_ROUTE_SIGNATURE: tuple[str, ...] | None = None
_GRAPH_CACHE_SIGNATURE: tuple[str, ...] | None = None
_GRAPH_CACHE: tuple[Graph, dict[str, dict[str, Any]]] | None = None


class GraphService:
    """Servicio encargado de construir el grafo usando archivos GTFS o datos de prueba."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def build_graph(self) -> Graph:
        if self.settings.source_config.provider == "gtfs":
            path = self.settings.source_config.gtfs_path
            base_path = Path(path) if path else Path(self.settings.source_config.data_dir)
            client = GTFSClient(base_path=str(base_path))
            raw_records = client.fetch()
            normalized = client.normalize(raw_records)
            if not normalized:
                return self._build_fallback_graph()
            return GraphBuilder.from_records(normalized)

        return self._build_fallback_graph()

    async def build_open_data_graph(self, limit: int | None = None) -> tuple[Graph, dict[str, dict[str, Any]]]:
        if not self.settings.source_config.enable_external_sources:
            return self._build_local_database_graph()

        try:
            rutas = await asyncio.wait_for(fetch_rutas_zonales(limit=limit), timeout=30)
        except (asyncio.TimeoutError, httpx.HTTPError):
            return self._build_local_database_graph()
        normalized_routes = normalize_route_records(
            rutas,
            source_crs=self.settings.source_config.source_crs,
            target_crs=self.settings.source_config.target_crs,
        )
        graph_routes = simplify_route_records(normalized_routes, max_vertices=40)
        points = route_vertex_records(graph_routes, max_points=200)
        global _PERSISTED_ROUTE_SIGNATURE, _GRAPH_CACHE_SIGNATURE, _GRAPH_CACHE
        route_signature = tuple(route["id"] for route in normalized_routes)
        if route_signature == _GRAPH_CACHE_SIGNATURE and _GRAPH_CACHE is not None:
            return _GRAPH_CACHE
        if (points or normalized_routes) and route_signature != _PERSISTED_ROUTE_SIGNATURE:
            persist_open_data(points, normalized_routes)
            _PERSISTED_ROUTE_SIGNATURE = route_signature
        if len(points) < 2 and not normalized_routes:
            return self._build_fallback_graph(), {}
        node_points = {point["id"]: point for point in points}
        for route in graph_routes:
            for path_index, path in enumerate(route["paths"]):
                for vertex_index, (lat, lng) in enumerate(path):
                    node_points[f"route:{route['id']}:{path_index}:{vertex_index}"] = {
                        "id": f"route:{route['id']}:{path_index}:{vertex_index}",
                        "name": route["name"],
                        "source_type": "ruta_zonal",
                        "lat": lat,
                        "lng": lng,
                        "mode": route.get("mode", "sitp"),
                        "route_id": route["id"],
                    }
        _GRAPH_CACHE_SIGNATURE = route_signature
        _GRAPH_CACHE = self.build_graph_from_points(points, graph_routes), node_points
        return _GRAPH_CACHE

    def _build_local_database_graph(self) -> tuple[Graph, dict[str, dict[str, Any]]]:
        with SessionLocal() as db:
            records = db.query(Parada).filter(Parada.activo.is_(True)).all()
            route_records = db.query(Ruta).filter(Ruta.activo.is_(True)).all()
        points = [
            {
                "id": f"db:{record.codigo or record.id}",
                "name": record.nombre,
                "source_type": "parada",
                "lat": record.lat,
                "lng": record.lng,
                "mode": record.tipo or "sitp",
                "status": "normal",
                "raw": {},
            }
            for record in records
        ]
        if len(points) < 2:
            return self._build_fallback_graph(), {}
        ordered_points = sorted(points, key=lambda point: (point["lat"], point["lng"]))
        route_path = [(point["lat"], point["lng"]) for point in ordered_points]
        routes = [
            {
                "id": route.codigo,
                "name": f"{route.codigo} · {route.nombre}",
                "mode": "sitp" if route.tipo in {"zonal", "troncal"} else route.tipo,
                "paths": [route_path],
            }
            for route in route_records
        ]
        graph = self.build_graph_from_points(points, routes)
        node_points = {point["id"]: point for point in points}
        for route in routes:
            for path_index, path in enumerate(route["paths"]):
                for vertex_index, (lat, lng) in enumerate(path):
                    node_id = f"route:{route['id']}:{path_index}:{vertex_index}"
                    node_points[node_id] = {
                        "id": node_id,
                        "name": route["name"],
                        "source_type": "ruta_zonal",
                        "lat": lat,
                        "lng": lng,
                        "mode": route["mode"],
                        "route_id": route["id"],
                    }
        return graph, node_points

    @staticmethod
    def build_graph_from_points(
        points: list[dict[str, Any]],
        routes: list[dict[str, Any]] | None = None,
        neighbors: int = 3,
    ) -> Graph:
        graph = Graph()
        for point in points:
            graph.add_node(str(point["id"]))

        for point in points:
            candidates = sorted(
                (
                    (haversine_km(point["lat"], point["lng"], other["lat"], other["lng"]), other)
                    for other in points
                    if other["id"] != point["id"]
                ),
                key=lambda item: item[0],
            )[:neighbors]
            for distance, other in candidates:
                duration = max(1, round(distance / 5 * 60))
                graph.add_connection(
                    str(point["id"]),
                    str(other["id"]),
                    duration=duration,
                    cost=0,
                    distance=distance,
                    walking=distance,
                    wait=0,
                    transfers=0,
                    reliability=0.95,
                    accessibility=0.8,
                    status="normal",
                    mode="caminata",
                )

        GraphService._add_route_edges(graph, points, routes or [])

        # Ensure isolated geographic clusters remain reachable by Dijkstra.
        ordered_points = sorted(points, key=lambda point: (point["lat"], point["lng"]))
        for point, other in zip(ordered_points, ordered_points[1:]):
            distance = haversine_km(point["lat"], point["lng"], other["lat"], other["lng"])
            duration = max(1, round(distance / 5 * 60))
            for source, destination in ((point, other), (other, point)):
                graph.add_connection(
                    str(source["id"]),
                    str(destination["id"]),
                    duration=duration,
                    cost=0,
                    distance=distance,
                    walking=distance,
                    wait=0,
                    transfers=0,
                    reliability=0.95,
                    accessibility=0.8,
                    status="normal",
                    mode="caminata",
                )
        return graph

    @staticmethod
    def _add_route_edges(
        graph: Graph,
        points: list[dict[str, Any]],
        routes: list[dict[str, Any]],
    ) -> None:
        point_nodes = [point for point in points]
        for route in routes:
            for path_index, path in enumerate(route["paths"]):
                route_nodes: list[str] = []
                for vertex_index, (lat, lng) in enumerate(path):
                    node_id = f"route:{route['id']}:{path_index}:{vertex_index}"
                    graph.add_node(node_id)
                    route_nodes.append(node_id)
                    if vertex_index:
                        previous_lat, previous_lng = path[vertex_index - 1]
                        distance = haversine_km(previous_lat, previous_lng, lat, lng)
                        duration = max(1, round(distance / 25 * 60))
                        for source, destination in ((route_nodes[-2], node_id), (node_id, route_nodes[-2])):
                            graph.add_connection(
                                source,
                                destination,
                                duration=duration,
                                cost=2950,
                                distance=distance,
                                walking=0,
                                wait=max(1, round((route.get("frequency_min") or 4) / 2)),
                                transfers=0,
                                reliability=0.9,
                                accessibility=0.8,
                                status="normal",
                                mode=route.get("mode", "sitp"),
                                route_id=str(route["id"]),
                            )

                route_points = [
                    point
                    for point in point_nodes
                    if point.get("route_id") == route["id"] and point.get("path_index") == path_index
                ]
                for point in route_points or point_nodes:
                    point_id = str(point["id"])
                    point_lat = point["lat"]
                    point_lng = point["lng"]
                    nearest_index = point.get("vertex_index")
                    if nearest_index is None or nearest_index >= len(path):
                        nearest_index = min(
                            range(len(path)),
                            key=lambda index: haversine_km(point_lat, point_lng, path[index][0], path[index][1]),
                        )
                    distance = haversine_km(point_lat, point_lng, path[nearest_index][0], path[nearest_index][1])
                    if distance > 0.5:
                        continue
                    route_node = route_nodes[nearest_index]
                    duration = max(1, round(distance / 5 * 60))
                    for source, destination in ((point_id, route_node), (route_node, point_id)):
                        graph.add_connection(
                            source,
                            destination,
                            duration=duration,
                            cost=0,
                            distance=distance,
                            walking=distance,
                            wait=0,
                            transfers=0,
                            reliability=0.9,
                            accessibility=0.8,
                            status="normal",
                            mode="caminata",
                        )

    @staticmethod
    def nearest_point(points: dict[str, dict[str, Any]], lat: float, lng: float) -> str:
        if not points:
            raise ValueError("No hay puntos de transporte disponibles")
        return min(
            points,
            key=lambda point_id: haversine_km(lat, lng, points[point_id]["lat"], points[point_id]["lng"]),
        )

    def _build_fallback_graph(self) -> Graph:
        return GraphBuilder.from_records(self.settings.default_graph_records)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    lat_delta = math.radians(lat2 - lat1)
    lng_delta = math.radians(lng2 - lng1)
    value = (
        math.sin(lat_delta / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(lng_delta / 2) ** 2
    )
    return radius_km * 2 * math.asin(math.sqrt(value))
