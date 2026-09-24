from __future__ import annotations

from pathlib import Path
from typing import Any

from app.integrations.datos_abiertos.gtfs_client import GTFSClient


class OpenDataClient:
    """Cliente central para datos abiertos de movilidad.

    Permite seleccionar el proveedor real de datos sin tocar la lógica del dominio.
    """

    def __init__(self, provider: str = "sample", data_dir: str | None = None, gtfs_path: str | None = None) -> None:
        self.provider = provider
        self.data_dir = Path(data_dir) if data_dir else None
        self.gtfs_path = Path(gtfs_path) if gtfs_path else None

    def fetch(self) -> list[dict[str, Any]]:
        if self.provider == "gtfs":
            base_path = self.gtfs_path or self.data_dir
            if not base_path:
                return []
            return GTFSClient(base_path=str(base_path)).fetch()
        return []

    def normalize(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.provider == "gtfs":
            base_path = self.gtfs_path or self.data_dir
            if not base_path:
                return []
            return GTFSClient(base_path=str(base_path)).normalize(raw_records)
        return []
