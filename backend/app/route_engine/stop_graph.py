"""
stop_graph.py — Grafo de transporte basado en paradas derivadas SITP.

CONCEPTO
--------
La fuente ArcGIS (FeatureServer/15) proporciona geometrías de rutas SITP,
no una capa oficial de paraderos.  Por eso usamos "paradas derivadas":

    Tipo 1 — EXTREMO DE RUTA
        El promedio de los primeros/últimos 3 vértices de la geometría.
        Representa el punto de inicio/fin del servicio.
        Nombre: "<cod_linea> · <orig_ruta>" / "<cod_linea> · <dest_ruta>"

    Tipo 2 — PUNTO DE TRANSFERENCIA
        Cuando dos geometrías de rutas distintas tienen vértices a ≤ XFER_RADIUS_M.
        Representa un punto donde es posible transbordar entre servicios.

    Tipo 3 — PARADA FIJA (grafo local)
        Los ~20 nodos de local_graph.py, verificados manualmente.
        Actúan como paradas conocidas con route_ids asignados por proximidad.

LIMITACIONES DOCUMENTADAS
--------------------------
- Las paradas derivadas NO son paraderos oficiales.  No tienen código de cenefa
  ni posición exacta en la acera; son aproximaciones geométricas.
- El campo 'sentido' no existe en el dataset.  Las aristas son bidireccionales.
- frecuencia_min no está disponible; se usa un valor por defecto de 10 min.

DISTANCIA ENTRE PARADAS
-----------------------
Para aristas dentro de una misma ruta se acumula la longitud de la geometría
entre los índices de vértice, NO Haversine directo entre paradas.
Esto produce la distancia real recorrida por el bus.
"""
from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Any

from app.route_engine.graph import Connection, Graph

logger = logging.getLogger(__name__)

# ── Parámetros configurables ───────────────────────────────────────────────
MAX_WALK_TO_STOP_KM: float = 0.8      # distancia máxima peatonal para aceptar una parada
XFER_RADIUS_M: float = 50.0           # radio para detectar puntos de transferencia
STOP_ANCHOR_VERTICES: int = 3         # vértices promediados para calcular extremo
DEFAULT_BUS_SPEED_KMH: float = 22.0   # velocidad media del bus en Ciudad Bolívar
DEFAULT_FREQ_MIN: int = 10            # frecuencia por defecto cuando no está disponible
BUS_FARE: float = 2950.0              # tarifa estándar SITP (COP)
WALK_SPEED_KMH: float = 5.0          # velocidad peatonal


# ── Estructura de parada derivada ──────────────────────────────────────────

@dataclass
class DerivedStop:
    """
    Parada derivada de la geometría de una o más rutas SITP.

    Attributes
    ----------
    id:        identificador único, ej. "stop:P44-3:orig"
    lat/lng:   coordenadas WGS-84
    name:      nombre legible para el usuario
    route_ids: conjunto de cod_ruta que sirven esta parada
    source:    "derived_endpoint" | "derived_transfer" | "local"
    raw_vertex_index: índice del vértice en la geometría de cada ruta
                      {route_id: vertex_index}  — usado para calcular distancia
    """
    id: str
    lat: float
    lng: float
    name: str
    route_ids: set[str] = field(default_factory=set)
    source: str = "derived"
    raw_vertex_index: dict[str, int] = field(default_factory=dict)


# ── Red de paradas ─────────────────────────────────────────────────────────

@dataclass
class StopNetwork:
    """
    Red de transporte basada en paradas SITP.

    Attributes
    ----------
    stops:      dict stop_id → DerivedStop
    routes:     dict route_id → ruta normalizada completa (con paths)
    graph:      grafo Dijkstra-compatible (paradas como nodos)
    """
    stops: dict[str, DerivedStop] = field(default_factory=dict)
    routes: dict[str, dict[str, Any]] = field(default_factory=dict)
    graph: Graph = field(default_factory=Graph)


# ── Constructor principal ──────────────────────────────────────────────────

