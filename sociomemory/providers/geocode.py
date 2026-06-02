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
DEFAULT_S2_LEVELS = (10, 12, 14)


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
class S2CellIndex:
    cells: dict[str, str]
    source: str = "s2sphere"


class OfflineGeoResolver:

    provider_name = "offline_geo_resolver"
    requires_network = False

    def __init__(self, data_path: Path = INDIA_CITIES_PATH, max_distance_km: float = 75.0) -> None:
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
            import geopandas as gpd  # type: ignore
            from shapely.geometry import Point  # type: ignore
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


class S2CellIndexer:

    provider_name = "s2_cell_indexer"
    requires_network = False

    def __init__(self, levels: tuple[int, ...] = DEFAULT_S2_LEVELS, s2_module: Any | None = None) -> None:
        self._levels = levels
        self._s2 = s2_module

    def index(self, lat: float, lng: float) -> S2CellIndex | None:
        s2 = self._s2 or _load_s2sphere()
        if s2 is None:
            return None

        lat_lng = s2.LatLng.from_degrees(lat, lng)
        cells = {}
        for level in self._levels:
            cell = s2.CellId.from_lat_lng(lat_lng).parent(level)
            cells[f"level_{level}"] = cell.to_token()
        return S2CellIndex(cells=cells)


def s2_cell_index(lat: float, lng: float, levels: tuple[int, ...] = DEFAULT_S2_LEVELS) -> S2CellIndex | None:
    return S2CellIndexer(levels=levels).index(lat, lng)


def _load_s2sphere():
    try:
        import s2sphere  # type: ignore
    except ImportError:
        return None
    return s2sphere


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
