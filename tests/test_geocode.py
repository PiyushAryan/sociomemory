from __future__ import annotations

from pathlib import Path

from sociomemory.providers.geocode import OfflineGeoResolver, S2CellIndexer


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


def test_s2_cell_indexer_returns_none_without_s2_module(monkeypatch):
    import sociomemory.providers.geocode as geocode

    monkeypatch.setattr(geocode, "_load_s2sphere", lambda: None)

    assert S2CellIndexer().index(12.9352, 77.6245) is None


def test_s2_cell_indexer_builds_tokens_with_injected_module():
    class FakeLatLng:
        @staticmethod
        def from_degrees(lat, lng):
            return (lat, lng)

    class FakeCell:
        def __init__(self, level=None):
            self.level = level

        @staticmethod
        def from_lat_lng(lat_lng):
            return FakeCell()

        def parent(self, level):
            return FakeCell(level=level)

        def to_token(self):
            return f"cell-{self.level}"

    class FakeS2:
        LatLng = FakeLatLng
        CellId = FakeCell

    index = S2CellIndexer(levels=(10, 12), s2_module=FakeS2).index(12.9352, 77.6245)

    assert index is not None
    assert index.cells == {"level_10": "cell-10", "level_12": "cell-12"}
    assert index.source == "s2sphere"
