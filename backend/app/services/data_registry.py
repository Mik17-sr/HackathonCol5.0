from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataSourceDescriptor:
    name: str
    provider: str
    description: str
    enabled: bool = True


class DataRegistry:
    """Registro central de fuentes de datos para facilitar la integración de datos abiertos."""

    SOURCES = {
        "rutas_sitp_arcgis": DataSourceDescriptor(
            name="rutas_sitp_arcgis",
            provider="arcgis",
            description="FeatureServer 15 de planificación SITP: rutas, geometrías y horarios",
            enabled=True,
        ),
    }

    @classmethod
    def enabled_sources(cls) -> list[DataSourceDescriptor]:
        return [source for source in cls.SOURCES.values() if source.enabled]
