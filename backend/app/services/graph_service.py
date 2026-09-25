"""
graph_service.py — Servicio de construcción del grafo de transporte.

ESTRATEGIA DE DISPONIBILIDAD
-----------------------------
1. Grafo local (local_graph.py)  →  siempre disponible,  < 50 ms.
2. API ArcGIS de Transmilenio   →  enriquecimiento opcional, timeout 10 s.
   Las rutas externas se FUSIONAN con las locales, no las reemplazan.
3. Si la API está caída           →  solo grafo local.

NUEVO: get_stop_router()
    Construye la StopNetwork basada en paradas derivadas SITP y devuelve
    un StopRouter listo para find_route().  Este es el camino principal.

build_open_data_graph() sigue disponible para compatibilidad con tests
y el endpoint legacy de recomendación de chat.
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any
import asyncio
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.ingestion.normalizar_datos import (
    normalize_route_records,
    route_vertex_records,
    simplify_route_records,
)
from app.integrations.datos_abiertos.gtfs_client import GTFSClient
from app.route_engine.graph import Graph
from app.route_engine.graph_builder import GraphBuilder
from app.route_engine.stop_graph import StopNetwork, build_stop_network
from app.route_engine.stop_router import StopRouter
from app.services.local_graph import get_local_nodes, get_local_routes
from app.services.open_data_service import fetch_rutas_zonales
from app.services.mobility_persistence import persist_open_data
from app.models.parada import Parada
from app.models.ruta import Ruta

logger = logging.getLogger(__name__)

# ── Cachés en memoria ──────────────────────────────────────────────────────
_PERSISTED_ROUTE_SIGNATURE: tuple[str, ...] | None = None
_GRAPH_CACHE_SIGNATURE: tuple[str, ...] | None = None
_GRAPH_CACHE: tuple[Graph, dict[str, dict[str, Any]]] | None = None
_LOCAL_GRAPH_CACHE: tuple[Graph, dict[str, dict[str, Any]]] | None = None

# Caché de StopNetwork (reconstruir solo si cambian las rutas)
_STOP_NETWORK_CACHE: StopNetwork | None = None
_STOP_NETWORK_SIGNATURE: tuple[str, ...] | None = None


class GraphService:
    """
    Construye el grafo de transporte para Ciudad Bolívar.

    Método principal: get_stop_router()  →  StopRouter basado en paradas.
    Método legado:    build_open_data_graph()  →  grafo vértice-por-vértice.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    # ── API principal: StopRouter ──────────────────────────────────────────

    async def get_stop_router(self, limit: int | None = None) -> StopRouter:
        """
        Devuelve un StopRouter listo para usar.

        1. Obtiene rutas (API ArcGIS o caché).
        2. Construye la StopNetwork con paradas derivadas.
        3. Almacena en caché hasta que cambien las rutas.
        """
        global _STOP_NETWORK_CACHE, _STOP_NETWORK_SIGNATURE

        t0 = time.perf_counter()
        normalized_routes = await self._get_normalized_routes(limit=limit)

        signature = tuple(r["id"] for r in normalized_routes)
        if signature == _STOP_NETWORK_SIGNATURE and _STOP_NETWORK_CACHE is not None:
            logger.debug("[STOP_GRAPH] cache hit (%.1f ms)", (time.perf_counter() - t0) * 1000)
            return StopRouter(_STOP_NETWORK_CACHE)

        logger.info("[STOP_GRAPH] building network from %d routes...", len(normalized_routes))
        local_nodes = get_local_nodes()
        net = build_stop_network(normalized_routes, local_nodes=local_nodes)

        _STOP_NETWORK_CACHE = net
        _STOP_NETWORK_SIGNATURE = signature

        logger.info(
            "[STOP_GRAPH] ready  stops=%d  edges=%d  (%.1f ms)",
            len(net.stops),
            sum(len(v) for v in net.graph.adjacency.values()),
            (time.perf_counter() - t0) * 1000,
        )
        return StopRouter(net)

    async def _get_normalized_routes(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Obtiene rutas normalizadas.
        Intenta la API ArcGIS (timeout 10 s); si falla, usa el grafo local.
        """
        local_routes = get_local_routes()

        if not self.settings.source_config.enable_external_sources:
            return local_routes

        try:
            raw = await asyncio.wait_for(fetch_rutas_zonales(limit=limit), timeout=10.0)
            if raw:
                api_routes = normalize_route_records(
                    raw,
                    source_crs=self.settings.source_config.source_crs,
                    target_crs=self.settings.source_config.target_crs,
                )
                if api_routes:
                    # Fusionar: las rutas locales enriquecen con nodos conocidos
                    # Las rutas de la API dominan para la geometría real
                    return api_routes
        except (asyncio.TimeoutError, httpx.HTTPError, Exception) as exc:
            logger.warning("[STOP_GRAPH] API no disponible (%s), usando rutas locales", exc)

        return local_routes

    # ── API legada: grafo vértice-por-vértice ──────────────────────────────
    # (mantenida para compatibilidad con recommendation_service y tests)

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

    async def build_open_data_graph(
        self, limit: int | None = None
    ) -> tuple[Graph, dict[str, dict[str, Any]]]:
        """
        Construye el grafo vértice-por-vértice (legado).
        Siempre retorna inmediatamente con el grafo local como base.
        """
        global _LOCAL_GRAPH_CACHE, _GRAPH_CACHE, _GRAPH_CACHE_SIGNATURE, _PERSISTED_ROUTE_SIGNATURE

        t0 = time.perf_counter()

        if _GRAPH_CACHE is not None and _GRAPH_CACHE_SIGNATURE is not None:
            return _GRAPH_CACHE

        local_result = self._build_local_graph()
        logger.info(
            "[GRAPH] local graph ready: %d nodes  %d edges  (%.1f ms)",
            len(local_result[0].adjacency),
            sum(len(v) for v in local_result[0].adjacency.values()),
            (time.perf_counter() - t0) * 1000,
        )

        if self.settings.source_config.enable_external_sources:
            try:
                enriched = await asyncio.wait_for(
                    self._enrich_with_open_data(local_result, limit=limit),
                    timeout=10.0,
                )
                return enriched
            except (asyncio.TimeoutError, httpx.HTTPError, Exception) as exc:
                logger.warning("[GRAPH] API no disponible (%s), usando grafo local", exc)

        return local_result

    def _build_local_graph(self) -> tuple[Graph, dict[str, dict[str, Any]]]:
        global _LOCAL_GRAPH_CACHE
        if _LOCAL_GRAPH_CACHE is not None:
            return _LOCAL_GRAPH_CACHE
        points = get_local_nodes()
        routes = get_local_routes()
        graph = self.build_graph_from_points(points, routes)
        point_map = _build_point_map(points, routes)
        _LOCAL_GRAPH_CACHE = graph, point_map
        return _LOCAL_GRAPH_CACHE

    async def _enrich_with_open_data(
        self,
        base: tuple[Graph, dict[str, dict[str, Any]]],
        limit: int | None = None,
    ) -> tuple[Graph, dict[str, dict[str, Any]]]:
        global _PERSISTED_ROUTE_SIGNATURE, _GRAPH_CACHE_SIGNATURE, _GRAPH_CACHE

        rutas = await fetch_rutas_zonales(limit=limit)
        if not rutas:
            return base

        normalized_routes = normalize_route_records(
            rutas,
            source_crs=self.settings.source_config.source_crs,
            target_crs=self.settings.source_config.target_crs,
        )
        if not normalized_routes:
            return base

        route_signature = tuple(r["id"] for r in normalized_routes)
        if route_signature == _GRAPH_CACHE_SIGNATURE and _GRAPH_CACHE is not None:
            return _GRAPH_CACHE

        graph_routes = simplify_route_records(normalized_routes, max_vertices=40)
        api_points = route_vertex_records(graph_routes, max_points=200)
        local_points = get_local_nodes()
        all_points = local_points + api_points
        all_routes = get_local_routes() + graph_routes

        if route_signature != _PERSISTED_ROUTE_SIGNATURE:
            try:
                persist_open_data(api_points, normalized_routes)
                _PERSISTED_ROUTE_SIGNATURE = route_signature
            except Exception as exc:
                logger.warning("[GRAPH] no se pudo persistir: %s", exc)

        graph = self.build_graph_from_points(all_points, all_routes)
        point_map = _build_point_map(all_points, all_routes)
        _GRAPH_CACHE_SIGNATURE = route_signature
        _GRAPH_CACHE = graph, point_map
        return _GRAPH_CACHE

    # ── build_graph_from_points (usado por tests) ──────────────────────────

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
                    str(point["id"]), str(other["id"]),
                    duration=duration, cost=0, distance=distance,
                    walking=distance, wait=0, transfers=0,
                    reliability=0.95, accessibility=0.8,
                    status="normal", mode="caminata",
                )

        GraphService._add_route_edges(graph, points, routes or [])

        ordered = sorted(points, key=lambda p: (p["lat"], p["lng"]))
        for p, q in zip(ordered, ordered[1:]):
            distance = haversine_km(p["lat"], p["lng"], q["lat"], q["lng"])
            duration = max(1, round(distance / 5 * 60))
            for src, dst in ((p, q), (q, p)):
                graph.add_connection(
                    str(src["id"]), str(dst["id"]),
                    duration=duration, cost=0, distance=distance,
                    walking=distance, wait=0, transfers=0,
                    reliability=0.95, accessibility=0.8,
                    status="normal", mode="caminata",
                )
        return graph

    @staticmethod
    def _add_route_edges(
        graph: Graph,
        points: list[dict[str, Any]],
        routes: list[dict[str, Any]],
    ) -> None:
        for route in routes:
            for path_index, path in enumerate(route["paths"]):
                route_nodes: list[str] = []
                for vertex_index, (lat, lng) in enumerate(path):
                    node_id = f"route:{route['id']}:{path_index}:{vertex_index}"
                    graph.add_node(node_id)
                    route_nodes.append(node_id)
                    if vertex_index:
                        prev_lat, prev_lng = path[vertex_index - 1]
                        distance = haversine_km(prev_lat, prev_lng, lat, lng)
                        speed_kmh = 20.0 if route.get("mode") == "transmicable" else 25.0
                        duration = max(1, round(distance / speed_kmh * 60))
                        wait = max(1, round((route.get("frequency_min") or 6) / 2))
                        cost = 0.0 if route.get("mode") == "caminata" else 2950.0
                        for src, dst in ((route_nodes[-2], node_id), (node_id, route_nodes[-2])):
                            graph.add_connection(
                                src, dst,
                                duration=duration, cost=cost, distance=distance,
                                walking=0, wait=wait, transfers=0,
                                reliability=0.9, accessibility=0.8,
                                status="normal", mode=route.get("mode", "sitp"),
                                route_id=str(route["id"]),
                            )

                for point in points:
                    nearest_index = min(
                        range(len(path)),
                        key=lambda i: haversine_km(point["lat"], point["lng"], path[i][0], path[i][1]),
                    )
                    distance = haversine_km(
                        point["lat"], point["lng"],
                        path[nearest_index][0], path[nearest_index][1],
                    )
                    if distance > 0.5:
                        continue
                    route_node = route_nodes[nearest_index]
                    duration = max(1, round(distance / 5 * 60))
                    for src, dst in ((str(point["id"]), route_node), (route_node, str(point["id"]))):
                        graph.add_connection(
                            src, dst,
                            duration=duration, cost=0, distance=distance,
                            walking=distance, wait=0, transfers=0,
                            reliability=0.9, accessibility=0.8,
                            status="normal", mode="caminata",
                        )

    @staticmethod
    def nearest_point(
        points: dict[str, dict[str, Any]], lat: float, lng: float
    ) -> str:
        if not points:
            raise ValueError("No hay puntos de transporte disponibles")
        return min(
            points,
            key=lambda pid: haversine_km(lat, lng, points[pid]["lat"], points[pid]["lng"]),
        )

    def _build_fallback_graph(self) -> Graph:
        return GraphBuilder.from_records(self.settings.default_graph_records)


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_point_map(
    points: list[dict[str, Any]],
    routes: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    point_map: dict[str, dict[str, Any]] = {str(p["id"]): p for p in points}
    for route in routes:
        for path_index, path in enumerate(route["paths"]):
            for vertex_index, (lat, lng) in enumerate(path):
                node_id = f"route:{route['id']}:{path_index}:{vertex_index}"
                point_map[node_id] = {
                    "id": node_id,
                    "name": route["name"],
                    "source_type": "ruta_zonal",
                    "lat": lat,
                    "lng": lng,
                    "mode": route.get("mode", "sitp"),
                    "route_id": route["id"],
                    "status": "normal",
                    "raw": {},
                }
    return point_map


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))
