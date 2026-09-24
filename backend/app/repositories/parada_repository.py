from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.parada import Parada


class ParadaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Parada]:
        return self.db.query(Parada).filter(Parada.activo.is_(True)).all()

    def create(self, parada: Parada) -> Parada:
        self.db.add(parada)
        self.db.commit()
        self.db.refresh(parada)
        return parada
