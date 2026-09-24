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
    points = {
        "A": {"id": "A", "name": "Origen", "lat": 4.6000, "lng": -74.1000, "source_type": "parada"},
        "B": {"id": "B", "name": "Destino", "lat": 4.6050, "lng": -74.1000, "source_type": "parada"},
    }

    async def fake_open_data_graph(self, limit=100):
        return GraphService.build_graph_from_points(list(points.values())), points

    monkeypatch.setattr(GraphService, "build_open_data_graph", fake_open_data_graph)
    response = TestClient(app).post(
        "/api/v1/rutas/calcular",
        json={
            "origen": {"lat": 4.6000, "lng": -74.1000},
            "destino": {"lat": 4.6050, "lng": -74.1000},
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert data["ruta"]["path"] == ["A", "B"]
    assert data["ruta"]["legs"]
