"""Prueba real del flujo completo: Vista Hermosa -> Arborizadora Alta"""
import asyncio, sys, time, logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(message)s")

async def main():
    from app.services.graph_service import GraphService
    from app.route_engine.stop_router import route_result_to_legacy

    # Vista Hermosa → Arborizadora Alta
    orig_lat, orig_lng = 4.5684, -74.1502
    dest_lat, dest_lng = 4.5770, -74.1560

    print("=" * 60)
    print("RUTA: Vista Hermosa -> Arborizadora Alta")
    print("=" * 60)

    t0 = time.perf_counter()
    svc = GraphService()
    router = await svc.get_stop_router(limit=100)
    net = router.net

    print(f"\n[STOP_GRAPH] stops={len(net.stops)}  routes={len(net.routes)}")
    print(f"[STOP_GRAPH] edges={sum(len(v) for v in net.graph.adjacency.values())}")
    print(f"[STOP_GRAPH] build_time={1000*(time.perf_counter()-t0):.0f} ms\n")

    results = router.find_route(orig_lat, orig_lng, dest_lat, dest_lng)
    r = results[0]

    if not r.found:
        print(f"[ERROR] {r.error}")
        return

    print(f"[RESULT]")
    print(f"  found:       {r.found}")
    print(f"  walking:     {r.walking_distance_km:.2f} km")
    print(f"  bus:         {r.bus_distance_km:.2f} km")
    print(f"  total:       {r.total_distance_km:.2f} km")
    print(f"  duration:    {r.total_duration_min} min")
    print(f"  transfers:   {r.transfers}")
    print(f"  coordinates: {len(r.coordinates)} puntos para Leaflet")

    print(f"\n[SEGMENTS]")
    for seg in r.segments:
        if seg.type == "WALK":
            print(f"  WALK  {seg.from_label} -> {seg.to_label}  {seg.distance_km:.2f} km  {seg.duration_min} min")
        else:
            fr = seg.from_stop.name if seg.from_stop else "?"
            to = seg.to_stop.name if seg.to_stop else "?"
            print(f"  BUS [{seg.route_id}]  {fr} -> {to}  {seg.distance_km:.2f} km  {seg.duration_min} min")

    print(f"\n[ALTERNATIVAS] {len(results)}")
    for i, alt in enumerate(results):
        bus_ids = [s.route_id for s in alt.segments if s.type == "BUS"]
        print(f"  [{i}] {'->'.join(bus_ids) or 'WALK'}  {alt.total_duration_min} min  {alt.walking_distance_km:.2f}km caminata  {alt.transfers} transbordos")

    print(f"\n[TOTAL] {1000*(time.perf_counter()-t0):.0f} ms")

asyncio.run(main())
