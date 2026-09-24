from app.core.config import get_settings
from app.route_engine.dijkstra import dijkstra_shortest_path
from app.route_engine.graph import Graph
from app.schemas.chat import RecomendacionRequest, RecomendacionResponse, RutaAlternativa
from app.services.graph_service import GraphService


class RecommendationService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.graph_service = GraphService()
        self.graph: Graph = self.graph_service.build_graph()

    async def create_recommendation(self, payload: RecomendacionRequest) -> RecomendacionResponse:
        origin = self.settings.default_origin
        destination = self.settings.default_destination
        route = None
        point_names: dict[str, str] = {}

        if payload.contexto.destino is not None:
            open_graph, points = await self.graph_service.build_open_data_graph(limit=100)
            if points:
                origin_id = self.graph_service.nearest_point(
                    points, payload.contexto.ubicacion_actual.lat, payload.contexto.ubicacion_actual.lng
                )
                destination_id = self.graph_service.nearest_point(
                    points, payload.contexto.destino.lat, payload.contexto.destino.lng
                )
                route = dijkstra_shortest_path(open_graph, origin_id, destination_id)
                origin = points[origin_id]["name"]
                destination = points[destination_id]["name"]
                point_names = {point_id: point["name"] for point_id, point in points.items()}

        if route is None:
            route = dijkstra_shortest_path(self.graph, origin, destination)

        path_names = [point_names.get(node, node) for node in route["path"]]

        alternatives = [
            RutaAlternativa(
                tipo="rapida",
                tiempo_estimado=int(route["total_time"]),
                costo=float(route["total_cost"]),
                caminata=float(route["walking"]),
                transbordos=int(route["transfers"]),
                espera=int(route["wait_time"]),
                confiabilidad=float(route["reliability"]),
                segmentos=[f"{source} → {target}" for source, target in zip(path_names, path_names[1:])],
            ),
            RutaAlternativa(
                tipo="confiable",
                tiempo_estimado=int(route["total_time"]) + 6,
                costo=float(route["total_cost"]) + 600,
                caminata=1.2,
                transbordos=1,
                espera=4,
                confiabilidad=0.96,
                segmentos=[f"{source} → {target}" for source, target in zip(path_names, path_names[1:])],
            ),
            RutaAlternativa(
                tipo="baja_caminata",
                tiempo_estimado=int(route["total_time"]) + 10,
                costo=float(route["total_cost"]) + 900,
                caminata=0.7,
                transbordos=0,
                espera=5,
                confiabilidad=0.94,
                segmentos=[f"{source} → {target}" for source, target in zip(path_names, path_names[1:])],
            ),
        ]

        return RecomendacionResponse(
            usuario_id=payload.usuario_id,
            mensaje=payload.mensaje,
            respuesta=(
                "Se recomienda priorizar la ruta que equilibra tiempo, confiabilidad y caminata, "
                "evitando transbordos innecesarios y reduciendo la espera al mínimo."
            ),
            resumen=(
                "La mejor alternativa combina transporte público con una caminata moderada y mantiene "
                "una alta confiabilidad para llegar a la hora objetivo."
            ),
            alternativas=alternatives,
        )
