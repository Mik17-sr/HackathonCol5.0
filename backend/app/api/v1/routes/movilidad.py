from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.schemas.movilidad import EstadoMovilidad
from app.services.mobility_service import MobilityService
from app.services.open_data_service import fetch_ckan_dataset, fetch_estaciones_cable

router = APIRouter(prefix="/api/v1", tags=["movilidad"])

DATASET_BASE = "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search"


@router.get("/movilidad/estado", response_model=EstadoMovilidad)
async def estado_movilidad() -> EstadoMovilidad:
    service = MobilityService()
    return service.get_status()


@router.get("/movilidad/estaciones-cable")
async def obtener_estaciones_cable(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    records = await fetch_estaciones_cable(limit=limit)
    if not records:
        return {"status": "fallback", "count": 0, "data": [], "detail": "No se pudo consultar la fuente pública."}
    return {"status": "success", "count": len(records), "data": records}


@router.get("/movilidad/consulta-multifuente")
async def consultar_datos_integrados(busqueda: str = "Ciudad Bolívar") -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        tareas = [
            client.get(DATASET_BASE, params={"q": busqueda, "limit": 10}),
            client.get(DATASET_BASE, params={"q": "TransMiCable", "limit": 5}),
        ]
        respuestas = await asyncio.gather(*tareas, return_exceptions=True)

    resultados: list[list[dict[str, Any]]] = []
    for resp in respuestas:
        if isinstance(resp, httpx.Response) and resp.status_code == 200:
            resultados.append(resp.json().get("result", {}).get("records", []))
        else:
            resultados.append([])

    return {
        "busqueda": busqueda,
        "rutas_encontradas": resultados[0],
        "estaciones_cable": resultados[1],
    }


@router.get("/movilidad/dataset-open-data")
async def consultar_dataset_open_data(
    query: str | None = None,
    resource_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    try:
        records = await fetch_ckan_dataset(resource_id=resource_id, query=query, limit=limit)
        return {"status": "success", "count": len(records), "data": records}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
