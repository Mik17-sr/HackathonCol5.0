from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.parada import Parada
from app.services.open_data_service import fetch_estaciones_cable

router = APIRouter(prefix="/api/v1", tags=["estaciones"])


def normalize_station(record: dict[str, Any], index: int) -> dict[str, Any] | None:
    lat = record.get("latitud") or record.get("lat")
    lng = record.get("longitud") or record.get("lng")
    if lat is None or lng is None:
        return None
    return {
        "id": str(record.get("objectid") or record.get("id") or f"estacion-{index}"),
        "nombre": record.get("nom_est") or record.get("nombre") or "Estación TransMiCable",
        "codigo": record.get("cod_nodo") or record.get("num_est"),
        "lat": float(lat),
        "lng": float(lng),
        "tipo": "estacion",
        "estado": "operativa" if record.get("esta_oper", 1) else "fuera_de_servicio",
    }


@router.get("/estaciones")
async def listar_estaciones(limit: int = Query(20, ge=1, le=500)) -> dict[str, Any]:
    if not get_settings().source_config.enable_external_sources:
        with SessionLocal() as db:
            records = (
                db.query(Parada)
                .filter(Parada.activo.is_(True), Parada.tipo == "cable")
                .limit(limit)
                .all()
            )
        data = [
            {
                "id": str(record.id),
                "nombre": record.nombre,
                "codigo": record.codigo,
                "lat": record.lat,
                "lng": record.lng,
                "tipo": "estacion",
                "estado": "operativa",
            }
            for record in records
        ]
        return {"status": "local", "count": len(data), "data": data}

    records = await fetch_estaciones_cable(limit=limit)
    data = [item for index, record in enumerate(records) if (item := normalize_station(record, index))]
    if not data:
        return {
            "status": "fallback",
            "count": 0,
            "data": [],
            "detail": "No se encontraron estaciones disponibles en la fuente pública.",
        }
    return {"status": "success", "count": len(data), "data": data}
