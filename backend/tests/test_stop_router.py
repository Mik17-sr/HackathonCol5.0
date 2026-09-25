"""
test_stop_router.py — Pruebas del motor de rutas basado en paradas SITP.

Diseño de coordenadas
---------------------
- DIRECT_WALK_KM = 1.0  →  distancia entre origen y destino debe ser > 1.0 km
  para que el router busque bus en vez de devolver caminata directa.
- MAX_WALK_TO_STOP_KM = 0.8  →  parada debe estar a ≤ 0.8 km del punto.
- Cada caso usa max_walk_km explícito para controlar exactamente qué paradas
  son candidatas.

Casos:
  1. Bus directo
  2. Un transbordo
  3. Sin ruta (destino sin paradas cercanas)
  4. Origen demasiado lejos de cualquier parada
  5. Caminata directa (distancia ≤ 1.0 km)
  6. Rechazo de 3 buses
  7. Sin transbordo arbitrario (dos redes desconectadas)
"""
from __future__ import annotations

from app.route_engine.graph import Graph
from app.route_engine.stop_graph import DerivedStop, StopNetwork
from app.route_engine.stop_router import StopRouter


# ── Helpers de construcción ────────────────────────────────────────────────

def _stop(sid, lat, lng, name, route_ids, vi=None):
    s = DerivedStop(id=sid, lat=lat, lng=lng, name=name, route_ids=set(route_ids))
    if vi:
        s.raw_vertex_index = vi
    return s


def _bus(graph, a, b, rid, km=1.0):
    dur = max(1, round(km / 22 * 60))
    for src, dst in ((a, b), (b, a)):
        graph.add_connection(
            src, dst,
            duration=dur, cost=2950, distance=km, walking=0,
            wait=5, transfers=0, reliability=0.9, accessibility=0.8,
            status="normal", mode="sitp", route_id=rid,
        )


def _net(stops, routes, edges):
    """Construye StopNetwork mínima desde listas de paradas y aristas."""
    graph = Graph()
    for s in stops:
        graph.add_node(s.id)
    for a, b, rid, km in edges:
        _bus(graph, a, b, rid, km)
    stop_dict = {s.id: s for s in stops}
    route_dict = {
        rid: {"id": rid, "name": rid, "mode": "sitp", "paths": [], "raw": {}}
        for rid in routes
    }
    return StopNetwork(stops=stop_dict, routes=route_dict, graph=graph)


# ── Caso 1: Bus directo ────────────────────────────────────────────────────

def test_caso1_bus_directo():
    """ORIGEN → SA →[R1]→ SB → DESTINO  (sin transbordo)"""
    # SA en 4.5700, SB en 4.5800  →  distancia entre paradas ≈ 1.11 km
    sa = _stop("SA", 4.5700, -74.1500, "Parada A", ["R1"], {"R1": 0})
    sb = _stop("SB", 4.5800, -74.1500, "Parada B", ["R1"], {"R1": 1})

    net = _net([sa, sb], ["R1"], [("SA", "SB", "R1", 1.1)])
    net.routes["R1"]["paths"] = [[(4.5700, -74.1500), (4.5750, -74.1500), (4.5800, -74.1500)]]

    router = StopRouter(net)
    # Origen: 4.5680 (200 m al sur de SA, dentro de max_walk_km=0.3)
    # Destino: 4.5820 (200 m al norte de SB, dentro de max_walk_km=0.3)
    # Distancia total: ≈ 1.55 km > 1.0 → busca bus
    results = router.find_route(4.5680, -74.1500, 4.5820, -74.1500, max_walk_km=0.3)

    r = results[0]
    assert r.found is True
    bus_segs = [s for s in r.segments if s.type == "BUS"]
    assert len(bus_segs) == 1
    assert bus_segs[0].route_id == "R1"
    assert r.transfers == 0


# ── Caso 2: Un transbordo ──────────────────────────────────────────────────

