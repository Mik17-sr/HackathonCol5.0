from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.estaciones import router as estaciones_router
from app.api.v1.routes.fuentes import router as fuentes_router
from app.api.v1.routes.horarios import router as horarios_router
from app.api.v1.routes.movilidad import router as movilidad_router
from app.api.v1.routes.paradas import router as paradas_router
from app.api.v1.routes.rutas import router as rutas_router
from app.core.database import Base, SessionLocal, engine
from app.models import *  # noqa: F401,F403
from app.services.dataset_loader import DatasetLoader

app = FastAPI(title="Muévete CB API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    loader = DatasetLoader(db)
    loader.ensure_default_sources()

app.include_router(chat_router)
app.include_router(rutas_router)
app.include_router(horarios_router)
app.include_router(fuentes_router)
app.include_router(paradas_router)
app.include_router(estaciones_router)
app.include_router(movilidad_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
