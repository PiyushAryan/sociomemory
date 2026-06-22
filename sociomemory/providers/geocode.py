from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
INDIA_CITIES_PATH = DATA_DIR / "india_cities.json"
# H3 resolutions: coarse district (~5 km²), neighborhood (~0.1 km²), fine block (~0.002 km²).
DEFAULT_H3_RESOLUTIONS = (7, 9, 11)
# Hard radius for every geo/location feature: only consider points within 5 km.
DEFAULT_RADIUS_KM = 5.0


@dataclass(frozen=True)
class LocationMatch:
    label: str
    neighborhood: str
    city: str
    state: str
    lat: float
    lng: float
    distance_km: float
    source: str
    area_type: str | None = None
    tier: int | None = None


@dataclass(frozen=True)
class H3CellIndex:
    cells: dict[str, str]
    source: str = "h3"


class OfflineGeoResolver:
    provider_name = "offline_geo_resolver"
    requires_network = False

    def __init__(
        self, data_path: Path = INDIA_CITIES_PATH, max_distance_km: float = DEFAULT_RADIUS_KM
    ) -> None:
        self._data_path = data_path
        self._max_distance_km = max_distance_km
        self._rows = self._load_rows(data_path)
        self._gdf = self._build_geodataframe(self._rows)

    def reverse(self, lat: float, lng: float) -> LocationMatch | None:
        candidates = self._records()
        best: tuple[float, dict[str, Any]] | None = None
        for row in candidates:
            row_lat = row.get("lat")
            row_lng = row.get("lng")
            if row_lat is None or row_lng is None:
                continue
            distance = _haversine_km(lat, lng, float(row_lat), float(row_lng))
            if best is None or distance < best[0]:
                best = (distance, row)

        if best is None or best[0] > self._max_distance_km:
            return None

        distance, row = best
        neighborhood = str(row.get("neighborhood") or row.get("city") or "")
        city = str(row.get("city") or "")
        state = str(row.get("state") or "")
        label_parts = []
        for part in (neighborhood, city, state):
            if part and part not in label_parts:
                label_parts.append(part)
        return LocationMatch(
            label=", ".join(label_parts),
            neighborhood=neighborhood,
            city=city,
            state=state,
            lat=float(row["lat"]),
            lng=float(row["lng"]),
            distance_km=round(distance, 2),
            source="offline_geopandas" if self._gdf is not None else "offline_geo",
            area_type=row.get("area_type"),
            tier=row.get("tier"),
        )

    def _records(self) -> list[dict[str, Any]]:
        if self._gdf is not None:
            return self._gdf.drop(columns=["geometry"]).to_dict("records")
        return self._rows

    def _load_rows(self, path: Path) -> list[dict[str, Any]]:
        try:
            data = json.loads(path.read_text())
        except FileNotFoundError:
            logger.warning("Geo resolver data file not found: %s", path)
            return []
        if not isinstance(data, list):
            return []
        return [row for row in data if isinstance(row, dict)]

    def _build_geodataframe(self, rows: list[dict[str, Any]]):
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            return None

        points = []
        valid_rows = []
        for row in rows:
            if row.get("lat") is None or row.get("lng") is None:
                continue
            points.append(Point(float(row["lng"]), float(row["lat"])))
            valid_rows.append(row)
        if not valid_rows:
            return None
        return gpd.GeoDataFrame(valid_rows, geometry=points, crs="EPSG:4326")


class H3CellIndexer:
    provider_name = "h3_cell_indexer"
    requires_network = False

    def __init__(
        self, resolutions: tuple[int, ...] = DEFAULT_H3_RESOLUTIONS, h3_module: Any | None = None
    ) -> None:
        self._resolutions = resolutions
        self._h3 = h3_module

    def index(self, lat: float, lng: float) -> H3CellIndex | None:
        h3 = self._h3 or _load_h3()
        if h3 is None:
            return None

        # h3 v4: latlng_to_cell; v3 fallback: geo_to_h3.
        to_cell = getattr(h3, "latlng_to_cell", None) or getattr(h3, "geo_to_h3", None)
        if to_cell is None:
            return None

        cells = {f"res_{res}": to_cell(lat, lng, res) for res in self._resolutions}
        return H3CellIndex(cells=cells)


def h3_cell_index(
    lat: float, lng: float, resolutions: tuple[int, ...] = DEFAULT_H3_RESOLUTIONS
) -> H3CellIndex | None:
    return H3CellIndexer(resolutions=resolutions).index(lat, lng)


def _load_h3():
    try:
        import h3
    except ImportError:
        return None
    return h3


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
