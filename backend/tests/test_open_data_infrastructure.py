import asyncio

from app.ingestion.normalizar_datos import normalize_point_records, normalize_route_records, simplify_route_records
from app.services.open_data_cache import OpenDataCache


def test_projected_point_is_transformed_to_wgs84():
    records = [{"objectid": 1, "geometry": {"x": 992241.5438, "y": 995531.4742}}]

    normalized = normalize_point_records(records, source_type="estacion")

    assert 4.5 < normalized[0]["lat"] < 4.7
    assert -74.3 < normalized[0]["lng"] < -74.0


def test_projected_route_vertices_are_transformed_to_wgs84():
    records = [
        {
            "objectid": 2,
            "servicio": "Z2",
            "geometry": {"paths": [[[992241.5438, 995531.4742], [992500, 995800]]] },
        }
    ]

    normalized = normalize_route_records(records)

    assert len(normalized) == 1
    assert 4.5 < normalized[0]["paths"][0][0][0] < 4.7


def test_open_data_cache_loads_each_key_once():
    async def scenario() -> tuple[int, list[dict[str, int]]]:
        cache = OpenDataCache(ttl_seconds=60)
        calls = 0

        async def loader() -> list[dict[str, int]]:
            nonlocal calls
            calls += 1
            return [{"value": 1}]

        first = await cache.get_or_set("dataset", loader)
        second = await cache.get_or_set("dataset", loader)
        return calls, first + second

    calls, values = asyncio.run(scenario())

    assert calls == 1
    assert values == [{"value": 1}, {"value": 1}]


def test_route_simplification_preserves_endpoints():
    route = {"id": "C1", "paths": [[(4.5, -74.2) for _ in range(200)]]}
    simplified = simplify_route_records([route], max_vertices=20)

    assert len(simplified[0]["paths"][0]) == 20
    assert simplified[0]["paths"][0][0] == route["paths"][0][0]
    assert simplified[0]["paths"][0][-1] == route["paths"][0][-1]