def test_caso2_un_transbordo():
    """ORIGEN → SA →[R1]→ SB →[R2]→ SC → DESTINO  (1 transbordo en SB)"""
    sa = _stop("SA", 4.5700, -74.1500, "A", ["R1"], {"R1": 0})
    sb = _stop("SB", 4.5760, -74.1500, "B", ["R1", "R2"], {"R1": 1, "R2": 0})
    sc = _stop("SC", 4.5820, -74.1500, "C", ["R2"], {"R2": 1})

    net = _net([sa, sb, sc], ["R1", "R2"], [("SA", "SB", "R1", 0.7), ("SB", "SC", "R2", 0.7)])
    net.routes["R1"]["paths"] = [[(4.5700, -74.1500), (4.5760, -74.1500)]]
    net.routes["R2"]["paths"] = [[(4.5760, -74.1500), (4.5820, -74.1500)]]

    router = StopRouter(net)
    # max_walk_km=0.25: origen alcanza SA (200 m), destino alcanza SC (200 m)
    # SB queda a 0.72 km del destino → fuera de max_walk_km → no candidato destino
    # El único par válido es (SA, SC) → fuerza transbordo en SB
    results = router.find_route(4.5682, -74.1500, 4.5838, -74.1500, max_walk_km=0.25)

    r = results[0]
    assert r.found is True
    bus_segs = [s for s in r.segments if s.type == "BUS"]
    assert len(bus_segs) == 2
    assert bus_segs[0].route_id == "R1"
    assert bus_segs[1].route_id == "R2"
    assert r.transfers == 1


# ── Caso 3: Sin ruta disponible ───────────────────────────────────────────

def test_caso3_sin_ruta_disponible():
    """Destino a > 0.8 km de cualquier parada → found=False."""
    sa = _stop("SA", 4.5700, -74.1500, "A", ["R1"], {"R1": 0})
    sb = _stop("SB", 4.5740, -74.1500, "B", ["R1"], {"R1": 1})
    net = _net([sa, sb], ["R1"], [("SA", "SB", "R1", 0.5)])

    router = StopRouter(net)
    # Destino en Chapinero norte: muy lejos de cualquier parada de Ciudad Bolívar
    results = router.find_route(4.5700, -74.1500, 4.6500, -74.0500)

    r = results[0]
    assert r.found is False
    assert r.error and len(r.error) > 0


# ── Caso 4: Origen demasiado lejos ────────────────────────────────────────

def test_caso4_demasiado_lejos_de_parada():
    """Origen a > max_walk_km de todas las paradas → found=False."""
    sa = _stop("SA", 4.5700, -74.1500, "A", ["R1"], {"R1": 0})
    net = _net([sa], ["R1"], [])

    router = StopRouter(net)
    # Origen en 4.5300: ~4.4 km de SA → muy lejos de max_walk_km=0.8
    results = router.find_route(4.5300, -74.1500, 4.5700, -74.1500, max_walk_km=0.8)

    r = results[0]
    assert r.found is False
    assert "paradas SITP" in (r.error or "")


# ── Caso 5: Caminata directa ──────────────────────────────────────────────

def test_caso5_caminata_directa():
    """Distancia origen‑destino ≤ 1.0 km → solo WALK."""
    net = StopNetwork()  # sin paradas

    router = StopRouter(net)
    # 400 m en vertical (< 1.0 km) → activa caminata directa
    results = router.find_route(4.5700, -74.1500, 4.5736, -74.1500)

    r = results[0]
    assert r.found is True
    assert all(s.type == "WALK" for s in r.segments)
    assert r.bus_distance_km == 0.0
    assert r.transfers == 0


# ── Caso 6: Rechazo de 3 buses ────────────────────────────────────────────

