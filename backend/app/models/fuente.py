from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FuenteDatos(Base):
    __tablename__ = "fuentes_datos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # gtfs, ckan, api, csv
    url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