def build_stop_network(
    normalized_routes: list[dict[str, Any]],
    local_nodes: list[dict[str, Any]] | None = None,
) -> StopNetwork:
    """
    Construye la red de paradas a partir de rutas normalizadas.

    Parámetros
    ----------
    normalized_routes:  salida de normalize_route_records() — cada elemento
                        tiene id, name, mode, paths, raw (con orig_ruta, dest_ruta…)
    local_nodes:        nodos del grafo local (local_graph.py) — opcionales
    """
    net = StopNetwork()

    # 1. Indexar rutas
    for route in normalized_routes:
        net.routes[route["id"]] = route

    # 2. Crear paradas de extremo para cada ruta
    for route in normalized_routes:
        _add_endpoint_stops(net, route)

    # 3. Detectar puntos de transferencia
    _add_transfer_stops(net, normalized_routes)

    # 4. Incorporar paradas del grafo local
    if local_nodes:
        _add_local_stops(net, local_nodes, normalized_routes)

    # 5. Construir aristas del grafo
    _build_graph_edges(net)

    n_stops = len(net.stops)
    n_edges = sum(len(v) for v in net.graph.adjacency.values())
    logger.info(
        "[STOP_GRAPH] built: %d stops  %d edges  %d routes",
        n_stops, n_edges, len(net.routes),
    )
    return net


# ── Paso 2: extremos de ruta ───────────────────────────────────────────────

def _anchor_point(vertices: list[tuple[float, float]], from_end: bool = False) -> tuple[float, float]:
    """Promedia los primeros (o últimos) STOP_ANCHOR_VERTICES para suavizar ruido GPS."""
    n = STOP_ANCHOR_VERTICES
    if from_end:
        sample = vertices[-n:] if len(vertices) >= n else vertices
    else:
        sample = vertices[:n] if len(vertices) >= n else vertices
    lat = sum(v[0] for v in sample) / len(sample)
    lng = sum(v[1] for v in sample) / len(sample)
    return lat, lng


def _add_endpoint_stops(net: StopNetwork, route: dict[str, Any]) -> None:
    route_id = route["id"]
    raw = route.get("raw", {})
    cod_linea = raw.get("cod_linea") or route_id
    orig_name = raw.get("orig_ruta") or "Origen"
    dest_name = raw.get("dest_ruta") or "Destino"

    for path_idx, path in enumerate(route["paths"]):
        if len(path) < 2:
            continue

        # Extremo origen
        orig_lat, orig_lng = _anchor_point(path, from_end=False)
        orig_vid = 0
        orig_id = f"stop:{route_id}:{path_idx}:orig"
        _upsert_stop(
            net,
            stop_id=orig_id,
            lat=orig_lat,
            lng=orig_lng,
            name=f"{cod_linea} · {orig_name}",
            route_id=route_id,
            vertex_index=orig_vid,
            source="derived_endpoint",
        )

        # Extremo destino
        dest_lat, dest_lng = _anchor_point(path, from_end=True)
        dest_vid = len(path) - 1
        dest_id = f"stop:{route_id}:{path_idx}:dest"
        _upsert_stop(
            net,
            stop_id=dest_id,
            lat=dest_lat,
            lng=dest_lng,
            name=f"{cod_linea} · {dest_name}",
            route_id=route_id,
            vertex_index=dest_vid,
            source="derived_endpoint",
        )


# ── Paso 3: transferencias ─────────────────────────────────────────────────

