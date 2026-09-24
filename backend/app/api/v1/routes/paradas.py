from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.open_data_service import fetch_paraderos_sitp

router = APIRouter(prefix="/api/v1", tags=["paradas"])


@router.get("/paradas")
async def listar_paradas(
    limit: int = Query(20, ge=1, le=100),
    query: str | None = None,
) -> dict[str, Any]:
    records = await fetch_paraderos_sitp(limit=limit, query=query)
    if not records:
        return {
            "status": "fallback",
            "count": 0,
            "data": [],
            "detail": "No se encontraron paraderos disponibles en la fuente pública.",
        }
    return {"status": "success", "count": len(records), "data": records}


@router.get("/paradas/ciudad-bolivar")
async def listar_paradas_ciudad_bolivar(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    records = await fetch_paraderos_sitp(limit=limit, query="Ciudad Bolívar")
    if not records:
        raise HTTPException(status_code=503, detail="No se pudo consultar la fuente pública de paraderos.")
    return {"status": "success", "count": len(records), "data": records}
