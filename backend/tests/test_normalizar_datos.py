from app.ingestion.normalizar_datos import normalize_point_records


def test_normalize_arcgis_point_record():
    records = [
        {
            "OBJECTID": 7,
            "NOM_EST": "Estacion Cable",
            "geometry": {"x": -74.1502, "y": 4.5684},
        }
    ]

    normalized = normalize_point_records(records, source_type="estacion")

    assert normalized == [
        {
            "id": "7",
            "name": "Estacion Cable",
            "source_type": "estacion",
            "lat": 4.5684,
            "lng": -74.1502,
            "mode": "transmicable",
            "status": "normal",
            "raw": records[0],
        }
    ]


def test_normalize_discards_records_without_valid_coordinates():
    records = [{"OBJECTID": 1, "NOMBRE": "Sin coordenadas"}, {"lat": 91, "lng": -74}]

    assert normalize_point_records(records, source_type="parada") == []