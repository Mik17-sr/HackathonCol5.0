from __future__ import annotations

from typing import Any

from app.route_engine.graph import Graph


class GraphBuilder:
    """Construye el grafo a partir de datos estructurados o de fuentes externas."""

    @staticmethod
    def from_records(records: list[dict[str, Any]]) -> Graph:
        graph = Graph()
        for record in records:
            graph.add_connection(
                source=str(record["source"]),
                destination=str(record["destination"]),
                duration=int(record.get("duration", 0)),
                cost=float(record.get("cost", 0)),
                distance=float(record.get("distance", 0.0)),
                walking=float(record.get("walking", 0.0)),
                wait=int(record.get("wait", 0)),
                transfers=int(record.get("transfers", 0)),
                reliability=float(record.get("reliability", 0.0)),
                accessibility=float(record.get("accessibility", 0.0)),
                status=str(record.get("status", "normal")),
            )
        return graph
