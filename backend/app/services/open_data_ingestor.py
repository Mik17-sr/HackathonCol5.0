from __future__ import annotations

from typing import Any

from app.services.open_data_service import fetch_sitp_routes


class OpenDataIngestor:
    """Orquesta la carga de datasets abiertos y los entrega normalizados al sistema."""

    def __init__(self, provider: str = "arcgis") -> None:
        self.provider = provider

    async def ingest(self, data_dir: str | None = None, gtfs_path: str | None = None) -> list[dict[str, Any]]:
        return await fetch_sitp_routes(limit=None)
