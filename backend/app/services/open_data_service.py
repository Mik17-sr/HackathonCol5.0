from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.services.open_data_cache import open_data_cache
SITP_ROUTES_URL = (
    "https://gis.transmilenio.gov.co/arcgis/rest/services/"
    "ConsultaSubgerenciaPlanificacionSITP/Consulta_Planificacion_SITP/"
    "FeatureServer/15/query"
 )
SITP_CITY_FILTER = "loc_orig = 19 OR loc_dest = 19"


async def fetch_arcgis_layer(
    layer_url: str,
    limit: int | None = None,
    query: str | None = None,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    page_size = min(limit, 1000) if limit else 1000
    params: dict[str, Any] = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "resultRecordCount": page_size,
        "resultOffset": 0,
        "f": "json",
    }
    if query:
        params["resultRecordCount"] = page_size

    try:
        async with httpx.AsyncClient() as client:
            for attempt in range(3):
                try:
                    records: list[dict[str, Any]] = []
                    while True:
                        response = await client.get(f"{layer_url}/query", params=params, timeout=timeout)
                        response.raise_for_status()
                        payload = response.json()
                        page = [
                            {**feature.get("attributes", {}), "geometry": feature.get("geometry")}
                            for feature in payload.get("features", [])
                        ]
                        records.extend(page)
                        if not page or len(page) < page_size or (limit and len(records) >= limit):
                            break
                        params["resultOffset"] += page_size
                    if query:
                        normalized_query = query.casefold()
                        records = [
                            record
                            for record in records
                            if normalized_query in " ".join(str(value) for value in record.values()).casefold()
                        ]
                    return records[:limit] if limit else records
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.5 * (attempt + 1))
    except Exception:
        return []


async def fetch_sitp_routes(
    limit: int | None = None,
    query: str | None = None,
    timeout: float = 30.0,
) -> list[dict[str, Any]]:
    """Obtiene las rutas desde la única fuente oficial configurada."""
    params = {"where": SITP_CITY_FILTER, "outFields": "*", "outSR": "4326", "f": "geojson"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(SITP_ROUTES_URL, params=params, timeout=timeout)
            response.raise_for_status()
            features = response.json().get("features", [])
            records = [
                {**feature.get("properties", {}), "geometry": feature.get("geometry")}
                for feature in features
            ]
            if query:
                normalized_query = query.casefold()
                records = [
                    record
                    for record in records
                    if normalized_query in " ".join(
                        str(value) for key, value in record.items() if key != "geometry"
                    ).casefold()
                ]
            return records[:limit] if limit else records
    except Exception:
        return []


async def fetch_rutas_zonales(limit: int | None = None, query: str | None = None) -> list[dict[str, Any]]:
    return await open_data_cache.get_or_set(
        f"sitp_routes:ciudad_bolivar:{limit}:{query or ''}", lambda: fetch_sitp_routes(limit, query)
    )
