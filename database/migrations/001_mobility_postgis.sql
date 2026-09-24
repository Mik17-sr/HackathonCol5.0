CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS puntos_movilidad (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(150) NOT NULL UNIQUE,
    nombre VARCHAR(250) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    modo VARCHAR(50) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    estado VARCHAR(50) NOT NULL DEFAULT 'normal',
    atributos JSONB,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    geom geometry(Point, 4326)
);

CREATE TABLE IF NOT EXISTS rutas_movilidad (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(150) NOT NULL UNIQUE,
    nombre VARCHAR(250) NOT NULL,
    modo VARCHAR(50) NOT NULL,
    frecuencia_min INTEGER,
    hora_inicio VARCHAR(10),
    hora_fin VARCHAR(10),
    geometria_geojson TEXT NOT NULL,
    atributos JSONB,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    geom geometry(MultiLineString, 4326)
);

ALTER TABLE rutas_movilidad ADD COLUMN IF NOT EXISTS frecuencia_min INTEGER;
ALTER TABLE rutas_movilidad ADD COLUMN IF NOT EXISTS hora_inicio VARCHAR(10);
ALTER TABLE rutas_movilidad ADD COLUMN IF NOT EXISTS hora_fin VARCHAR(10);

UPDATE puntos_movilidad
SET geom = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
WHERE geom IS NULL;

UPDATE rutas_movilidad
SET geom = ST_SetSRID(ST_GeomFromGeoJSON(geometria_geojson), 4326)
WHERE geom IS NULL;

CREATE INDEX IF NOT EXISTS ix_puntos_movilidad_geom
    ON puntos_movilidad USING GIST (geom);
CREATE INDEX IF NOT EXISTS ix_rutas_movilidad_geom
    ON rutas_movilidad USING GIST (geom);
