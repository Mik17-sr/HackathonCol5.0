from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseDataClient(ABC):
    """Cliente base para cualquier fuente de datos abiertos de movilidad."""

    def __init__(self, source_name: str, base_path: str | None = None) -> None:
        self.source_name = source_name
        self.base_path = Path(base_path) if base_path else None

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError
