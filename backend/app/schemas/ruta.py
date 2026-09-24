from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SegmentoRuta(BaseModel):
    origen: str
    destino: str
    modo: Literal["caminata", "sitp", "transmilenio", "transmicable", "bicicleta", "otro"]
    tiempo: int = Field(..., ge=0)
    costo: float = Field(default=0.0, ge=0)
    distancia: float = Field(default=0.0, ge=0)


class RutaBase(BaseModel):
    id: str
    origen: str
    destino: str
    tipo: Literal["rapida", "confiable", "baja_caminata", "multimodal"]
    tiempo_estimado: int = Field(..., ge=0)
    costo_total: float = Field(default=0.0, ge=0)
    caminata_total: float = Field(default=0.0, ge=0)
    transbordos: int = Field(default=0, ge=0)
    espera_total: int = Field(default=0, ge=0)
    confiabilidad: float = Field(default=0.0, ge=0, le=1)
    segmentos: list[SegmentoRuta] = Field(default_factory=list)


class CoordenadasRuta(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class RutaCoordenadasRequest(BaseModel):
    origen: CoordenadasRuta
    destino: CoordenadasRuta
    limite_datos: int = Field(default=100, ge=2, le=500)
