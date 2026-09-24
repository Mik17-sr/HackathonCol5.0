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
        "gtfs_sitp": DataSourceDescriptor(
            name="gtfs_sitp",
            provider="gtfs",
            description="GTFS del Sistema Integrado de Transporte Público de Bogotá",
            enabled=True,
        ),
        "transmilenio": DataSourceDescriptor(
            name="transmilenio",
            provider="api",
            description="Información operativa y de estaciones de TransMilenio",
            enabled=False,
        ),
        "transmicable": DataSourceDescriptor(
            name="transmicable",
            provider="api",
            description="Datos de TransMiCable y incidencias",
            enabled=False,
        ),
        "datos_abiertos_bogota": DataSourceDescriptor(
            name="datos_abiertos_bogota",
            provider="api",
            description="Catálogo de datos abiertos de movilidad del distrito",
            enabled=False,
        ),
    }

    @classmethod
    def enabled_sources(cls) -> list[DataSourceDescriptor]:
        return [source for source in cls.SOURCES.values() if source.enabled]
