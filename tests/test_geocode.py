from __future__ import annotations

from pathlib import Path

import pytest

from sociomemory.providers.geocode import H3CellIndexer, OfflineGeoResolver


def test_offline_geo_resolver_finds_nearest_bundled_locality():
    match = OfflineGeoResolver().reverse(12.9353, 77.6244)

    assert match is not None
    assert match.neighborhood == "Koramangala"
    assert match.city == "Bangalore"
    assert match.state == "Karnataka"
    assert match.distance_km < 0.1
    assert match.source in {"offline_geopandas", "offline_geo"}


def test_offline_geo_resolver_returns_none_when_far_from_known_points():
    match = OfflineGeoResolver(max_distance_km=1.0).reverse(11.0, 77.0)

    assert match is None


def test_offline_geo_resolver_loads_custom_point_file(tmp_path: Path):
    data_path = tmp_path / "points.json"
    data_path.write_text(
        '[{"city":"Test City","neighborhood":"Test Area","state":"Test State",'
        '"lat":10.0,"lng":20.0,"area_type":"urban_middle","tier":3}]'
    )

    match = OfflineGeoResolver(data_path=data_path).reverse(10.001, 20.001)

    assert match is not None
    assert match.label == "Test Area, Test City, Test State"
    assert match.area_type == "urban_middle"
    assert match.tier == 3


def test_h3_cell_indexer_returns_none_without_h3_module(monkeypatch):
    import sociomemory.providers.geocode as geocode

    monkeypatch.setattr(geocode, "_load_h3", lambda: None)

    assert H3CellIndexer().index(12.9352, 77.6245) is None


def test_h3_cell_indexer_builds_cells_with_injected_module():
    class FakeH3:
        @staticmethod
        def latlng_to_cell(lat, lng, res):
            return f"cell-{res}"

    index = H3CellIndexer(resolutions=(7, 9), h3_module=FakeH3).index(12.9352, 77.6245)

    assert index is not None
    assert index.cells == {"res_7": "cell-7", "res_9": "cell-9"}
    assert index.source == "h3"


def test_h3_cell_indexer_real_module_produces_stable_cells():
    pytest.importorskip("h3")
    index = H3CellIndexer(resolutions=(7, 9, 11)).index(12.9352, 77.6245)

    assert index is not None
    assert set(index.cells) == {"res_7", "res_9", "res_11"}
    assert all(isinstance(cell, str) and cell for cell in index.cells.values())
