from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.fuente import FuenteDatos
from app.models.parada import Parada
from app.models.ruta import Ruta
from app.models.horario import Horario


class DatasetLoader:
    """Carga lógica de datos abiertos aplicada al modelo del sistema."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_default_sources(self) -> None:
        default_sources = [
            {
                "nombre": "gtfs_sitp",
                "tipo": "gtfs",
                "url": "https://datosabiertos.bogota.gov.co/",
                "descripcion": "Fuente GTFS del SITP / datos abiertos de Bogotá",
            },
            {
                "nombre": "estaciones_cable",
                "tipo": "ckan",
                "url": "https://datosabiertos.bogota.gov.co/dataset/estaciones-cable",
                "descripcion": "Estaciones de TransMiCable",
            },
            {
                "nombre": "paraderos_sitp",
                "tipo": "ckan",
                "url": "https://datosabiertos.bogota.gov.co/dataset/paraderos-zonales-del-sitp",
                "descripcion": "Paraderos del SITP",
            },
            {
                "nombre": "rutas_zonales",
                "tipo": "arcgis",
                "url": "https://datosabiertos.bogota.gov.co/dataset/servicios-rutas-troncales-y-zonales",
                "descripcion": "Geometrías y servicios de rutas zonales",
            },
        ]

        for item in default_sources:
            exists = self.db.query(FuenteDatos).filter(FuenteDatos.nombre == item["nombre"]).first()
            if not exists:
                self.db.add(FuenteDatos(**item))

        self.db.commit()

    def seed_sample_transport_data(self) -> None:
        if self.db.query(Ruta).first():
            return

        ruta_1 = Ruta(codigo="R1", nombre="Ruta Troncal 1", tipo="troncal", descripcion="Ruta de prueba", distancia_km=12.5)
        ruta_2 = Ruta(codigo="Z1", nombre="Ruta Zonal 1", tipo="zonal", descripcion="Ruta zonal", distancia_km=8.3)
        self.db.add_all([ruta_1, ruta_2])
        self.db.commit()
        self.db.refresh(ruta_1)
        self.db.refresh(ruta_2)

        self.db.add_all(
            [
                Parada(nombre="Vista Hermosa", codigo="VH-01", lat=4.5684, lng=-74.1502, zona="Ciudad Bolívar", tipo="sitp", activo=True),
                Parada(nombre="Estación Sur", codigo="ES-01", lat=4.5715, lng=-74.1480, zona="Ciudad Bolívar", tipo="transmilenio", activo=True),
                Parada(nombre="TransMiCable", codigo="TC-01", lat=4.5760, lng=-74.1460, zona="Ciudad Bolívar", tipo="cable", activo=True),
                Parada(nombre="Universidad Distrital", codigo="UD-01", lat=4.5799, lng=-74.1420, zona="Ciudad Bolívar", tipo="sitp", activo=True),
            ]
        )
        self.db.commit()

        self.db.add_all(
            [
                Horario(ruta_id=ruta_1.id, dia_semana="Lunes", hora="06:00", frecuencia_min=10),
                Horario(ruta_id=ruta_1.id, dia_semana="Lunes", hora="07:00", frecuencia_min=12),
                Horario(ruta_id=ruta_2.id, dia_semana="Lunes", hora="06:30", frecuencia_min=15),
            ]
        )
        self.db.commit()
