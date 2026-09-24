from fastapi.testclient import TestClient

from app.main import app


def test_estaciones_cable_open_data_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/movilidad/estaciones-cable?limit=5")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] in {"success", "fallback"}
    assert "data" in data
    assert isinstance(data["data"], list)


def test_consulta_multifuente_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/movilidad/consulta-multifuente?busqueda=Ciudad Bolivar")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "busqueda" in data
    assert "rutas_encontradas" in data
    assert "estaciones_cable" in data
