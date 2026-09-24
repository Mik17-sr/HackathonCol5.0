import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.repositories.fuente_repository import FuenteRepository
from app.services.open_data_service import (
    fetch_estaciones_cable,
    fetch_paraderos_sitp,
    fetch_rutas_zonales,
)

router = APIRouter(prefix="/api/v1", tags=["fuentes"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/fuentes")
async def listar_fuentes(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    fuentes = FuenteRepository(db).list_all()
    return [
        {
            "id": fuente.id,
            "nombre": fuente.nombre,
            "tipo": fuente.tipo,
            "url": fuente.url,
            "descripcion": fuente.descripcion,
        }
        for fuente in fuentes
    ]


@router.get("/fuentes/estado")
async def estado_fuentes() -> list[dict[str, object]]:
    resultados = await asyncio.gather(
        fetch_estaciones_cable(limit=1),
        fetch_paraderos_sitp(limit=1),
        fetch_rutas_zonales(limit=1),
    )
    nombres = ["estaciones_cable", "paraderos_sitp", "rutas_zonales"]
    return [
        {
            "fuente": nombre,
            "disponible": bool(records),
            "registros_muestra": len(records),
        }
        for nombre, records in zip(nombres, resultados)
    ]
