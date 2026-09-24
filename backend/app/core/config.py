from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DataSourceConfig:
    provider: str = "sample"
    gtfs_path: str | None = None
    data_dir: str = "data"
    enable_external_sources: bool = False
    database_url: str = "sqlite:///./movete_cb.db"
    cache_ttl_seconds: int = 86400
    open_data_limit: int = 500
    source_crs: str = "EPSG:3116"
    target_crs: str = "EPSG:4326"
    redis_url: str | None = None


@dataclass(frozen=True)
class AppSettings:
    app_name: str = "Muévete CB API"
    default_origin: str = "Vista Hermosa"
    default_destination: str = "Universidad Distrital"
    source_config: DataSourceConfig = field(
        default_factory=lambda: DataSourceConfig(
            provider="sample",
            enable_external_sources=False,
            database_url="sqlite:///./movete_cb.db",
        )
    )
    default_graph_records: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {
                "source": "Vista Hermosa",
                "destination": "Paradero A",
                "duration": 9,
                "cost": 1500,
                "distance": 0.8,
                "walking": 0.8,
                "wait": 2,
                "transfers": 0,
                "reliability": 0.88,
                "accessibility": 0.82,
                "status": "normal",
            },
            {
                "source": "Paradero A",
                "destination": "Estación Sur",
                "duration": 12,
                "cost": 2200,
                "distance": 1.2,
                "walking": 0.2,
                "wait": 3,
                "transfers": 0,
                "reliability": 0.9,
                "accessibility": 0.8,
                "status": "normal",
            },
            {
                "source": "Estación Sur",
                "destination": "TransMiCable",
                "duration": 8,
                "cost": 1800,
                "distance": 1.0,
                "walking": 0.1,
                "wait": 4,
                "transfers": 0,
                "reliability": 0.95,
                "accessibility": 0.9,
                "status": "normal",
            },
            {
                "source": "TransMiCable",
                "destination": "Universidad Distrital",
                "duration": 15,
                "cost": 2600,
                "distance": 1.5,
                "walking": 0.9,
                "wait": 1,
                "transfers": 0,
                "reliability": 0.92,
                "accessibility": 0.83,
                "status": "normal",
            },
            {
                "source": "Vista Hermosa",
                "destination": "Paradero B",
                "duration": 11,
                "cost": 2000,
                "distance": 0.9,
                "walking": 0.6,
                "wait": 1,
                "transfers": 0,
                "reliability": 0.84,
                "accessibility": 0.75,
                "status": "normal",
            },
            {
                "source": "Paradero B",
                "destination": "Universidad Distrital",
                "duration": 19,
                "cost": 3200,
                "distance": 2.2,
                "walking": 1.1,
                "wait": 2,
                "transfers": 1,
                "reliability": 0.81,
                "accessibility": 0.74,
                "status": "normal",
            },
        ]
    )


def get_settings() -> AppSettings:
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    return AppSettings(
        source_config=DataSourceConfig(
            provider=os.getenv("DATA_PROVIDER", "sample"),
            data_dir=os.getenv("DATA_DIR", str(data_dir)),
            enable_external_sources=os.getenv("ENABLE_EXTERNAL_SOURCES", "false").lower() == "true",
            database_url=os.getenv("DATABASE_URL", "sqlite:///./movete_cb.db"),
            cache_ttl_seconds=int(os.getenv("OPEN_DATA_CACHE_TTL", "86400")),
            open_data_limit=int(os.getenv("OPEN_DATA_LIMIT", "500")),
            source_crs=os.getenv("OPEN_DATA_SOURCE_CRS", "EPSG:3116"),
            target_crs=os.getenv("OPEN_DATA_TARGET_CRS", "EPSG:4326"),
            redis_url=os.getenv("REDIS_URL") or None,
        )
    )
