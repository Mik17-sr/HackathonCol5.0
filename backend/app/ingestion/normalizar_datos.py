from __future__ import annotations

import re
from typing import Any

from pyproj import Transformer


def _first_value(record: dict[str, Any], *names: str) -> Any:
    normalized = {str(key).casefold(): value for key, value in record.items()}
    for name in names:
        value = normalized.get(name.casefold())
        if value not in (None, ""):
            return value
    return None


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _transform_projected_coordinates(x: float, y: float, source_crs: str, target_crs: str) -> tuple[float, float] | None:
    try:
        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
        lng, lat = transformer.transform(x, y)
    except Exception:
        return None
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return lat, lng
    return None


def _coordinates(record: dict[str, Any], *, source_crs: str, target_crs: str) -> tuple[float, float] | None:
    lat = _number(_first_value(record, "lat", "latitude", "latitud"))
    lng = _number(_first_value(record, "lng", "lon", "longitude", "longitud"))
    if lat is not None and lng is not None:
        return lat, lng

    geometry = record.get("geometry") or {}
    if isinstance(geometry, dict):
        x = _number(geometry.get("x"))
        y = _number(geometry.get("y"))
        if x is not None and y is not None:
            if -90 <= y <= 90 and -180 <= x <= 180:
                return y, x
            transformed = _transform_projected_coordinates(x, y, source_crs, target_crs)
            if transformed is not None:
                return transformed

        coordinates = geometry.get("coordinates")
        if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
            lng = _number(coordinates[0])
            lat = _number(coordinates[1])
            if lat is not None and lng is not None:
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return lat, lng
                return _transform_projected_coordinates(lng, lat, source_crs, target_crs)

    lat = _number(_first_value(record, "y"))
    lng = _number(_first_value(record, "x"))
    if lat is None or lng is None:
        return None
    return _transform_projected_coordinates(lng, lat, source_crs, target_crs)


def normalize_point_records(
    records: list[dict[str, Any]],
    *,
    source_type: str,
    source_crs: str = "EPSG:3116",
    target_crs: str = "EPSG:4326",
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        coordinates = _coordinates(record, source_crs=source_crs, target_crs=target_crs)
        if coordinates is None:
            continue
        lat, lng = coordinates
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue

        raw_id = _first_value(record, "id", "objectid", "codigo", "code", "consecutivo")
        name = _first_value(record, "nombre", "name", "nom_est", "estacion", "direccion")
        identifier = str(raw_id or f"{source_type}-{index}")
        normalized.append(
            {
                "id": identifier,
                "name": str(name or identifier),
                "source_type": source_type,
                "lat": lat,
                "lng": lng,
                "mode": "transmicable" if source_type == "estacion" else "sitp",
                "status": str(_first_value(record, "estado", "status") or "normal").casefold(),
                "raw": record,
            }
        )
    return normalized


def normalize_route_records(
    records: list[dict[str, Any]],
    *,
    source_crs: str = "EPSG:3116",
    target_crs: str = "EPSG:4326",
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        geometry = record.get("geometry") or {}
        paths: list[Any] = []
        if isinstance(geometry, dict):
            geometry_type = geometry.get("type")
            coordinates = geometry.get("coordinates", [])
            if geometry_type == "LineString":
                paths = [coordinates]
            elif geometry_type == "MultiLineString":
                paths = coordinates
            else:
                paths = geometry.get("paths", [])
        valid_paths: list[list[tuple[float, float]]] = []
        for path in paths:
            valid_path: list[tuple[float, float]] = []
            for coordinate in path:
                if not isinstance(coordinate, (list, tuple)) or len(coordinate) < 2:
                    continue
                x = _number(coordinate[0])
                y = _number(coordinate[1])
                if x is None or y is None:
                    continue
                if not (-90 <= y <= 90 and -180 <= x <= 180):
                    transformed = _transform_projected_coordinates(x, y, source_crs, target_crs)
                    if transformed is None:
                        continue
                    y, x = transformed
                valid_path.append((y, x))
            if len(valid_path) >= 2:
                valid_paths.append(valid_path)

        if not valid_paths:
            continue
        route_id = _first_value(record, "cod_ruta", "codigo_ruta", "route_id", "servicio", "codigo", "objectid")
        name = _first_value(record, "nom_ruta", "nombre", "name", "servicio", "ruta")
        frequency = _number(_first_value(record, "frecuencia_min", "frecuencia", "headway", "intervalo"))
        start_time = _first_value(record, "hora_inicio", "inicio", "start_time")
        end_time = _first_value(record, "hora_fin", "fin", "end_time")
        normalized.append(
            {
                "id": str(route_id or f"ruta-{index}"),
                "name": str(name or route_id or f"Ruta {index + 1}"),
                "mode": "sitp",
                "frequency_min": int(frequency) if frequency is not None else None,
                "start_time": str(start_time) if start_time else None,
                "end_time": str(end_time) if end_time else None,
                "schedule": {
                    "habil": _first_value(record, "hor_habil"),
                    "sabado": _first_value(record, "hor_sab"),
                    "festivo": _first_value(record, "hor_fest"),
                },
                "paths": valid_paths,
                "raw": record,
            }
        )
    return normalized


def normalize_search_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def route_vertex_records(
    routes: list[dict[str, Any]],
    max_points: int | None = None,
) -> list[dict[str, Any]]:
    """Deriva puntos de mapa únicamente de los vértices de las rutas oficiales."""
    points: list[dict[str, Any]] = []
    seen: set[tuple[float, float]] = set()
    for route in routes:
        for path_index, path in enumerate(route["paths"]):
            for vertex_index, (lat, lng) in enumerate(path):
                coordinate = (round(lat, 6), round(lng, 6))
                if coordinate in seen:
                    continue
                seen.add(coordinate)
                points.append(
                    {
                        "id": f"route-point:{route['id']}:{path_index}:{vertex_index}",
                        "name": route["name"],
                        "source_type": "punto_ruta",
                        "lat": lat,
                        "lng": lng,
                        "mode": route.get("mode", "sitp"),
                        "status": "normal",
                        "route_id": route["id"],
                        "path_index": path_index,
                        "vertex_index": vertex_index,
                        "raw": route.get("raw", {}),
                    }
                )
                if max_points is not None and len(points) >= max_points:
                    return points
    return points


def simplify_route_records(
    routes: list[dict[str, Any]],
    max_vertices: int = 80,
) -> list[dict[str, Any]]:
    """Reduce vértices para el grafo sin modificar las geometrías publicadas."""
    simplified: list[dict[str, Any]] = []
    for route in routes:
        paths: list[list[tuple[float, float]]] = []
        for path in route["paths"]:
            if len(path) <= max_vertices:
                paths.append(path)
                continue
            indexes = [round(index * (len(path) - 1) / (max_vertices - 1)) for index in range(max_vertices)]
            paths.append([path[index] for index in indexes])
        simplified.append({**route, "paths": paths})
    return simplified
