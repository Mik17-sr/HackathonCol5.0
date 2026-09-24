from __future__ import annotations

from pathlib import Path
from typing import Any

from app.integrations.datos_abiertos.base_client import BaseDataClient


class GTFSClient(BaseDataClient):
    """Cliente orientado a GTFS y datasets abiertos de transporte."""

    def __init__(self, source_name: str = "gtfs", base_path: str | None = None) -> None:
        super().__init__(source_name, base_path)

    def fetch(self) -> list[dict[str, Any]]:
        if not self.base_path:
            return []

        records: list[dict[str, Any]] = []
        for csv_file in self.base_path.glob("*.csv"):
            records.extend(self._read_csv(csv_file))
        return records

    def normalize(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for record in raw_records:
            normalized.append(
                {
                    "source": record.get("source") or record.get("origin") or "unknown",
                    "destination": record.get("destination") or record.get("target") or "unknown",
                    "duration": int(record.get("duration", 0)),
                    "cost": float(record.get("cost", 0)),
                    "distance": float(record.get("distance", 0.0)),
                    "walking": float(record.get("walking", 0.0)),
                    "wait": int(record.get("wait", 0)),
                    "transfers": int(record.get("transfers", 0)),
                    "reliability": float(record.get("reliability", 0.0)),
                    "accessibility": float(record.get("accessibility", 0.0)),
                    "status": record.get("status", "normal"),
                }
            )
        return normalized

    def _read_csv(self, csv_file: Path) -> list[dict[str, Any]]:
        try:
            import csv

            with csv_file.open("r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                return list(reader)
        except Exception:
            return []
