from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.ingestion.normalizar_datos import normalize_route_records, route_vertex_records
from app.services.local_graph import get_local_nodes
from app.services.open_data_service import fetch_rutas_zonales

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


@router.get("/paradas/local")
async def listar_paradas_local() -> dict[str, Any]:
    """
    Devuelve los nodos del grafo local de Ciudad Bolívar.
    Esta ruta SIEMPRE responde en < 50 ms y no depende de ninguna API externa.
    El frontend la usa como fallback garantizado para poblar el mapa inicial.
    """
    nodes = get_local_nodes()
    data = [
        {
            "id": node["id"],
            "nombre": node["name"],
            "codigo": node["id"],
            "lat": node["lat"],
            "lng": node["lng"],
            "localidad": "Ciudad Bolívar",
            "tipo": node["source_type"],
            "estado": "normal",
        }
        for node in nodes
    ]
    return {"status": "success", "count": len(data), "data": data}


@router.get("/paradas")
async def listar_paradas(
    limit: int | None = Query(None, ge=1, le=100000),
    query: str | None = None,
) -> dict[str, Any]:
    """
    Intenta obtener paradas desde la API de Transmilenio.
    Si no hay datos disponibles, devuelve los nodos del grafo local.
    """
    records = await fetch_rutas_zonales(limit=None, query=query)
    routes = normalize_route_records(records)
    data = [
        {
            "id": point["id"],
            "nombre": point["name"],
            "codigo": point["route_id"],
            "lat": point["lat"],
            "lng": point["lng"],
            "localidad": None,
            "tipo": point["source_type"],
            "estado": point["status"],
        }
        for point in route_vertex_records(routes, max_points=limit)
    ]
    if not data:
        # Fallback garantizado: nodos del grafo local
        local_nodes = get_local_nodes()
        data = [
            {
                "id": node["id"],
                "nombre": node["name"],
                "codigo": node["id"],
                "lat": node["lat"],
                "lng": node["lng"],
                "localidad": "Ciudad Bolívar",
                "tipo": node["source_type"],
                "estado": "normal",
            }
            for node in local_nodes
        ]
        return {"status": "fallback", "count": len(data), "data": data}

    return {"status": "success", "count": len(data), "data": data}


@router.get("/paradas/ciudad-bolivar")
async def listar_paradas_ciudad_bolivar(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    return await listar_paradas(limit=limit, query="Ciudad Bolívar")
