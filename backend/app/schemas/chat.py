from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Ubicacion(BaseModel):
    lat: float
    lng: float


class ContextoSolicitud(BaseModel):
    ubicacion_actual: Ubicacion
    hora_consulta: datetime
    destino: Ubicacion | None = None


class RecomendacionRequest(BaseModel):
    usuario_id: str = Field(..., description="Identificador del usuario")
    mensaje: str = Field(..., min_length=5, description="Mensaje natural del usuario")
    contexto: ContextoSolicitud


class RutaAlternativa(BaseModel):
    tipo: Literal["rapida", "confiable", "baja_caminata"]
    tiempo_estimado: int
    costo: float
    caminata: float
    transbordos: int
    espera: int
    confiabilidad: float
    segmentos: list[str] = Field(default_factory=list)


class RecomendacionResponse(BaseModel):
    usuario_id: str
    mensaje: str
    respuesta: str
    resumen: str
    alternativas: list[RutaAlternativa]
