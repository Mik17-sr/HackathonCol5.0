from __future__ import annotations

from pydantic import BaseModel, Field


class ParadaBase(BaseModel):
    id: str | None = None
    nombre: str
    codigo: str | None = None
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    zona: str | None = None
    tipo: str | None = None
    activo: bool = True


class EstacionBase(BaseModel):
    id: str | None = None
    nombre: str
    codigo: str | None = None
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    zona: str | None = None
    tipo: str = "estacion"
    activo: bool = True
