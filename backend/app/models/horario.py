from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Horario(Base):
    __tablename__ = "horarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ruta_id: Mapped[int] = mapped_column(ForeignKey("rutas.id"), nullable=False)
    dia_semana: Mapped[str] = mapped_column(String(20), nullable=False)
    hora: Mapped[str] = mapped_column(String(10), nullable=False)
    frecuencia_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    ruta: Mapped["Ruta"] = relationship("Ruta")
