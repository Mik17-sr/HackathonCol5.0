from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.services.open_data_service import fetch_estaciones_cable

router = APIRouter(prefix="/api/v1", tags=["estaciones"])


@router.get("/estaciones")
async def listar_estaciones(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    records = await fetch_estaciones_cable(limit=limit)
    if not records:
        return {
            "status": "fallback",
            "count": 0,
            "data": [],
            "detail": "No se encontraron estaciones disponibles en la fuente pública.",
        }
    return {"status": "success", "count": len(records), "data": records}