def _add_transfer_stops(net: StopNetwork, routes: list[dict[str, Any]]) -> None:
    """
    Detecta vértices cercanos entre rutas distintas y crea paradas de
    transferencia.  Solo se examinan vértices cada SAMPLE_STEP para
    mantener el tiempo de cómputo < 500 ms incluso con 55 rutas de 1300 vértices.
    """
    SAMPLE_STEP = 15  # examinar 1 de cada 15 vértices (~87 por ruta de 1300)

    # Índice: (route_id, path_idx, vertex_idx) → (lat, lng)
    index: list[tuple[str, int, int, float, float]] = []
    for route in routes:
        for pi, path in enumerate(route["paths"]):
            for vi in range(0, len(path), SAMPLE_STEP):
                lat, lng = path[vi]
                index.append((route["id"], pi, vi, lat, lng))

    # Buscar pares cercanos entre rutas distintas
    radius_deg = (XFER_RADIUS_M / 1000.0) / 111.0  # ~deg por km
    seen_pairs: set[frozenset[str]] = set()

    for i, (rid_a, pi_a, vi_a, lat_a, lng_a) in enumerate(index):
        for rid_b, pi_b, vi_b, lat_b, lng_b in index[i + 1:]:
            if rid_a == rid_b:
                continue
            # Filtro rápido por bounding box
            if abs(lat_b - lat_a) > radius_deg or abs(lng_b - lng_a) > radius_deg:
                continue
            dist_m = haversine_km(lat_a, lng_a, lat_b, lng_b) * 1000
            if dist_m > XFER_RADIUS_M:
                continue
            pair = frozenset({rid_a, rid_b})
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # Usar el vértice de la ruta con id lexicográficamente menor como canónico
            if rid_a <= rid_b:
                lat, lng, canon_rid, canon_vi, canon_pi = lat_a, lng_a, rid_a, vi_a, pi_a
                other_rid, other_vi = rid_b, vi_b
            else:
                lat, lng, canon_rid, canon_vi, canon_pi = lat_b, lng_b, rid_b, vi_b, pi_b
                other_rid, other_vi = rid_a, vi_a

            xfer_id = f"xfer:{canon_rid}:{other_rid}"
            raw_a = net.routes.get(rid_a, {}).get("raw", {})
            raw_b = net.routes.get(rid_b, {}).get("raw", {})
            cl_a = raw_a.get("cod_linea") or rid_a
            cl_b = raw_b.get("cod_linea") or rid_b
            xfer_name = f"Transferencia {cl_a} / {cl_b}"

            stop = _upsert_stop(
                net,
                stop_id=xfer_id,
                lat=lat,
                lng=lng,
                name=xfer_name,
                route_id=canon_rid,
                vertex_index=canon_vi,
                source="derived_transfer",
            )
            # También registrar la segunda ruta en esta parada
            stop.route_ids.add(other_rid)
            # Guardar índice de vértice para la segunda ruta (usamos el propio vi)
            stop.raw_vertex_index[other_rid] = other_vi


# ── Paso 4: paradas locales ────────────────────────────────────────────────

def _add_local_stops(
    net: StopNetwork,
    local_nodes: list[dict[str, Any]],
    routes: list[dict[str, Any]],
) -> None:
    """
    Incorpora los nodos del grafo local como paradas.
    Cada nodo local se asigna a las rutas cuya geometría pase a ≤ 300 m.
    """
    ASSIGN_RADIUS_KM = 0.30

    for node in local_nodes:
        nid = f"local:{node['id']}" if not str(node["id"]).startswith("local:") else str(node["id"])
        stop = DerivedStop(
            id=nid,
            lat=float(node["lat"]),
            lng=float(node["lng"]),
            name=str(node.get("name", nid)),
            source="local",
        )

        # Asignar a rutas cercanas
        for route in routes:
            for pi, path in enumerate(route["paths"]):
                nearest_vi, nearest_dist = _nearest_vertex(path, stop.lat, stop.lng)
                if nearest_dist <= ASSIGN_RADIUS_KM:
                    stop.route_ids.add(route["id"])
                    if route["id"] not in stop.raw_vertex_index:
                        stop.raw_vertex_index[route["id"]] = nearest_vi

        net.stops[nid] = stop
        net.graph.add_node(nid)


# ── Paso 5: construir aristas ──────────────────────────────────────────────

