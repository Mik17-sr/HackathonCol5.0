from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Connection:
    destination: str
    duration: int
    cost: float
    distance: float
    walking: float
    wait: int
    transfers: int
    reliability: float
    accessibility: float
    status: str = "normal"
    mode: str = "caminata"
    route_id: str | None = None


@dataclass
class Graph:
    adjacency: Dict[str, List[Connection]] = field(default_factory=dict)

    def add_node(self, node: str) -> None:
        self.adjacency.setdefault(node, [])

    def add_connection(
        self,
        source: str,
        destination: str,
        *,
        duration: int,
        cost: float,
        distance: float,
        walking: float,
        wait: int,
        transfers: int,
        reliability: float,
        accessibility: float,
        status: str = "normal",
        mode: str = "caminata",
        route_id: str | None = None,
    ) -> None:
        self.add_node(source)
        self.add_node(destination)
        self.adjacency.setdefault(source, []).append(
            Connection(
                destination=destination,
                duration=duration,
                cost=cost,
                distance=distance,
                walking=walking,
                wait=wait,
                transfers=transfers,
                reliability=reliability,
                accessibility=accessibility,
                status=status,
                mode=mode,
                route_id=route_id,
            )
        )
