from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.horario import Horario


class HorarioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Horario]:
        return self.db.query(Horario).all()

    def create(self, horario: Horario) -> Horario:
        self.db.add(horario)
        self.db.commit()
        self.db.refresh(horario)
        return horario
