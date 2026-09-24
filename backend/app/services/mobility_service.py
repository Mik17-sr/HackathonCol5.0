from __future__ import annotations

from app.schemas.movilidad import EstadoMovilidad


class MobilityService:
    def get_status(self, zona: str = "Ciudad Bolívar") -> EstadoMovilidad:
        return EstadoMovilidad(
            estado="normal",
            zona=zona,
            alerta=None,
            descripcion="Sistema operativo. Sin incidentes reportados.",
        )
