from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import SessionLocal
from app.models.horario import Horario
from app.repositories.horario_repository import HorarioRepository

router = APIRouter(prefix="/api/v1", tags=["horarios"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/horarios")
async def listar_horarios(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    items = HorarioRepository(db).list_all()
    return [
        {
            "id": horario.id,
            "ruta_id": horario.ruta_id,
            "dia_semana": horario.dia_semana,
            "hora": horario.hora,
            "frecuencia_min": horario.frecuencia_min,
        }
        for horario in items
    ]