def test_caso6_rechaza_tres_buses():
    """
    Red: SA-[R1]->SB-[R2]->SC-[R3]->SD
    El único camino SA→SD requiere 3 servicios.
    max_services=2 → Dijkstra no encuentra ruta → found=False.
    """
    sa = _stop("SA", 4.5700, -74.1500, "A", ["R1"], {"R1": 0})
    sb = _stop("SB", 4.5733, -74.1500, "B", ["R1", "R2"], {"R1": 1, "R2": 0})
    sc = _stop("SC", 4.5766, -74.1500, "C", ["R2", "R3"], {"R2": 1, "R3": 0})
    sd = _stop("SD", 4.5800, -74.1500, "D", ["R3"], {"R3": 1})

    net = _net(
        [sa, sb, sc, sd], ["R1", "R2", "R3"],
        [("SA", "SB", "R1", 0.4), ("SB", "SC", "R2", 0.4), ("SC", "SD", "R3", 0.4)],
    )

    router = StopRouter(net)
    # Distancia SA→SD ≈ 1.11 km > 1.0 → no caminata directa.
    # max_walk_km=0.05: origen solo alcanza SA, destino solo alcanza SD.
    # Dijkstra necesita R1+R2+R3 → descartado.
    results = router.find_route(4.5699, -74.1500, 4.5801, -74.1500, max_walk_km=0.05)

    assert results[0].found is False


# ── Caso 7: Sin transbordo arbitrario ─────────────────────────────────────

def test_caso7_sin_transbordo_arbitrario():
    """
    Red izquierda:  SA-[R1]->SB   (lng ≈ -74.1520)
    Red derecha:    SC-[R2]->SD   (lng ≈ -74.1450)
    Las dos redes no tienen ninguna arista en común.
    El origen solo alcanza SA. El destino solo alcanza SD.
    No debe inventarse un transbordo SB→SC.
    """
    sa = _stop("SA", 4.5700, -74.1520, "A", ["R1"], {"R1": 0})
    sb = _stop("SB", 4.5760, -74.1520, "B", ["R1"], {"R1": 1})
    sc = _stop("SC", 4.5700, -74.1450, "C", ["R2"], {"R2": 0})
    sd = _stop("SD", 4.5760, -74.1450, "D", ["R2"], {"R2": 1})

    # Solo aristas dentro de cada red; ninguna entre las dos
    net = _net(
        [sa, sb, sc, sd], ["R1", "R2"],
        [("SA", "SB", "R1", 0.7), ("SC", "SD", "R2", 0.7)],
    )

    router = StopRouter(net)
    # Origen cerca de SA (max_walk_km=0.15 → alcanza SA a 0.11 km, no SC a 0.77 km)
    # Destino cerca de SD (max_walk_km=0.15 → alcanza SD a 0.11 km, no SB a 0.77 km)
    # Distancia origen→destino ≈ 0.78 km < 1.0 → activaría caminata.
    # Ponemos origen más al sur para superar 1.0 km:
    # Origen 4.5600, destino 4.5770  → ~1.89 km > 1.0
    # Ajustamos longitudes para que max_walk_km=0.15 solo alcance cada red propia.
    sa2 = _stop("SA", 4.5650, -74.1520, "A", ["R1"], {"R1": 0})
    sb2 = _stop("SB", 4.5710, -74.1520, "B", ["R1"], {"R1": 1})
    sc2 = _stop("SC", 4.5770, -74.1450, "C", ["R2"], {"R2": 0})
    sd2 = _stop("SD", 4.5830, -74.1450, "D", ["R2"], {"R2": 1})

    net2 = _net(
        [sa2, sb2, sc2, sd2], ["R1", "R2"],
        [("SA", "SB", "R1", 0.7), ("SC", "SD", "R2", 0.7)],
    )

    router2 = StopRouter(net2)
    # Origen: 4.5638,-74.1520  → SA a 0.13 km ✓, SC a >0.8 km ✗
    # Destino: 4.5842,-74.1450 → SD a 0.13 km ✓, SB a >0.8 km ✗
    # Distancia origen→destino ≈ 2.3 km > 1.0 → no caminata directa
    results = router2.find_route(4.5638, -74.1520, 4.5842, -74.1450, max_walk_km=0.15)

    r = results[0]
    assert r.found is False
    # Refuerzo: si encontró algo (no debería), no debe tener R1 y R2 juntos
    for rr in results:
        if rr.found:
            rids = [s.route_id for s in rr.segments if s.type == "BUS"]
            assert not ("R1" in rids and "R2" in rids), (
                "Transbordo arbitrario generado entre redes sin conexión"
            )
