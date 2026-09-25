from fastapi import APIRouter, HTTPException, Query

from app.route_engine.dijkstra import dijkstra_shortest_path
from app.schemas.ruta import RutaCoordenadasRequest
from app.services.graph_service import GraphService, haversine_km
from app.ingestion.normalizar_datos import normalize_route_records
from app.services.open_data_service import fetch_rutas_zonales

router = APIRouter(prefix="/api/v1", tags=["rutas"])
WALKING_DISTANCE_LIMIT_KM = 1.2


def service_sequence(route: dict[str, object]) -> list[str]:
    services: list[str] = []
    for leg in route.get("legs", []):
        route_id = leg.get("route_id")
        if route_id and route_id not in services:
            services.append(str(route_id))
    return services


def walking_route(source: str, target: str, distance: float) -> dict[str, object]:
    duration = max(1, round(distance / 5 * 60))
    return {
        "path": [source, target],
        "total_time": duration,
        "total_cost": 0.0,
        "walking": distance,
        "wait_time": 0,
        "transfers": 0,
        "reliability": 0.99,
        "legs": [{
            "origen": source,
            "destino": target,
            "modo": "caminata",
            "route_id": None,
            "tiempo": duration,
            "distancia": distance,
        }],
    }


@router.get("/rutas")
async def listar_rutas() -> list[dict[str, object]]:
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
    point_distance = haversine_km(
        points[origin]["lat"], points[origin]["lng"],
        points[destination]["lat"], points[destination]["lng"],
    )
    if point_distance <= WALKING_DISTANCE_LIMIT_KM:
        route = walking_route(origin, destination, point_distance)
    else:
        try:
            route = dijkstra_shortest_path(graph, origin, destination)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    alternatives: list[dict[str, object]] = [route]
    primary_services = service_sequence(route)
    block_sets: list[set[str]] = []
    if primary_services:
        block_sets.extend({service_id} for service_id in (primary_services[0], primary_services[-1]))
        if len(primary_services) > 1:
            block_sets.append(set(primary_services))
    block_sets.extend(
        {str(connection.route_id)}
        for connections in graph.adjacency.values()
        for connection in connections
        if connection.route_id and {str(connection.route_id)} not in block_sets
    )
    for blocked_services in block_sets:
        if len(alternatives) >= 3:
            break
        try:
            candidate = dijkstra_shortest_path(
                graph,
                origin,
                destination,
                blocked_route_ids=blocked_services,
            )
        except ValueError:
            continue
        if all(candidate["path"] != item["path"] for item in alternatives):
            alternatives.append(candidate)

    service_groups = []
    for position in range(2):
        options = sorted({service_sequence(candidate)[position] for candidate in alternatives if len(service_sequence(candidate)) > position})
        if len(options) > 1:
            service_groups.append({"posicion": position, "opciones": options})

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
        "alternativas": [
            {
                **candidate,
                "coordinates": [
                    {"lat": points[node_id]["lat"], "lng": points[node_id]["lng"]}
                    for node_id in candidate["path"]
                    if node_id in points
                ],
            }
            for candidate in alternatives
        ],
        "grupos_servicios": service_groups,
    }


@router.get("/rutas/zonales")
async def listar_rutas_zonales(limit: int | None = Query(default=None, ge=1)) -> dict[str, object]:
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
                "horarios": route["schedule"],
                "atributos": route["raw"],
            }
            for route in routes
        ],
    }
