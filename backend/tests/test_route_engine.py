from app.route_engine.dijkstra import dijkstra_shortest_path
from app.route_engine.graph import Graph
from app.services.graph_service import GraphService


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
