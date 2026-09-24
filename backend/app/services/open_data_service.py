from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.services.open_data_cache import open_data_cache
CKAN_BASE = "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search"
CKAN_PACKAGE_SHOW = "https://datosabiertos.bogota.gov.co/api/3/action/package_show"
DEFAULT_RESOURCE_IDS = {
    "estaciones_cable": "9a3bb88a-e977-48cd-8e20-5ca481c19b1d",
    "paraderos_sitp": None,
    "rutas_zonales": None,
}
DATASET_SLUGS = {
    "estaciones_cable": "estaciones-cable",
    "paraderos_sitp": "paraderos-zonales-del-sitp",
    "rutas_zonales": "servicios-rutas-troncales-y-zonales",
}


async def resolve_dataset_resource_url(dataset_slug: str, timeout: float = 10.0) -> str | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                CKAN_PACKAGE_SHOW,
                params={"id": dataset_slug},
                timeout=timeout,
            )
            response.raise_for_status()
            resources = response.json().get("result", {}).get("resources", [])
            for resource in resources:
                url = resource.get("url", "")
                if "FeatureServer" in url or "MapServer" in url:
                    return url
    except Exception:
        return None
    return None


async def resolve_dataset_resource(dataset_slug: str, timeout: float = 10.0) -> str | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                CKAN_PACKAGE_SHOW,
                params={"id": dataset_slug},
                timeout=timeout,
            )
            response.raise_for_status()
            resources = response.json().get("result", {}).get("resources", [])
            for resource in resources:
                if resource.get("datastore_active") and resource.get("id"):
                    return resource["id"]
    except Exception:
        return None
    return None


async def fetch_arcgis_layer(
    layer_url: str,
    limit: int = 20,
    query: str | None = None,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "resultRecordCount": limit,
        "f": "json",
    }
    if query:
        params["resultRecordCount"] = max(limit, 100)

    try:
        async with httpx.AsyncClient() as client:
            for attempt in range(3):
                try:
                    response = await client.get(f"{layer_url}/query", params=params, timeout=timeout)
                    response.raise_for_status()
                    payload = response.json()
                    records = [
                        {**feature.get("attributes", {}), "geometry": feature.get("geometry")}
                        for feature in payload.get("features", [])
                    ]
                    if query:
                        normalized_query = query.casefold()
                        records = [
                            record
                            for record in records
                            if normalized_query in " ".join(str(value) for value in record.values()).casefold()
                        ]
                    return records[:limit]
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.5 * (attempt + 1))
    except Exception:
        return []


async def fetch_ckan_dataset(
    resource_id: str | None = None,
    query: str | None = None,
    limit: int = 20,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": limit}

    if resource_id:
        params["resource_id"] = resource_id
    if query:
        params["q"] = query

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CKAN_BASE, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            return payload.get("result", {}).get("records", [])
    except Exception:
        return []


async def _fetch_estaciones_cable(limit: int = 20) -> list[dict[str, Any]]:
    layer_url = await resolve_dataset_resource_url(DATASET_SLUGS["estaciones_cable"])
    if layer_url:
        return await fetch_arcgis_layer(layer_url=layer_url, limit=limit)
    resource_id = DEFAULT_RESOURCE_IDS["estaciones_cable"]
    return await fetch_ckan_dataset(resource_id=resource_id, limit=limit)


async def _fetch_paraderos_sitp(limit: int = 20, query: str | None = None) -> list[dict[str, Any]]:
    layer_url = await resolve_dataset_resource_url(DATASET_SLUGS["paraderos_sitp"])
    if layer_url:
        return await fetch_arcgis_layer(layer_url=layer_url, limit=limit, query=query)
    resource_id = DEFAULT_RESOURCE_IDS["paraderos_sitp"]
    if resource_id is None:
        resource_id = await resolve_dataset_resource(DATASET_SLUGS["paraderos_sitp"])
    return await fetch_ckan_dataset(resource_id=resource_id, query=query, limit=limit)


async def _fetch_rutas_zonales(limit: int = 20, query: str | None = None) -> list[dict[str, Any]]:
    layer_url = await resolve_dataset_resource_url(DATASET_SLUGS["rutas_zonales"])
    if layer_url:
        return await fetch_arcgis_layer(layer_url=layer_url, limit=limit, query=query)
    resource_id = DEFAULT_RESOURCE_IDS["rutas_zonales"]
    if resource_id is None:
        resource_id = await resolve_dataset_resource(DATASET_SLUGS["rutas_zonales"])
    return await fetch_ckan_dataset(resource_id=resource_id, query=query, limit=limit)


async def fetch_estaciones_cable(limit: int = 20) -> list[dict[str, Any]]:
    return await open_data_cache.get_or_set(
        f"estaciones_cable:{limit}", lambda: _fetch_estaciones_cable(limit)
    )


async def fetch_paraderos_sitp(limit: int = 20, query: str | None = None) -> list[dict[str, Any]]:
    return await open_data_cache.get_or_set(
        f"paraderos_sitp:{limit}:{query or ''}", lambda: _fetch_paraderos_sitp(limit, query)
    )


async def fetch_rutas_zonales(limit: int = 20, query: str | None = None) -> list[dict[str, Any]]:
    return await open_data_cache.get_or_set(
        f"rutas_zonales:{limit}:{query or ''}", lambda: _fetch_rutas_zonales(limit, query)
    )
