import sys
sys.path.insert(0, ".")
from app.route_engine.graph import Graph
from app.route_engine.stop_graph import DerivedStop, StopNetwork
from app.route_engine.stop_router import StopRouter

def make_stop(sid, lat, lng, name, routes, vi=None):
    s = DerivedStop(id=sid, lat=lat, lng=lng, name=name, route_ids=routes)
    if vi:
        s.raw_vertex_index = vi
    return s

def add_bus(g, src, dst, rid, dist=1.0):
    dur = max(1, round(dist / 22 * 60))
    for a, b in ((src, dst), (dst, src)):
        g.add_connection(a, b, duration=dur, cost=2950, distance=dist, walking=0,
                         wait=5, transfers=0, reliability=0.9, accessibility=0.8,
                         status="normal", mode="sitp", route_id=rid)

stop_a = make_stop("SA", 4.5700, -74.1500, "A", {"R1"}, {"R1": 0})
stop_b = make_stop("SB", 4.5750, -74.1500, "B", {"R1", "R2"}, {"R1": 2, "R2": 0})
stop_c = make_stop("SC", 4.5800, -74.1500, "C", {"R2"}, {"R2": 2})
g = Graph()
add_bus(g, "SA", "SB", "R1", 0.9)
add_bus(g, "SB", "SC", "R2", 0.9)

net = StopNetwork(
    stops={"SA": stop_a, "SB": stop_b, "SC": stop_c},
    routes={
        "R1": {"id": "R1", "name": "R1", "mode": "sitp",
               "paths": [[(4.5700, -74.1500), (4.5725, -74.1500), (4.5750, -74.1500)]],
               "raw": {"cod_linea": "R1"}},
        "R2": {"id": "R2", "name": "R2", "mode": "sitp",
               "paths": [[(4.5750, -74.1500), (4.5775, -74.1500), (4.5800, -74.1500)]],
               "raw": {"cod_linea": "R2"}},
    },
    graph=g,
)
router = StopRouter(net)
res = router.find_route(4.5682, -74.1500, 4.5818, -74.1500)
r = res[0]
print("found:", r.found)
print("path:", r.path)
print("segments:")
for s in r.segments:
    print(f"  {s.type}  route={s.route_id}  dist={s.distance_km}")
print()
# Debug Dijkstra directo
from app.route_engine.dijkstra import dijkstra_shortest_path
try:
    dijk = dijkstra_shortest_path(g, "SA", "SC", max_services=2)
    print("Dijkstra path:", dijk["path"])
    print("legs:", [(l["modo"], l["route_id"]) for l in dijk["legs"]])
except Exception as e:
    print("Dijkstra error:", e)
