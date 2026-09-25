from fastapi.testclient import TestClient

from app.main import app
from app.services.graph_service import GraphService


def test_chat_recomendar_contract():
    client = TestClient(app)

    payload = {
        "usuario_id": "user_123",
        "mensaje": "Mañana tengo clase a las 7:00 a.m. en la Universidad Distrital. Estoy en Vista Hermosa, quiero llegar 10 minutos antes y caminar lo menos posible.",
        "contexto": {
            "ubicacion_actual": {"lat": 4.5684, "lng": -74.1502},
            "hora_consulta": "2026-09-24T13:00:00Z",
        },
    }

    response = client.post("/api/v1/chat/recomendar", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["usuario_id"] == "user_123"
    assert "mensaje" in data
    assert "alternativas" in data
    assert len(data["alternativas"]) >= 1
    assert data["alternativas"][0]["tipo"] in {"rapida", "confiable", "baja_caminata"}
    assert "respuesta" in data
    assert "resumen" in data


def test_rutas_and_horarios_endpoints_return_data():
    client = TestClient(app)

    rutas = client.get("/api/v1/rutas")
    horarios = client.get("/api/v1/horarios")

    assert rutas.status_code == 200, rutas.text
    assert horarios.status_code == 200, horarios.text
    assert len(rutas.json()) >= 1
    assert len(horarios.json()) >= 1


def test_fuentes_activas_endpoint():
    client = TestClient(app)

    response = client.get("/api/v1/fuentes")

    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_calcular_ruta_usa_grafo_normalizado(monkeypatch):
    """El endpoint delega al StopRouter y devuelve status=success."""
    from app.route_engine.stop_router import StopRouter, RouteResult, Segment
    from app.route_engine.stop_graph import DerivedStop, StopNetwork
    from app.route_engine.graph import Graph

    # Construir una red mínima con dos paradas y una arista de bus
    stop_a = DerivedStop(
        id="S1", lat=4.6000, lng=-74.1000, name="Parada A", route_ids={"R1"}
    )
    stop_b = DerivedStop(
        id="S2", lat=4.6050, lng=-74.1000, name="Parada B", route_ids={"R1"}
    )
    graph = Graph()
    graph.add_connection(
        "S1", "S2",
        duration=5, cost=2950, distance=0.6, walking=0,
        wait=5, transfers=0, reliability=0.9, accessibility=0.8,
        status="normal", mode="sitp", route_id="R1",
    )
    graph.add_connection(
        "S2", "S1",
        duration=5, cost=2950, distance=0.6, walking=0,
        wait=5, transfers=0, reliability=0.9, accessibility=0.8,
        status="normal", mode="sitp", route_id="R1",
    )

    net = StopNetwork(
        stops={"S1": stop_a, "S2": stop_b},
        routes={
            "R1": {
                "id": "R1", "name": "Ruta Test", "mode": "sitp",
                "paths": [[(4.6000, -74.1000), (4.6025, -74.1000), (4.6050, -74.1000)]],
                "raw": {"cod_linea": "R1", "orig_ruta": "Parada A", "dest_ruta": "Parada B"},
            }
        },
        graph=graph,
    )
    stop_a.raw_vertex_index["R1"] = 0
    stop_b.raw_vertex_index["R1"] = 2

    async def fake_get_stop_router(self, limit=100):
        return StopRouter(net)

    monkeypatch.setattr(GraphService, "get_stop_router", fake_get_stop_router)

    response = TestClient(app).post(
        "/api/v1/rutas/calcular",
        json={
            # Origen: ~500 m al sur de S1 (4.6000 - 0.0045 ≈ 500 m)
            # Destino: ~500 m al norte de S2 (4.6050 + 0.0045 ≈ 500 m)
            # Distancia total ≈ 1.4 km > DIRECT_WALK_KM → busca bus
            "origen": {"lat": 4.5955, "lng": -74.1000},
            "destino": {"lat": 4.6095, "lng": -74.1000},
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert "segments" in data
    assert any(s["type"] == "BUS" for s in data["segments"])