def _build_graph_edges(net: StopNetwork) -> None:
    """
    Para cada ruta, ordena las paradas que la sirven por su índice de vértice
    y crea aristas consecutivas con distancia real sobre la geometría.
    """
    for route_id, route in net.routes.items():
        freq = route.get("frequency_min") or DEFAULT_FREQ_MIN
        mode = route.get("mode", "sitp")

        for path_idx, path in enumerate(route["paths"]):
            # Paradas que sirven esta ruta en este path, ordenadas por vértice
            serving: list[tuple[int, DerivedStop]] = []
            for stop in net.stops.values():
                if route_id not in stop.route_ids:
                    continue
                vi = stop.raw_vertex_index.get(route_id)
                if vi is None:
                    continue
                serving.append((vi, stop))

            if len(serving) < 2:
                continue

            serving.sort(key=lambda x: x[0])

            # Crear aristas entre paradas consecutivas
            for (vi_a, stop_a), (vi_b, stop_b) in zip(serving, serving[1:]):
                if vi_a == vi_b:
                    continue

                # Distancia real sobre la geometría
                dist_km = _path_distance(path, min(vi_a, vi_b), max(vi_a, vi_b))
                if dist_km <= 0:
                    dist_km = haversine_km(stop_a.lat, stop_a.lng, stop_b.lat, stop_b.lng)

                duration = max(1, round(dist_km / DEFAULT_BUS_SPEED_KMH * 60))
                wait = max(1, round(freq / 2))

                cost = 0.0 if mode == "caminata" else BUS_FARE

                # Bidireccional — el sentido real no está disponible en el dataset
                for src, dst in ((stop_a.id, stop_b.id), (stop_b.id, stop_a.id)):
                    net.graph.add_connection(
                        src, dst,
                        duration=duration,
                        cost=cost,
                        distance=dist_km,
                        walking=0.0,
                        wait=wait,
                        transfers=0,
                        reliability=0.88,
                        accessibility=0.8,
                        status="normal",
                        mode=mode,
                        route_id=route_id,
                    )


# ── Helpers geométricos ────────────────────────────────────────────────────

def _path_distance(
    path: list[tuple[float, float]],
    from_vi: int,
    to_vi: int,
) -> float:
    """Suma de segmentos Haversine entre vértices from_vi..to_vi (inclusive)."""
    total = 0.0
    for i in range(from_vi, min(to_vi, len(path) - 1)):
        total += haversine_km(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
    return total


def _nearest_vertex(
    path: list[tuple[float, float]],
    lat: float,
    lng: float,
) -> tuple[int, float]:
    """Devuelve (índice, distancia_km) del vértice más cercano en el path."""
    best_i, best_d = 0, float("inf")
    for i, (vlat, vlng) in enumerate(path):
        d = haversine_km(lat, lng, vlat, vlng)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i, best_d


def _upsert_stop(
    net: StopNetwork,
    *,
    stop_id: str,
    lat: float,
    lng: float,
    name: str,
    route_id: str,
    vertex_index: int,
    source: str,
) -> DerivedStop:
    """Crea o recupera una parada y le añade la ruta indicada."""
    if stop_id not in net.stops:
        net.stops[stop_id] = DerivedStop(
            id=stop_id,
            lat=lat,
            lng=lng,
            name=name,
            source=source,
        )
        net.graph.add_node(stop_id)
    stop = net.stops[stop_id]
    stop.route_ids.add(route_id)
    if route_id not in stop.raw_vertex_index:
        stop.raw_vertex_index[route_id] = vertex_index
    return stop


# ── Búsqueda de paradas cercanas ───────────────────────────────────────────

def nearest_stops(
    net: StopNetwork,
    lat: float,
    lng: float,
    max_km: float = MAX_WALK_TO_STOP_KM,
    limit: int = 5,
) -> list[tuple[float, DerivedStop]]:
    """
    Devuelve hasta `limit` paradas a ≤ max_km del punto dado,
    ordenadas por distancia ascendente.
    Solo incluye paradas que sirven al menos una ruta de transporte
    (excluye nodos con route_ids vacío).
    """
    candidates: list[tuple[float, DerivedStop]] = []
    for stop in net.stops.values():
        if not stop.route_ids:
            continue
        d = haversine_km(lat, lng, stop.lat, stop.lng)
        if d <= max_km:
            candidates.append((d, stop))
    candidates.sort(key=lambda x: x[0])
    return candidates[:limit]


# ── Haversine ──────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(lng_delta := math.radians(lng2 - lng1)) ** 2
    )
    # Recalcular sin usar := dos veces
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))
