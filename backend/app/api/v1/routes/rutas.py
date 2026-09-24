from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.repositories.ruta_repository import RutaRepository
from app.route_engine.dijkstra import dijkstra_shortest_path
from app.schemas.ruta import RutaCoordenadasRequest
from app.services.graph_service import GraphService

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
        "ruta": route,
        "nodos": [points[node_id] for node_id in route["path"]],
    }
