from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ruta import Ruta


class RutaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Ruta]:
        return self.db.query(Ruta).filter(Ruta.activo.is_(True)).all()

    def create(self, ruta: Ruta) -> Ruta:
        self.db.add(ruta)
        self.db.commit()
        self.db.refresh(ruta)
        return ruta
