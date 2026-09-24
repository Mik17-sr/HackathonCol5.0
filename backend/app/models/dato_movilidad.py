from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PuntoMovilidad(Base):
    __tablename__ = "puntos_movilidad"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(250), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    modo: Mapped[str] = mapped_column(String(50), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="normal")
    atributos: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RutaMovilidad(Base):
    __tablename__ = "rutas_movilidad"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(250), nullable=False)
    modo: Mapped[str] = mapped_column(String(50), nullable=False)
    frecuencia_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hora_inicio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    hora_fin: Mapped[str | None] = mapped_column(String(10), nullable=True)
    geometria_geojson: Mapped[str] = mapped_column(Text, nullable=False)
    atributos: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
