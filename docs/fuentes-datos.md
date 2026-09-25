# Fuente única de movilidad

La aplicación consume exclusivamente la capa 15 del FeatureServer de TransMilenio, filtrada a las rutas de Ciudad Bolívar con `loc_orig = 19 OR loc_dest = 19`:

`https://gis.transmilenio.gov.co/arcgis/rest/services/ConsultaSubgerenciaPlanificacionSITP/Consulta_Planificacion_SITP/FeatureServer/15/query`

La consulta se realiza con `where=1=1`, `outFields=*`, `outSR=4326` y `f=geojson`, por lo que incluye todas las rutas disponibles. Sus campos principales son `cod_ruta`, `nom_ruta`, `long_ruta`, `hor_habil`, `hor_sab`, `hor_fest` y la geometría de cada ruta.

El backend normaliza `LineString` y `MultiLineString` a `paths` en formato `[lat, lng]` y conserva todos los atributos originales en `atributos`. Los puntos mostrados en `/api/v1/paradas` se derivan únicamente de todos los vértices de esas geometrías. Para que el cálculo geográfico sea viable, el motor usa una muestra de hasta 5.000 vértices, pero las 693 rutas y sus geometrías completas permanecen disponibles en los endpoints de datos.

El filtro devuelve aproximadamente 55 rutas y evita descargar la red completa de Bogotá. Estos puntos son referencias geométricas de ruta, no paraderos oficiales: el dataset no incluye una capa de paraderos con código, nombre o ubicación independiente. La capa tampoco contiene estaciones; por eso `/api/v1/estaciones` devuelve una colección vacía y no mezcla otra fuente.

No se deben agregar consultas a CKAN, GTFS, Nominatim u otros datasets para completar rutas, paraderos, horarios o estaciones. Las búsquedas de direcciones del frontend son geocodificación de entrada del usuario y no una fuente de transporte.
