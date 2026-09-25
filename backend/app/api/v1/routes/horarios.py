from fastapi import APIRouter
from app.ingestion.normalizar_datos import normalize_route_records
from app.services.open_data_service import fetch_rutas_zonales

router = APIRouter(prefix="/api/v1", tags=["horarios"])


@router.get("/horarios")
async def listar_horarios() -> list[dict[str, object]]:
    routes = normalize_route_records(await fetch_rutas_zonales(limit=None))
    horarios: list[dict[str, object]] = []
    for route in routes:
        for tipo, hora in route["schedule"].items():
            horarios.append(
                {
                    "id": f"{route['id']}:{tipo}",
                    "ruta_id": route["id"],
                    "dia_semana": tipo,
                    "hora": hora,
                    "frecuencia_min": route.get("frequency_min"),
                    "atributos": route["raw"],
                }
            )
    return horarios
