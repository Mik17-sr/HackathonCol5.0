from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query


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
    return {
        "status": "success",
        "count": 0,
        "data": [],
        "detail": "La fuente canónica proporciona rutas; no incluye una capa independiente de estaciones.",
    }
