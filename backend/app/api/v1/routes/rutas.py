"""
rutas.py — Endpoints de cálculo de rutas.

POST /api/v1/rutas/calcular
    Delega al StopRouter basado en paradas SITP.
    La respuesta mantiene la estructura preexistente (compatible con el
    frontend actual) y añade el campo `segments` con el detalle completo
    WALK/BUS que el cliente puede usar para la visualización diferenciada.
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Query

from app.schemas.ruta import RutaCoordenadasRequest
from app.services.graph_service import GraphService
from app.ingestion.normalizar_datos import normalize_route_records
from app.services.open_data_service import fetch_rutas_zonales

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["rutas"])


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/rutas")
async def listar_rutas() -> list[dict]:
    rutas = normalize_route_records(await fetch_rutas_zonales(limit=None))
    return [
        {
            "id": ruta["id"],
            "codigo": ruta["id"],
            "nombre": ruta["name"],
            "tipo": ruta["mode"],
            "descripcion": ruta["raw"].get("orig_ruta"),
            "distancia_km": ruta["raw"].get("long_ruta"),
            "horarios": ruta["schedule"],
            "atributos": ruta["raw"],
        }
        for ruta in rutas
    ]


@router.get("/rutas/alternativas")
async def listar_alternativas() -> dict:
    return {
        "alternativas": [
            {"tipo": "rapida", "descripcion": "Menor tiempo estimado"},
            {"tipo": "confiable", "descripcion": "Menor variabilidad"},
            {"tipo": "baja_caminata", "descripcion": "Reduce caminata"},
        ]
    }


@router.post("/rutas/calcular")
async def calcular_ruta(request: RutaCoordenadasRequest) -> dict:
    t_total = time.perf_counter()
    logger.info(
        "[ROUTE] request received  origen=(%.5f,%.5f)  destino=(%.5f,%.5f)",
        request.origen.lat, request.origen.lng,
        request.destino.lat, request.destino.lng,
    )

    # ── Obtener red de paradas ────────────────────────────────────────────
    graph_service = GraphService()
    stop_router = await graph_service.get_stop_router(limit=request.limite_datos)

    # ── Buscar ruta ───────────────────────────────────────────────────────
    results = stop_router.find_route(
        request.origen.lat, request.origen.lng,
        request.destino.lat, request.destino.lng,
    )

    primary = results[0]

    if not primary.found:
        raise HTTPException(status_code=404, detail=primary.error or "Sin ruta disponible.")

    # ── Convertir al formato de respuesta ─────────────────────────────────
    from app.route_engine.stop_router import route_result_to_legacy

    main_legacy = route_result_to_legacy(primary)
    alternatives_legacy = [route_result_to_legacy(r) for r in results]

    # Grupos de servicio (para el frontend: opciones intercambiables)
    service_groups = _build_service_groups(results)

    logger.info(
        "[RESPONSE] total_time=%.1f ms  alternatives=%d",
        (time.perf_counter() - t_total) * 1000, len(results),
    )

    return {
        "status": "success",
        "origen": {"requested": request.origen.model_dump()},
        "destino": {"requested": request.destino.model_dump()},
        # ── Ruta principal ────────────────────────────────────────────────
        "ruta": {
            **main_legacy,
            "coordinates": primary.coordinates,
        },
        # ── Segmentos detallados (WALK/BUS) ───────────────────────────────
        "segments": main_legacy.get("segments", []),
        # ── Alternativas ──────────────────────────────────────────────────
        "alternativas": [
            {
                **alt,
                "coordinates": results[i].coordinates,
            }
            for i, alt in enumerate(alternatives_legacy)
        ],
        "nodos": [],          # vacío — ya no usamos nodos intermedios del grafo viejo
        "grupos_servicios": service_groups,
    }


@router.get("/rutas/zonales")
async def listar_rutas_zonales(limit: int | None = Query(default=None, ge=1)) -> dict:
    records = await fetch_rutas_zonales(limit=limit)
    routes = normalize_route_records(records)
    return {
        "status": "success" if routes else "fallback",
        "count": len(routes),
        "data": [
            {
                "id": r["id"],
                "nombre": r["name"],
                "modo": r["mode"],
                "paths": r["paths"],
                "horarios": r["schedule"],
                "atributos": r["raw"],
            }
            for r in routes
        ],
    }


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_service_groups(results) -> list[dict]:
    """
    Identifica posiciones de servicio donde existen alternativas intercambiables.
    Ejemplo: en posición 0 se puede tomar P44 o HD607.
    """
    from app.route_engine.stop_router import RouteResult

    def services(r: RouteResult) -> list[str]:
        return [s.route_id for s in r.segments if s.type == "BUS" and s.route_id]

    groups = []
    max_pos = max((len(services(r)) for r in results), default=0)
    for pos in range(max_pos):
        opts = sorted({services(r)[pos] for r in results if len(services(r)) > pos})
        if len(opts) > 1:
            groups.append({"posicion": pos, "opciones": opts})
    return groups
