from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.parada import Parada
from app.services.open_data_service import fetch_paraderos_sitp

router = APIRouter(prefix="/api/v1", tags=["paradas"])


def normalize_stop(record: dict[str, Any], index: int) -> dict[str, Any] | None:
    lat = record.get("latitud") or record.get("lat")
    lng = record.get("longitud") or record.get("lng")
    if lat is None or lng is None:
        return None
    return {
        "id": str(record.get("objectid") or record.get("id") or f"parada-{index}"),
        "nombre": record.get("nombre") or record.get("direccion_bandera") or "Paradero SITP",
        "codigo": record.get("cenefa") or record.get("consecutivo_zona"),
        "lat": float(lat),
        "lng": float(lng),
        "localidad": record.get("localidad"),
        "tipo": "parada",
        "estado": record.get("estado_multiple") or "normal",
    }


@router.get("/paradas")
async def listar_paradas(
    limit: int = Query(20, ge=1, le=5000),
    query: str | None = None,
) -> dict[str, Any]:
    if not get_settings().source_config.enable_external_sources:
        with SessionLocal() as db:
            query_builder = db.query(Parada).filter(Parada.activo.is_(True))
            if query:
                query_builder = query_builder.filter(Parada.nombre.ilike(f"%{query}%"))
            records = query_builder.limit(limit).all()
        data = [
            {
                "id": str(record.id),
                "nombre": record.nombre,
                "codigo": record.codigo,
                "lat": record.lat,
                "lng": record.lng,
                "localidad": record.zona,
                "tipo": "parada",
                "estado": "normal",
            }
            for record in records
        ]
        return {"status": "local", "count": len(data), "data": data}

    records = await fetch_paraderos_sitp(limit=limit, query=query)
    data = [item for index, record in enumerate(records) if (item := normalize_stop(record, index))]
    if not data:
        return {
            "status": "fallback",
            "count": 0,
            "data": [],
            "detail": "No se encontraron paraderos disponibles en la fuente pública.",
        }
    return {"status": "success", "count": len(data), "data": data}


@router.get("/paradas/ciudad-bolivar")
async def listar_paradas_ciudad_bolivar(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    records = await fetch_paraderos_sitp(limit=limit, query="Ciudad Bolívar")
    if not records:
        raise HTTPException(status_code=503, detail="No se pudo consultar la fuente pública de paraderos.")
    return {"status": "success", "count": len(records), "data": records}
