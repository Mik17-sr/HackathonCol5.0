from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EstadoMovilidad(BaseModel):
    estado: Literal["normal", "demora", "congestion", "incidente", "especial"]
    zona: str
    alerta: str | None = None
    descripcion: str | None = None
