import pytest

from app.route_engine.dijkstra import dijkstra_shortest_path
from app.route_engine.graph import Graph
from app.services.graph_service import GraphService
from app.route_engine.stop_router import StopRouter


def test_dijkstra_shortest_path():
    graph = Graph()
    graph.add_connection("A", "B", duration=10, cost=4, distance=2.0, walking=0.5, wait=1, transfers=0, reliability=0.9, accessibility=0.8, status="normal")
    graph.add_connection("B", "C", duration=8, cost=3, distance=1.5, walking=0.4, wait=1, transfers=0, reliability=0.95, accessibility=0.8, status="normal")
    graph.add_connection("A", "C", duration=20, cost=8, distance=4.0, walking=1.0, wait=2, transfers=1, reliability=0.75, accessibility=0.7, status="normal")

    result = dijkstra_shortest_path(graph, "A", "C")

    assert result["path"] == ["A", "B", "C"]
    assert result["total_time"] == 18
    assert result["total_cost"] == 7


def test_graph_from_normalized_points_routes_by_distance():
    points = [
        {"id": "A", "name": "Origen", "lat": 4.6000, "lng": -74.1000},
        {"id": "B", "name": "Intermedio", "lat": 4.6050, "lng": -74.1000},
        {"id": "C", "name": "Destino", "lat": 4.6100, "lng": -74.1000},
    ]

    graph = GraphService.build_graph_from_points(points, neighbors=1)
    result = dijkstra_shortest_path(graph, "A", "C")

    assert result["path"] == ["A", "B", "C"]
    assert result["total_time"] > 0
    assert result["walking"] > 0


def test_graph_connects_points_to_zonal_route_edges():
    points = [
        {"id": "A", "name": "Origen", "lat": 4.6000, "lng": -74.1000},
        {"id": "B", "name": "Destino", "lat": 4.6100, "lng": -74.1000},
    ]
    routes = [
        {
            "id": "Z1",
            "name": "Ruta Z1",
            "mode": "sitp",
            "paths": [[(4.6000, -74.1000), (4.6050, -74.1000), (4.6100, -74.1000)]],
        }
    ]

    graph = GraphService.build_graph_from_points(points, routes=routes, neighbors=1)

    route_connections = [
        connection
        for connections in graph.adjacency.values()
        for connection in connections
        if connection.route_id == "Z1"
    ]
    assert route_connections
    assert all(connection.mode == "sitp" for connection in route_connections)


def test_dijkstra_groups_segments_of_same_service_and_counts_real_transfers():
    graph = Graph()
    graph.add_connection("A", "B", duration=5, cost=1, distance=1, walking=0, wait=2, transfers=0, reliability=1, accessibility=1, mode="sitp", route_id="C1")
    graph.add_connection("B", "C", duration=5, cost=1, distance=1, walking=0, wait=2, transfers=0, reliability=1, accessibility=1, mode="sitp", route_id="C1")
    graph.add_connection("C", "D", duration=5, cost=1, distance=1, walking=0, wait=2, transfers=0, reliability=1, accessibility=1, mode="sitp", route_id="C2")

    result = dijkstra_shortest_path(graph, "A", "D")

    assert result["transfers"] == 1
    assert len(result["legs"]) == 2
    assert result["legs"][0]["route_id"] == "C1"
    assert result["legs"][1]["route_id"] == "C2"


def test_dijkstra_can_block_a_service_for_an_alternative():
    graph = Graph()
    graph.add_connection("A", "B", duration=5, cost=1, distance=1, walking=0, wait=0, transfers=0, reliability=1, accessibility=1, mode="sitp", route_id="C1")
    graph.add_connection("B", "D", duration=5, cost=1, distance=1, walking=0, wait=0, transfers=0, reliability=1, accessibility=1, mode="sitp", route_id="C1")
    graph.add_connection("A", "C", duration=8, cost=1, distance=1, walking=0, wait=0, transfers=0, reliability=1, accessibility=1, mode="sitp", route_id="C2")
    graph.add_connection("C", "D", duration=8, cost=1, distance=1, walking=0, wait=0, transfers=0, reliability=1, accessibility=1, mode="sitp", route_id="C2")

    result = dijkstra_shortest_path(graph, "A", "D", blocked_route_ids={"C1"})

    assert result["path"] == ["A", "C", "D"]


def test_short_distance_can_be_represented_as_walking_route():
    result = StopRouter._walk_only_result(4.6000, -74.1000, 4.6050, -74.1000, 0.8)

    assert result.found is True
    assert result.total_distance_km == pytest.approx(0.8, abs=0.01)
    assert result.walking_distance_km == pytest.approx(0.8, abs=0.01)
    assert result.bus_distance_km == 0.0
    assert result.transfers == 0
    assert result.segments[0].type == "WALK"
