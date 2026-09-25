from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.ingestion.normalizar_datos import normalize_route_records
from app.schemas.movilidad import EstadoMovilidad
from app.services.mobility_service import MobilityService
from app.services.open_data_service import fetch_rutas_zonales

router = APIRouter(prefix="/api/v1", tags=["movilidad"])

@router.get("/movilidad/estado", response_model=EstadoMovilidad)
async def estado_movilidad() -> EstadoMovilidad:
    service = MobilityService()
    return service.get_status()


@router.get("/movilidad/estaciones-cable")
async def obtener_estaciones_cable(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    return {
        "status": "success",
        "count": 0,
        "data": [],
        "detail": "La fuente canónica de rutas no incluye estaciones independientes.",
    }


@router.get("/movilidad/consulta-multifuente")
async def consultar_datos_integrados(busqueda: str = "Ciudad Bolívar") -> dict[str, Any]:
    records = await fetch_rutas_zonales(limit=None, query=busqueda)
    rutas = normalize_route_records(records)

    return {
        "busqueda": busqueda,
        "rutas_encontradas": rutas,
        "estaciones_cable": [],
    }


@router.get("/movilidad/dataset-open-data")
async def consultar_dataset_open_data(
    query: str | None = None,
    resource_id: str | None = None,
    limit: int | None = Query(None, ge=1, le=1000),
) -> dict[str, Any]:
    try:
        records = await fetch_rutas_zonales(limit=limit, query=query)
        data = normalize_route_records(records)
        return {"status": "success", "count": len(data), "data": data}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
