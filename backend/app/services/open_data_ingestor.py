from __future__ import annotations

from typing import Any

import httpx

from app.integrations.datos_abiertos.cliente import OpenDataClient


class OpenDataIngestor:
    """Orquesta la carga de datasets abiertos y los entrega normalizados al sistema."""

    def __init__(self, provider: str = "gtfs") -> None:
        self.provider = provider

    async def ingest(self, data_dir: str | None = None, gtfs_path: str | None = None) -> list[dict[str, Any]]:
        client = OpenDataClient(provider=self.provider, data_dir=data_dir, gtfs_path=gtfs_path)
        raw = client.fetch()
        if not raw:
            try:
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.get(
                        "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search",
                        params={"q": "Ciudad Bolívar", "limit": 10},
                        timeout=10,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    raw = payload.get("result", {}).get("records", [])
            except Exception:
                raw = []
        return client.normalize(raw)
