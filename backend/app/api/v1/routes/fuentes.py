from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.repositories.fuente_repository import FuenteRepository
from app.services.open_data_service import SITP_ROUTES_URL, fetch_rutas_zonales

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
    records = await fetch_rutas_zonales(limit=1)
    return [{
        "fuente": "rutas_sitp_arcgis_featureserver_15",
        "url": SITP_ROUTES_URL,
        "disponible": bool(records),
        "registros_muestra": len(records),
    }]
