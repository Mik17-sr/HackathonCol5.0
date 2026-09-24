# Integración de Datos Abiertos de Movilidad - Proyecto "Muévete CB"

Este documento contiene la especificación y guía de integración backend (FastAPI) para las fuentes de datos públicas del portal de **Datos Abiertos de Bogotá** y **TransMilenio S.A.**, orientadas al cálculo de rutas, paraderos y estaciones en la localidad de Ciudad Bolívar.

---

## 1. Inventario de Fuentes de Datos (Datasets)

| Nombre del Dataset / Fuente | URL / Recurso Público | Uso en el Sistema "Muévete CB" |
| :--- | :--- | :--- |
| **Estaciones Cable** | `https://datosabiertos.bogota.gov.co/dataset/estaciones-cable` | Puntos de acceso, coordenadas y estaciones operativas de TransMiCable en Ciudad Bolívar. |
| **Servicios (Rutas Troncales y Zonales)** | `https://datosabiertos.bogota.gov.co/dataset/servicios-rutas-troncales-y-zonales` | Trazados, itinerarios y códigos de rutas zonales (SITP) y troncales que alimentan la zona. |
| **Registro Único / Red Urbana (RU)** | `https://datosabiertos.bogota.gov.co/dataset/ru` | Mapeo de la malla vial urbana y rutas zonales asociadas a la infraestructura vial. |
| **Flota Vinculada del SITP** | `https://datosabiertos.bogota.gov.co/dataset/flota-vinculada-del-sitp` | Información sobre la flota operativa disponible por operador / zona. |
| **Nuevas Zonas SITP** | `https://datosabiertos.bogota.gov.co/dataset/nuevas-zonas-sitp` | Delimitación geofísica de las zonas de cobertura (Zonificación SITP / Ciudad Bolívar). |
| **Paraderos Zonales del SITP** | `https://datosabiertos.bogota.gov.co/dataset/paraderos-zonales-del-sitp` | Ubicación geográfica (`GeoJSON`/`Lat,Lng`) y códigos de paraderos para trasbordos. |
| **Estaciones del Cable (Duplicado/Complemento)** | `https://datosabiertos.bogota.gov.co/dataset/estaciones-del-cable` | Capas complementarias de infraestructura del sistema cableado. |
| **Organización TransMilenio (Catálogo General)** | `https://datosabiertos.bogota.gov.co/organization/transmilenio?page=1` | Repositorio completo de datasets de TransMilenio (actualizaciones y nuevos feeds). |

---

## 2. Métodos de Consumo Técnico (CKAN API & Esri REST)

La plataforma de Datos Abiertos de Bogotá expone sus datos principalmente a través de la **API de CKAN** o servicios geográficos **ArcGIS REST Service**.

### A. API de CKAN (Datastore Search)
Para consultar datasets tabulares directamente mediante parámetros HTTP `GET`:

- **Endpoint Base:** `https://datosabiertos.bogota.gov.co/api/3/action/datastore_search`
- **Parámetros:**
  - `resource_id`: El identificador de 36 caracteres del recurso (p. ej. `9a3bb88a-e977-48cd-8e20-5ca481c19b1d`).
  - `limit`: Número de registros a traer (ejemplo: `100`).
  - `q`: Término de búsqueda (ejemplo: `"Ciudad Bolívar"`).

---

## 3. Módulo Integrador en FastAPI (`httpx`)

A continuación se presenta la estructura sugerida para incluir en tu backend `FastAPI` empleando peticiones asíncronas con `httpx`.

```python
import asyncio
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
import httpx

app = FastAPI(
    title="Muévete CB - Backend Integrador",
    version="1.0.0",
    description="API Gateway que consume y procesa fuentes de Datos Abiertos de Bogotá para Ciudad Bolívar"
)

# Catálogo de Resource IDs de CKAN (Reemplazar con los IDs exactos de los recursos del portal)
DATASETS_CONFIG = {
    "estaciones_cable": "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search?resource_id=ID_RECURSO_CABLE",
    "paraderos_sitp": "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search?resource_id=ID_RECURSO_PARADEROS",
    "rutas_zonales": "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search?resource_id=ID_RECURSO_RUTAS"
}

@app.get("/api/v1/movilidad/estaciones-cable")
async def obtener_estaciones_cable(
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Obtiene las estaciones del TransMiCable consumiendo la API de Datos Abiertos.
    """
    url = "https://datosabiertos.bogota.gov.co/api/3/action/datastore_search"
    params = {
        "resource_id": "9a3bb88a-e977-48cd-8e20-5ca481c19b1d", # ID de recurso de Estaciones Cable
        "limit": limit
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("result", {}).get("records", [])
            return {
                "status": "success",
                "count": len(records),
                "data": records
            }
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Error en servidor de Datos Abiertos.")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"No se pudo conectar con la fuente externa: {str(e)}")


@app.get("/api/v1/movilidad/consulta-multifuente")
async def consultar_datos_integrados(busqueda: str = "Ciudad Bolívar"):
    """
    Realiza llamadas asíncronas en paralelo para integrar rutas y paraderos al tiempo.
    """
    async with httpx.AsyncClient() as client:
        # Peticiones en paralelo con asyncio.gather
        tareas = [
            client.get("https://datosabiertos.bogota.gov.co/api/3/action/datastore_search", params={"q": busqueda, "limit": 10}),
            client.get("https://datosabiertos.bogota.gov.co/api/3/action/datastore_search", params={"q": "TransMiCable", "limit": 5})
        ]
        
        respuestas = await asyncio.gather(*tareas, return_exceptions=True)
        
        resultados = []
        for resp in respuestas:
            if isinstance(resp, httpx.Response) and resp.status_code == 200:
                resultados.append(resp.json().get("result", {}).get("records", []))
            else:
                resultados.append([])

        return {
            "busqueda": busqueda,
            "rutas_encontradas": resultados[0],
            "estaciones_cable": resultados[1]
        }
```

---

## 4. Recomendaciones para el Reto "Muévete CB"

1. **Estrategia de Caching:** Dado que los datos de infraestructura (estaciones y paraderos) no cambian cada minuto, implementa una capa de **Redis** o caché en memoria (`functools.lru_cache` / `async-lru`) con tiempo de expiración (TTL) de 24 horas para reducir la latencia de respuesta en la aplicación móvil/web.
2. **Normalización de Coordenadas:** Asegúrate de verificar si las coordenadas vienen en sistema WGS84 (`EPSG:4326` - Lat/Lng tradicional) o en MAGNA-SIRGAS para proyectarlas correctamente en los mapas interactivos de la interfaz.
3. **Cruce con Transporte Informal:** Crea un endpoint interno en FastAPI que combine los paraderos devueltos por la API pública con tu propia base de datos (p. ej. alimentadores veredales o colectivos comunitarios) mediante coincidencia geográfica por proximidad.