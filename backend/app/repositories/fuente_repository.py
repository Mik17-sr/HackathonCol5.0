from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.fuente import FuenteDatos


class FuenteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[FuenteDatos]:
        return self.db.query(FuenteDatos).filter(FuenteDatos.activo.is_(True)).all()

    def create(self, fuente: FuenteDatos) -> FuenteDatos:
        self.db.add(fuente)
        self.db.commit()
        self.db.refresh(fuente)
        return fuente
