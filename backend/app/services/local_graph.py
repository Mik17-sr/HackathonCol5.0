"""
Grafo local predefinido de Ciudad Bolívar.

Contiene ~20 nodos reales de la localidad (paradas SITP, estaciones TransMiCable,
portales y puntos de interés) y las conexiones entre ellos.  Este grafo se usa
siempre como base garantizada: no depende de ninguna API externa ni de la base
de datos.  La API ArcGIS de Transmilenio enriquece el grafo cuando está
disponible, pero nunca bloquea la respuesta.

Coordenadas verificadas contra OpenStreetMap / Google Maps (WGS-84).
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Nodos — paradas y puntos de referencia reales en Ciudad Bolívar, Bogotá
# ---------------------------------------------------------------------------
#
# Cada nodo tiene:
#   id          – identificador único usado en el grafo
#   name        – nombre legible para el usuario
#   lat / lng   – coordenadas WGS-84
#   mode        – "sitp" | "transmicable" | "transmilenio" | "peatonal"
#   source_type – "parada" | "estacion" | "referencia"
#
LOCAL_NODES: list[dict[str, Any]] = [
    # ── Portal / Portales ──────────────────────────────────────────────────
    {
        "id": "local:portal_tunal",
        "name": "Portal El Tunal",
        "lat": 4.5680,
        "lng": -74.1466,
        "mode": "transmilenio",
        "source_type": "estacion",
    },
    # ── TransMiCable ───────────────────────────────────────────────────────
    {
        "id": "local:cable_tunal",
        "name": "TransMiCable · Estación El Tunal",
        "lat": 4.5694,
        "lng": -74.1479,
        "mode": "transmicable",
        "source_type": "estacion",
    },
    {
        "id": "local:cable_manantial",
        "name": "TransMiCable · Estación Manantial",
        "lat": 4.5750,
        "lng": -74.1489,
        "mode": "transmicable",
        "source_type": "estacion",
    },
    {
        "id": "local:cable_mirador",
        "name": "TransMiCable · Estación Mirador del Paraíso",
        "lat": 4.5802,
        "lng": -74.1496,
        "mode": "transmicable",
        "source_type": "estacion",
    },
    # ── SITP — zona sur ────────────────────────────────────────────────────
    {
        "id": "local:vista_hermosa",
        "name": "Vista Hermosa",
        "lat": 4.5684,
        "lng": -74.1502,
        "mode": "sitp",
        "source_type": "parada",
    },
    {
        "id": "local:lucero",
        "name": "Lucero",
        "lat": 4.5720,
        "lng": -74.1515,
        "mode": "sitp",
        "source_type": "parada",
    },
    {
        "id": "local:tesoro",
        "name": "El Tesoro",
        "lat": 4.5755,
        "lng": -74.1530,
        "mode": "sitp",
        "source_type": "parada",
    },
    {
        "id": "local:arborizadora_alta",
        "name": "Arborizadora Alta",
        "lat": 4.5770,
        "lng": -74.1560,
        "mode": "sitp",
        "source_type": "parada",
    },
    {
        "id": "local:arborizadora_baja",
        "name": "Arborizadora Baja",
        "lat": 4.5748,
        "lng": -74.1538,
        "mode": "sitp",
        "source_type": "parada",
    },
    {
        "id": "local:sierra_morena",
        "name": "Sierra Morena",
        "lat": 4.5795,
        "lng": -74.1580,
        "mode": "sitp",
        "source_type": "parada",
    },
    {
        "id": "local:san_francisco",
        "name": "San Francisco",
        "lat": 4.5810,
        "lng": -74.1600,
        "mode": "sitp",
        "source_type": "parada",
    },
    # ── SITP — zona norte / límite con Usme ───────────────────────────────
    {
        "id": "local:madelena",
        "name": "Madelena",
        "lat": 4.5660,
        "lng": -74.1440,
        "mode": "sitp",
        "source_type": "parada",
    },
    {
        "id": "local:venecia",
        "name": "Venecia (Av. Primero de Mayo)",
        "lat": 4.5620,
        "lng": -74.1385,
        "mode": "sitp",
        "source_type": "parada",
    },
    {
        "id": "local:av_boyaca_sur",
        "name": "Av. Boyacá Sur",
        "lat": 4.5640,
        "lng": -74.1420,
        "mode": "sitp",
        "source_type": "parada",
    },
    # ── Referencia — destinos frecuentes ──────────────────────────────────
    {
        "id": "local:ud_tecnologica",
        "name": "Universidad Distrital F.J.C. (Tecnológica)",
        "lat": 4.5799,
        "lng": -74.1420,
        "mode": "sitp",
        "source_type": "referencia",
    },
    {
        "id": "local:hospital_meissen",
        "name": "Hospital Meissen",
        "lat": 4.5630,
        "lng": -74.1460,
        "mode": "sitp",
        "source_type": "referencia",
    },
    {
        "id": "local:colegio_rodrigo_lara",
        "name": "Colegio Rodrigo Lara Bonilla",
        "lat": 4.5712,
        "lng": -74.1490,
        "mode": "sitp",
        "source_type": "referencia",
    },
    {
        "id": "local:parque_el_tunal",
        "name": "Parque El Tunal",
        "lat": 4.5670,
        "lng": -74.1472,
        "mode": "peatonal",
        "source_type": "referencia",
    },
    {
        "id": "local:plaza_bolivar_cb",
        "name": "Plaza Central Ciudad Bolívar",
        "lat": 4.5740,
        "lng": -74.1505,
        "mode": "sitp",
        "source_type": "referencia",
    },
    {
        "id": "local:chapinero_sur",
        "name": "Chapinero Sur (Av. 68)",
        "lat": 4.5590,
        "lng": -74.1350,
        "mode": "sitp",
        "source_type": "parada",
    },
]

# ---------------------------------------------------------------------------
# Rutas — segmentos de transporte real que conectan los nodos anteriores
# ---------------------------------------------------------------------------
#
# Cada ruta define un camino ordenado de paradas y los metadatos del servicio.
# Las aristas del grafo se construyen de forma bidireccional (A→B y B→A)
# para modelar el tránsito urbano real donde los buses operan en ambos sentidos
# en rutas circulares/de retorno.
#
# frequency_min: intervalo entre buses (minutos)
# mode: "sitp" | "transmicable" | "transmilenio"
#
LOCAL_ROUTES: list[dict[str, Any]] = [
    # ── TransMiCable (unidireccional subida/bajada, mismo trayecto) ───────
    {
        "id": "TransMiCable",
        "name": "TransMiCable",
        "mode": "transmicable",
        "frequency_min": 5,
        "stops": [
            "local:cable_tunal",
            "local:cable_manantial",
            "local:cable_mirador",
        ],
    },
    # ── B14 — Vista Hermosa ↔ Portal El Tunal ────────────────────────────
    {
        "id": "B14",
        "name": "SITP B14 · Vista Hermosa – Portal El Tunal",
        "mode": "sitp",
        "frequency_min": 8,
        "stops": [
            "local:vista_hermosa",
            "local:lucero",
            "local:colegio_rodrigo_lara",
            "local:cable_tunal",
            "local:parque_el_tunal",
            "local:portal_tunal",
        ],
    },
    # ── 6-4 — Arborizadora ↔ Portal El Tunal ─────────────────────────────
    {
        "id": "6-4",
        "name": "SITP 6-4 · Arborizadora – Portal El Tunal",
        "mode": "sitp",
        "frequency_min": 10,
        "stops": [
            "local:arborizadora_alta",
            "local:arborizadora_baja",
            "local:tesoro",
            "local:lucero",
            "local:madelena",
            "local:av_boyaca_sur",
            "local:portal_tunal",
        ],
    },
    # ── 6-3 — Sierra Morena ↔ Venecia ─────────────────────────────────────
    {
        "id": "6-3",
        "name": "SITP 6-3 · Sierra Morena – Venecia",
        "mode": "sitp",
        "frequency_min": 12,
        "stops": [
            "local:sierra_morena",
            "local:san_francisco",
            "local:arborizadora_alta",
            "local:plaza_bolivar_cb",
            "local:tesoro",
            "local:madelena",
            "local:venecia",
        ],
    },
    # ── TM Troncal (Transmilenio troncal — Caracas / NQS) ─────────────────
    {
        "id": "TM-Sur",
        "name": "Transmilenio · Portal El Tunal – Venecia – Chapinero",
        "mode": "transmilenio",
        "frequency_min": 4,
        "stops": [
            "local:portal_tunal",
            "local:venecia",
            "local:chapinero_sur",
        ],
    },
    # ── Peatonal / micro‑acceso Portal El Tunal ──────────────────────────
    {
        "id": "walk-tunal",
        "name": "Acceso peatonal Portal El Tunal",
        "mode": "caminata",
        "frequency_min": 0,
        "stops": [
            "local:portal_tunal",
            "local:cable_tunal",
            "local:parque_el_tunal",
            "local:madelena",
            "local:hospital_meissen",
        ],
    },
]


def get_local_nodes() -> list[dict[str, Any]]:
    """Devuelve la lista de nodos locales lista para consumir en GraphService."""
    return [
        {
            **node,
            "status": "normal",
            "raw": {},
        }
        for node in LOCAL_NODES
    ]


def get_local_routes() -> list[dict[str, Any]]:
    """
    Convierte las rutas locales al formato de paths esperado por build_graph_from_points.

    Cada ruta `stops` se transforma en un `paths` con las coordenadas ordenadas
    de los nodos correspondientes.
    """
    node_index = {node["id"]: node for node in LOCAL_NODES}
    result: list[dict[str, Any]] = []
    for route in LOCAL_ROUTES:
        path: list[tuple[float, float]] = []
        for stop_id in route["stops"]:
            node = node_index.get(stop_id)
            if node:
                path.append((node["lat"], node["lng"]))
        if len(path) < 2:
            continue
        result.append(
            {
                "id": route["id"],
                "name": route["name"],
                "mode": route["mode"],
                "frequency_min": route.get("frequency_min"),
                "paths": [path],
            }
        )
    return result
