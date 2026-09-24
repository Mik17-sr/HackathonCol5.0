from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.parada import Parada
from app.repositories.ruta_repository import RutaRepository
from app.route_engine.dijkstra import dijkstra_shortest_path
from app.schemas.ruta import RutaCoordenadasRequest
from app.services.graph_service import GraphService
from app.ingestion.normalizar_datos import normalize_route_records
from app.services.open_data_service import fetch_rutas_zonales

router = APIRouter(prefix="/api/v1", tags=["rutas"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/rutas")
async def listar_rutas(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rutas = RutaRepository(db).list_all()
    return [
        {
            "id": ruta.id,
            "codigo": ruta.codigo,
            "nombre": ruta.nombre,
            "tipo": ruta.tipo,
            "descripcion": ruta.descripcion,
            "distancia_km": ruta.distancia_km,
        }
        for ruta in rutas
    ]


@router.get("/rutas/alternativas")
async def listar_alternativas() -> dict[str, list[dict[str, str]]]:
    return {
        "alternativas": [
            {"tipo": "rapida", "descripcion": "Menor tiempo estimado"},
            {"tipo": "confiable", "descripcion": "Menor variabilidad"},
            {"tipo": "baja_caminata", "descripcion": "Reduce caminata"},
        ]
    }


@router.post("/rutas/calcular")
async def calcular_ruta(request: RutaCoordenadasRequest) -> dict[str, object]:
    graph_service = GraphService()
    graph, points = await graph_service.build_open_data_graph(limit=request.limite_datos)
    if not points:
        raise HTTPException(status_code=503, detail="No hay datos abiertos normalizados para calcular la ruta.")

    origin = graph_service.nearest_point(points, request.origen.lat, request.origen.lng)
    destination = graph_service.nearest_point(points, request.destino.lat, request.destino.lng)
    try:
        route = dijkstra_shortest_path(graph, origin, destination)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "status": "success",
        "origen": {"requested": request.origen.model_dump(), "matched_node": points[origin]},
        "destino": {"requested": request.destino.model_dump(), "matched_node": points[destination]},
        "ruta": {
            **route,
            "coordinates": [
                {"lat": points[node_id]["lat"], "lng": points[node_id]["lng"]}
                for node_id in route["path"]
                if node_id in points
            ],
        },
        "nodos": [points[node_id] for node_id in route["path"]],
    }


@router.get("/rutas/zonales")
async def listar_rutas_zonales(limit: int | None = Query(default=None, ge=1)) -> dict[str, object]:
    if not get_settings().source_config.enable_external_sources:
        with SessionLocal() as db:
            routes = RutaRepository(db).list_all()
            if limit:
                routes = routes[:limit]
            points = (
                db.query(Parada)
                .filter(Parada.activo.is_(True))
                .order_by(Parada.lat, Parada.lng)
                .all()
            )
        path = [[point.lat, point.lng] for point in points]
        data = [
            {
                "id": route.codigo,
                "codigo": route.codigo,
                "nombre": route.nombre,
                "modo": route.tipo or "sitp",
                "paths": [path] if len(path) >= 2 else [],
            }
            for route in routes
            if len(path) >= 2
        ]
        return {"status": "local", "count": len(data), "data": data}

    records = await fetch_rutas_zonales(limit=limit)
    routes = normalize_route_records(records)
    return {
        "status": "success" if routes else "fallback",
        "count": len(routes),
        "data": [
            {
                "id": route["id"],
                "nombre": route["name"],
                "modo": route["mode"],
                "paths": route["paths"],
            }
            for route in routes
        ],
    }
