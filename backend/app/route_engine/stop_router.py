"""
stop_router.py — Motor de búsqueda de rutas basado en paradas SITP.

FLUJO
-----
    Origen (lat, lng)
        ↓
    [paradas cercanas — nearest_stops()]
    STOP_A  0.23 km
    STOP_B  0.31 km
    STOP_C  0.44 km
        ↓
    Dijkstra sobre StopNetwork.graph
    (máx. 2 servicios de transporte)
        ↓
    [paradas cercanas al destino]
    STOP_X  0.28 km
    STOP_Y  0.36 km
        ↓
    Destino (lat, lng)

REGLAS
------
- Caminata SOLO en el primer y último tramo.
- Un transbordo = cambio de route_id entre dos paradas con route_ids compartidos.
- Máximo 2 servicios (Dijkstra ya lo controla con max_services=2).
- No se inventan transbordos peatonales entre paradas sin ruta compartida.
- Si origen/destino están a ≤ DIRECT_WALK_KM se devuelve ruta peatonal directa.
- Si no hay paradas en MAX_WALK_TO_STOP_KM se devuelve NoRouteFound.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.route_engine.dijkstra import dijkstra_shortest_path
from app.route_engine.stop_graph import (
    DerivedStop,
    StopNetwork,
    haversine_km,
    nearest_stops,
    MAX_WALK_TO_STOP_KM,
    WALK_SPEED_KMH,
    DEFAULT_BUS_SPEED_KMH,
)

logger = logging.getLogger(__name__)

DIRECT_WALK_KM: float = 1.0   # distancia bajo la cual se propone caminata directa
MAX_SERVICES: int = 2          # máximo de servicios SITP en una ruta
MAX_TRANSFERS: int = 1         # máximo de transbordos aceptables en el resultado final
MAX_PAIRS: int = 15            # máximo de pares (orig_stop, dest_stop) evaluados


# ── Tipos de resultado ─────────────────────────────────────────────────────

@dataclass
class Segment:
    """Un tramo del recorrido (WALK o BUS)."""
    type: str                   # "WALK" | "BUS"
    distance_km: float
    duration_min: int
    # WALK
    from_label: str = ""
    to_label: str = ""
    # BUS
    route_id: str | None = None
    route_name: str | None = None
    from_stop: DerivedStop | None = None
    to_stop: DerivedStop | None = None
    coordinates: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class RouteResult:
    """Resultado completo de una búsqueda de ruta."""
    found: bool
    segments: list[Segment] = field(default_factory=list)
    total_distance_km: float = 0.0
    walking_distance_km: float = 0.0
    bus_distance_km: float = 0.0
    total_duration_min: int = 0
    transfers: int = 0
    error: str | None = None

    # Nodos del path de Dijkstra (para compatibilidad con el grafo actual)
    path: list[str] = field(default_factory=list)
    # Coordenadas aplanadas para Leaflet
    coordinates: list[dict[str, float]] = field(default_factory=list)


class NoRouteFound(Exception):
    """No existe una ruta SITP válida entre los puntos dados."""


# ── Motor de búsqueda ──────────────────────────────────────────────────────

class StopRouter:
    """
    Calcula rutas de origen a destino usando la StopNetwork.

    Uso::
        router = StopRouter(stop_network)
        result = router.find_route(orig_lat, orig_lng, dest_lat, dest_lng)
    """

    def __init__(self, network: StopNetwork) -> None:
        self.net = network

    # ── API pública ────────────────────────────────────────────────────────

    def find_route(
        self,
        orig_lat: float,
        orig_lng: float,
        dest_lat: float,
        dest_lng: float,
        max_walk_km: float = MAX_WALK_TO_STOP_KM,
        max_alternatives: int = 3,
    ) -> list[RouteResult]:
        """
        Devuelve hasta max_alternatives rutas, ordenadas por
        (transfers ASC, walking_km ASC, duration ASC).

        Siempre devuelve al menos un elemento.
        Si no hay ruta, devuelve [RouteResult(found=False, error=...)].
        """
        t0 = time.perf_counter()

        direct_dist = haversine_km(orig_lat, orig_lng, dest_lat, dest_lng)

        # ── Caso 1: caminata directa ───────────────────────────────────────
        if direct_dist <= DIRECT_WALK_KM:
            logger.info("[ROUTER] direct walk %.3f km", direct_dist)
            return [self._walk_only_result(orig_lat, orig_lng, dest_lat, dest_lng, direct_dist)]

        # ── Paradas candidatas origen ──────────────────────────────────────
        orig_candidates = nearest_stops(self.net, orig_lat, orig_lng, max_km=max_walk_km)
        logger.info("[ORIGIN] nearest stops:")
        for d, s in orig_candidates:
            logger.info("  %s - %.2f km  routes=%s", s.id, d, sorted(s.route_ids))

        if not orig_candidates:
            return [RouteResult(
                found=False,
                error=(
                    f"No hay paradas SITP a menos de {max_walk_km:.1f} km del origen. "
                    "Verifica que el punto esté dentro de Ciudad Bolívar."
                ),
            )]

        # ── Paradas candidatas destino ─────────────────────────────────────
        dest_candidates = nearest_stops(self.net, dest_lat, dest_lng, max_km=max_walk_km)
        logger.info("[DESTINATION] nearest stops:")
        for d, s in dest_candidates:
            logger.info("  %s - %.2f km  routes=%s", s.id, d, sorted(s.route_ids))

        if not dest_candidates:
            return [RouteResult(
                found=False,
                error=(
                    f"No hay paradas SITP a menos de {max_walk_km:.1f} km del destino. "
                    "Verifica que el punto esté dentro de Ciudad Bolívar."
                ),
            )]

        # ── Buscar rutas entre todos los pares de candidatos ───────────────
        # Evaluamos TODOS los pares antes de ordenar, para no elegir
        # prematuramente un par subóptimo (ej. SA→SB en vez de SA→SC).
        results: list[RouteResult] = []
        seen_paths: set[tuple[str, ...]] = set()

        for _, orig_stop in orig_candidates:
            for _, dest_stop in dest_candidates:
                if orig_stop.id == dest_stop.id:
                    continue
                result = self._search(
                    orig_lat, orig_lng,
                    dest_lat, dest_lng,
                    orig_stop, dest_stop,
                )
                if result is None:
                    continue
                path_key = tuple(result.path)
                if path_key in seen_paths:
                    continue
                seen_paths.add(path_key)
                results.append(result)

        if not results:
            logger.info("[ROUTER] no route found")
            return [RouteResult(
                found=False,
                error="No encontramos una ruta SITP válida entre los puntos seleccionados.",
            )]

        # ── Ordenar y deduplicar ───────────────────────────────────────────
        results.sort(key=lambda r: (r.transfers, r.walking_distance_km, r.total_duration_min))
        final = _deduplicate(results)[:max_alternatives]

        logger.info(
            "[ROUTER] %d rutas encontradas en %.1f ms",
            len(final), (time.perf_counter() - t0) * 1000,
        )
        for i, r in enumerate(final):
            logger.info(
                "  [%d] transfers=%d  walk=%.2f km  bus=%.2f km  duration=%d min",
                i, r.transfers, r.walking_distance_km, r.bus_distance_km, r.total_duration_min,
            )
        return final

    # ── Búsqueda para un par concreto de paradas ───────────────────────────

    def _search(
        self,
        orig_lat: float,
        orig_lng: float,
        dest_lat: float,
        dest_lng: float,
        orig_stop: DerivedStop,
        dest_stop: DerivedStop,
    ) -> RouteResult | None:
        """
        Ejecuta Dijkstra entre orig_stop y dest_stop en el grafo de paradas.
        Devuelve None si no hay ruta.
        """
        if orig_stop.id not in self.net.graph.adjacency:
            return None
        if dest_stop.id not in self.net.graph.adjacency:
            return None

        try:
            dijk = dijkstra_shortest_path(
                self.net.graph,
                orig_stop.id,
                dest_stop.id,
                max_services=MAX_SERVICES,
            )
        except ValueError:
            return None

        path = dijk["path"]
        logger.info(
            "[ROUTE SEARCH] %s -> %s  path_len=%d",
            orig_stop.id, dest_stop.id, len(path),
        )

        # ── Construir segmentos ────────────────────────────────────────────
        walk_to_stop = haversine_km(orig_lat, orig_lng, orig_stop.lat, orig_stop.lng)
        walk_from_stop = haversine_km(dest_lat, dest_lng, dest_stop.lat, dest_stop.lng)

        segments: list[Segment] = []

        # Tramo peatonal inicial
        if walk_to_stop > 0.01:
            segments.append(Segment(
                type="WALK",
                distance_km=walk_to_stop,
                duration_min=max(1, round(walk_to_stop / WALK_SPEED_KMH * 60)),
                from_label="origen",
                to_label=orig_stop.name,
            ))

        # Tramos de bus (agrupados por route_id consecutivo)
        segments.extend(self._build_bus_segments(path))

        # Tramo peatonal final
        if walk_from_stop > 0.01:
            segments.append(Segment(
                type="WALK",
                distance_km=walk_from_stop,
                duration_min=max(1, round(walk_from_stop / WALK_SPEED_KMH * 60)),
                from_label=dest_stop.name,
                to_label="destino",
            ))

        # ── Métricas ───────────────────────────────────────────────────────
        walk_km = sum(s.distance_km for s in segments if s.type == "WALK")
        bus_km = sum(s.distance_km for s in segments if s.type == "BUS")
        total_km = walk_km + bus_km
        total_min = sum(s.duration_min for s in segments)
        transfers = max(0, sum(1 for s in segments if s.type == "BUS") - 1)

        # Coordenadas aplanadas para Leaflet
        all_coords: list[dict[str, float]] = [{"lat": orig_lat, "lng": orig_lng}]
        for seg in segments:
            for lat, lng in seg.coordinates:
                all_coords.append({"lat": lat, "lng": lng})
        all_coords.append({"lat": dest_lat, "lng": dest_lng})

        # Registrar en log
        logger.info("[RESULT]")
        logger.info("  walking: %.2f km", walk_km)
        logger.info("  bus:     %.2f km", bus_km)
        logger.info("  transfers: %d", transfers)
        logger.info("  total:   %.2f km  %d min", total_km, total_min)
        for seg in segments:
            if seg.type == "BUS":
                logger.info(
                    "  [BUS %s] %s -> %s  %.2f km",
                    seg.route_id,
                    seg.from_stop.name if seg.from_stop else "?",
                    seg.to_stop.name if seg.to_stop else "?",
                    seg.distance_km,
                )

        return RouteResult(
            found=True,
            segments=segments,
            total_distance_km=round(total_km, 3),
            walking_distance_km=round(walk_km, 3),
            bus_distance_km=round(bus_km, 3),
            total_duration_min=total_min,
            transfers=transfers,
            path=path,
            coordinates=all_coords,
        )

    # ── Construcción de segmentos de bus ───────────────────────────────────

    def _build_bus_segments(self, path: list[str]) -> list[Segment]:
        """
        Agrupa nodos consecutivos del mismo route_id en un segmento BUS.
        Extrae la geometría real de la ruta para las coordenadas.
        """
        if len(path) < 2:
            return []

        segments: list[Segment] = []

        # Acumuladores del segmento en curso
        current_route: str | None = None
        current_from: DerivedStop | None = None
        current_to: DerivedStop | None = None
        current_dist: float = 0.0
        current_dur: int = 0
        current_coords: list[tuple[float, float]] = []

        def flush_segment() -> None:
            nonlocal current_route, current_from, current_to
            nonlocal current_dist, current_dur, current_coords
            if current_route and current_from and current_to:
                route_info = self.net.routes.get(current_route, {})
                raw = route_info.get("raw", {})
                cod_linea = raw.get("cod_linea") or current_route
                nom_ruta = route_info.get("name") or current_route
                segments.append(Segment(
                    type="BUS",
                    route_id=current_route,
                    route_name=f"{cod_linea} · {nom_ruta}",
                    distance_km=round(current_dist, 3),
                    duration_min=max(1, current_dur),
                    from_stop=current_from,
                    to_stop=current_to,
                    coordinates=list(current_coords),
                ))
            current_route = None
            current_from = None
            current_to = None
            current_dist = 0.0
            current_dur = 0
            current_coords = []

        for i in range(len(path) - 1):
            src_id = path[i]
            dst_id = path[i + 1]
            conn = self._find_connection(src_id, dst_id)
            if conn is None:
                flush_segment()
                continue

            src_stop = self.net.stops.get(src_id)
            dst_stop = self.net.stops.get(dst_id)

            # Arista de caminata: cierra bus en curso
            if conn.mode == "caminata" or conn.route_id is None:
                flush_segment()
                continue

            route_id = str(conn.route_id)

            # Cambio de ruta de bus: cerrar el anterior
            if current_route is not None and current_route != route_id:
                # El nodo actual es el último del tramo anterior
                current_to = src_stop
                flush_segment()

            # Abrir nuevo segmento si no hay uno en curso
            if current_route is None:
                current_route = route_id
                current_from = src_stop
                if src_stop:
                    current_coords.append((src_stop.lat, src_stop.lng))

            # Añadir coordenadas intermedias de la geometría real
            geom_coords = self._get_geometry_segment(route_id, src_id, dst_id)
            if geom_coords:
                current_coords.extend(geom_coords)
            elif dst_stop:
                current_coords.append((dst_stop.lat, dst_stop.lng))

            current_dist += conn.distance
            current_dur += conn.duration
            current_to = dst_stop  # actualizar destino provisional

        # Cerrar el último segmento bus abierto
        flush_segment()

        return segments

    def _find_connection(self, src_id: str, dst_id: str):
        """Busca la conexión src→dst en el grafo."""
        for conn in self.net.graph.adjacency.get(src_id, []):
            if conn.destination == dst_id:
                return conn
        return None

    def _get_geometry_segment(
        self,
        route_id: str,
        src_stop_id: str,
        dst_stop_id: str,
    ) -> list[tuple[float, float]]:
        """
        Extrae los vértices intermedios de la geometría entre dos paradas.
        Si no puede determinar los índices, devuelve lista vacía.
        """
        src_stop = self.net.stops.get(src_stop_id)
        dst_stop = self.net.stops.get(dst_stop_id)
        if src_stop is None or dst_stop is None:
            return []

        vi_src = src_stop.raw_vertex_index.get(route_id)
        vi_dst = dst_stop.raw_vertex_index.get(route_id)
        if vi_src is None or vi_dst is None:
            return []

        route = self.net.routes.get(route_id, {})
        paths = route.get("paths", [])
        if not paths:
            return []

        path = paths[0]
        lo, hi = min(vi_src, vi_dst), max(vi_src, vi_dst)
        return path[lo : hi + 1]

    # ── Caso sin bus ───────────────────────────────────────────────────────

    @staticmethod
    def _walk_only_result(
        orig_lat: float,
        orig_lng: float,
        dest_lat: float,
        dest_lng: float,
        distance_km: float,
    ) -> RouteResult:
        duration = max(1, round(distance_km / WALK_SPEED_KMH * 60))
        seg = Segment(
            type="WALK",
            distance_km=distance_km,
            duration_min=duration,
            from_label="origen",
            to_label="destino",
            coordinates=[(orig_lat, orig_lng), (dest_lat, dest_lng)],
        )
        return RouteResult(
            found=True,
            segments=[seg],
            total_distance_km=round(distance_km, 3),
            walking_distance_km=round(distance_km, 3),
            bus_distance_km=0.0,
            total_duration_min=duration,
            transfers=0,
            path=[],
            coordinates=[
                {"lat": orig_lat, "lng": orig_lng},
                {"lat": dest_lat, "lng": dest_lng},
            ],
        )


# ── Deduplicación de alternativas ──────────────────────────────────────────

def _deduplicate(results: list[RouteResult]) -> list[RouteResult]:
    """
    Elimina rutas con exactamente la misma combinación de route_ids de bus,
    conservando la de menor duración en cada grupo.
    """
    seen: dict[tuple[str, ...], RouteResult] = {}
    for r in results:
        key = tuple(
            s.route_id or ""
            for s in r.segments
            if s.type == "BUS" and s.route_id
        )
        if key not in seen or r.total_duration_min < seen[key].total_duration_min:
            seen[key] = r
    return list(seen.values())


# ── Conversión a formato legacy (compatibilidad con graph_service) ─────────

def route_result_to_legacy(
    result: RouteResult,
    orig_stop_name: str = "origen",
    dest_stop_name: str = "destino",
) -> dict[str, Any]:
    """
    Convierte RouteResult al formato de respuesta que espera rutas.py
    (compatible con la estructura preexistente de dijkstra_shortest_path).
    """
    legs: list[dict[str, Any]] = []
    for seg in result.segments:
        if seg.type == "WALK":
            legs.append({
                "origen": seg.from_label,
                "destino": seg.to_label,
                "modo": "caminata",
                "route_id": None,
                "tiempo": seg.duration_min,
                "distancia": seg.distance_km,
            })
        else:
            legs.append({
                "origen": seg.from_stop.name if seg.from_stop else "",
                "destino": seg.to_stop.name if seg.to_stop else "",
                "modo": "sitp",
                "route_id": seg.route_id,
                "tiempo": seg.duration_min,
                "distancia": seg.distance_km,
            })

    return {
        "path": result.path,
        "total_time": result.total_duration_min,
        "total_cost": sum(
            2950.0 for s in result.segments if s.type == "BUS"
        ),
        "walking": result.walking_distance_km,
        "wait_time": len([s for s in result.segments if s.type == "BUS"]) * 5,
        "transfers": result.transfers,
        "reliability": 0.88,
        "legs": legs,
        "coordinates": result.coordinates,
        "segments": _segments_to_dict(result.segments),
    }


def _segments_to_dict(segments: list[Segment]) -> list[dict[str, Any]]:
    result = []
    for seg in segments:
        if seg.type == "WALK":
            result.append({
                "type": "WALK",
                "distance_km": seg.distance_km,
                "duration_min": seg.duration_min,
                "from": seg.from_label,
                "to": seg.to_label,
            })
        else:
            result.append({
                "type": "BUS",
                "route_id": seg.route_id,
                "route_name": seg.route_name,
                "distance_km": seg.distance_km,
                "duration_min": seg.duration_min,
                "from_stop": seg.from_stop.name if seg.from_stop else None,
                "to_stop": seg.to_stop.name if seg.to_stop else None,
                "coordinates": [
                    {"lat": lat, "lng": lng} for lat, lng in seg.coordinates
                ],
            })
    return result
