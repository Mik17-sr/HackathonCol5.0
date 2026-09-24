from __future__ import annotations

import json
from typing import Any

from sqlalchemy import inspect, select, update
from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.dato_movilidad import PuntoMovilidad, RutaMovilidad


def persist_open_data(
    points: list[dict[str, Any]],
    routes: list[dict[str, Any]],
) -> None:
    with SessionLocal() as db:
        _ensure_sqlite_columns(db)
        if points:
            point_types = {str(point["source_type"]) for point in points}
            db.execute(
                update(PuntoMovilidad)
                .where(PuntoMovilidad.tipo.in_(point_types))
                .values(activo=False)
            )
        if routes:
            db.execute(update(RutaMovilidad).values(activo=False))

        for point in points:
            existing = db.scalar(
                select(PuntoMovilidad).where(PuntoMovilidad.external_id == str(point["id"]))
            )
            if existing is None:
                existing = PuntoMovilidad(external_id=str(point["id"]))
                db.add(existing)
            existing.nombre = str(point["name"])
            existing.tipo = str(point["source_type"])
            existing.modo = str(point["mode"])
            existing.lat = float(point["lat"])
            existing.lng = float(point["lng"])
            existing.estado = str(point.get("status", "normal"))
            existing.atributos = point.get("raw")
            existing.activo = True

        for route in routes:
            existing = db.scalar(
                select(RutaMovilidad).where(RutaMovilidad.external_id == str(route["id"]))
            )
            if existing is None:
                existing = RutaMovilidad(external_id=str(route["id"]))
                db.add(existing)
            geometry = {
                "type": "MultiLineString",
                "coordinates": [
                    [[lng, lat] for lat, lng in path]
                    for path in route["paths"]
                ],
            }
            existing.nombre = str(route["name"])
            existing.modo = str(route.get("mode", "sitp"))
            existing.frecuencia_min = route.get("frequency_min")
            existing.hora_inicio = route.get("start_time")
            existing.hora_fin = route.get("end_time")
            existing.geometria_geojson = json.dumps(geometry)
            existing.atributos = route.get("raw")
            existing.activo = True

        db.commit()
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            _sync_postgis_columns(db)


def _sync_postgis_columns(db: Any) -> None:
    """Materialize spatial indexes when the configured database is PostGIS."""
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        db.execute(text(
            "ALTER TABLE puntos_movilidad "
            "ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326)"
        ))
        db.execute(text(
            "ALTER TABLE rutas_movilidad "
            "ADD COLUMN IF NOT EXISTS geom geometry(MultiLineString, 4326)"
        ))
        db.execute(text(
            "UPDATE puntos_movilidad SET geom = ST_SetSRID(ST_MakePoint(lng, lat), 4326)"
        ))
        db.execute(text(
            "UPDATE rutas_movilidad SET geom = ST_SetSRID(ST_GeomFromGeoJSON(geometria_geojson), 4326)"
        ))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_puntos_movilidad_geom "
            "ON puntos_movilidad USING GIST (geom)"
        ))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_rutas_movilidad_geom "
            "ON rutas_movilidad USING GIST (geom)"
        ))
        db.commit()
    except Exception:
        db.rollback()


def _ensure_sqlite_columns(db: Any) -> None:
    if db.bind is None or db.bind.dialect.name != "sqlite":
        return
    columns = {column["name"] for column in inspect(db.bind).get_columns("rutas_movilidad")}
    additions = {
        "frecuencia_min": "INTEGER",
        "hora_inicio": "VARCHAR(10)",
        "hora_fin": "VARCHAR(10)",
    }
    for name, sql_type in additions.items():
        if name not in columns:
            db.execute(text(f"ALTER TABLE rutas_movilidad ADD COLUMN {name} {sql_type}"))
    db.commit()
