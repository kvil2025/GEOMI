"""Shared geospatial utilities for the Mining Intelligence Backend."""

import math
import os
from typing import List, Tuple, Dict, Any

import httpx
import numpy as np

try:
    from pyproj import Geod
    _geod = Geod(ellps="WGS84")
except ImportError:  # pragma: no cover
    _geod = None

try:
    from shapely.geometry import shape as shapely_shape, mapping as shapely_mapping
    from shapely.ops import unary_union
except ImportError:  # pragma: no cover
    shapely_shape = None
    shapely_mapping = None
    unary_union = None


# ---------------------------------------------------------------------------
# Bounding-box helpers
# ---------------------------------------------------------------------------

def parse_bbox(bbox_str: str) -> Tuple[float, float, float, float]:
    """Parse `"minx,miny,maxx,maxy"` → (minx, miny, maxx, maxy)."""
    parts = [float(p.strip()) for p in bbox_str.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must have exactly 4 comma-separated values")
    return tuple(parts)  # type: ignore[return-value]


def bbox_grid(bbox: Tuple[float, float, float, float],
              n: int = 10) -> List[Dict[str, float]]:
    """Return an n×n grid of {latitude, longitude} points inside *bbox*."""
    minx, miny, maxx, maxy = bbox
    xs = np.linspace(minx, maxx, n)
    ys = np.linspace(miny, maxy, n)
    points: List[Dict[str, float]] = []
    for y in ys:
        for x in xs:
            points.append({"latitude": float(y), "longitude": float(x)})
    return points


# ---------------------------------------------------------------------------
# Elevation lookups — priority chain:
#   1. LiDAR local (if available for the bbox)
#   2. OpenTopography ALOS World 3D 30m
#   3. Open-Elevation (SRTM)
#   4. Synthetic fallback
# ---------------------------------------------------------------------------

OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"
OPENTOPO_URL = "https://portal.opentopography.org/API/globaldem"
_BATCH_SIZE = 100

_last_source = "unknown"  # Track which source was used


def get_last_elevation_source() -> str:
    """Return the name of the last elevation data source used."""
    return _last_source


def _get_opentopo_key() -> str:
    """Read OpenTopography API key at call time (after dotenv loads)."""
    return os.environ.get("OPENTOPO_API_KEY", "")


async def _fetch_opentopo(points: List[Dict[str, float]],
                          bbox: Tuple[float, float, float, float]
                          ) -> List[float]:
    """Fetch elevations from OpenTopography ALOS World 3D.

    Downloads a small GeoTIFF for the bbox, then samples elevation at points.
    Requires OPENTOPO_API_KEY env var and rasterio.
    """
    # Check prerequisites upfront
    api_key = _get_opentopo_key()
    if not api_key:
        raise RuntimeError("OPENTOPO_API_KEY not set")
    try:
        import rasterio
    except ImportError:
        raise RuntimeError("rasterio not installed — install with: pip install rasterio")

    import tempfile
    minx, miny, maxx, maxy = bbox
    params = {
        "demtype": "AW3D30",        # ALOS World 3D 30m
        "south": miny,
        "north": maxy,
        "west": minx,
        "east": maxx,
        "outputFormat": "GTiff",
        "API_Key": api_key,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(OPENTOPO_URL, params=params)
        resp.raise_for_status()

    # Save to temp file and sample with rasterio
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    tmp.write(resp.content)
    tmp.close()

    try:
        elevations = []
        with rasterio.open(tmp.name) as ds:
            band = ds.read(1)
            for pt in points:
                lon, lat = pt["longitude"], pt["latitude"]
                row, col = ds.index(lon, lat)
                if 0 <= row < band.shape[0] and 0 <= col < band.shape[1]:
                    val = float(band[row, col])
                    if ds.nodata is not None and val == ds.nodata:
                        elevations.append(0.0)
                    else:
                        elevations.append(val)
                else:
                    elevations.append(0.0)
        return elevations
    finally:
        os.unlink(tmp.name)


async def _fetch_open_elevation(points: List[Dict[str, float]]) -> List[float]:
    """Fetch from Open-Elevation API (SRTM ~30m)."""
    elevations: List[float] = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for i in range(0, len(points), _BATCH_SIZE):
            batch = points[i:i + _BATCH_SIZE]
            payload = {"locations": batch}
            resp = await client.post(OPEN_ELEVATION_URL, json=payload)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            elevations.extend(r["elevation"] for r in results)
    return elevations


def _synthetic_elevations(points: List[Dict[str, float]]) -> List[float]:
    """Generate synthetic elevation (offline fallback)."""
    elevations = []
    for p in points:
        lat, lon = p["latitude"], p["longitude"]
        elev = 500 + 200 * math.sin(lat * 0.1) + 150 * math.cos(lon * 0.1)
        elevations.append(round(elev, 1))
    return elevations


async def fetch_elevations(
    points: List[Dict[str, float]],
    bbox: Tuple[float, float, float, float] = None,
) -> List[float]:
    """Fetch elevation data using the best available source.

    Priority:
      1. LiDAR local GeoTIFF (if one covers the bbox)
      2. OpenTopography ALOS World 3D 30m (needs API key)
      3. Open-Elevation API (SRTM)
      4. Synthetic fallback
    """
    global _last_source

    # 1. Try local LiDAR
    if bbox:
        try:
            from .lidar_service import find_lidar_for_bbox, sample_lidar_elevations
            lidar_path = find_lidar_for_bbox(bbox)
            if lidar_path:
                result = sample_lidar_elevations(lidar_path, points)
                if result and len(result) == len(points):
                    _last_source = "lidar"
                    print(f"[DEM] Using LiDAR: {os.path.basename(lidar_path)}")
                    return result
        except Exception as e:
            print(f"[DEM] LiDAR check failed: {e}")

    # 2. Try OpenTopography ALOS
    if bbox and _get_opentopo_key():
        try:
            result = await _fetch_opentopo(points, bbox)
            _last_source = "alos_world3d"
            print("[DEM] Using OpenTopography ALOS World 3D")
            return result
        except Exception as e:
            print(f"[DEM] OpenTopography failed: {e}")

    # 3. Try Open-Elevation
    try:
        result = await _fetch_open_elevation(points)
        _last_source = "open_elevation_srtm"
        print("[DEM] Using Open-Elevation (SRTM)")
        return result
    except Exception as e:
        print(f"[DEM] Open-Elevation failed: {e}")

    # 4. Synthetic fallback
    _last_source = "synthetic"
    print("[DEM] Using synthetic elevation (offline mode)")
    return _synthetic_elevations(points)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def geojson_to_shapely(geojson: dict):
    """Convert a GeoJSON dict (Feature, FeatureCollection, or bare Geometry)
    into a list of Shapely geometry objects."""
    if shapely_shape is None:
        raise ImportError("shapely is required for spatial operations")

    geom_type = geojson.get("type", "")
    if geom_type == "FeatureCollection":
        return [shapely_shape(f["geometry"]) for f in geojson.get("features", [])]
    elif geom_type == "Feature":
        return [shapely_shape(geojson["geometry"])]
    else:
        return [shapely_shape(geojson)]


def interpolate_line(coords: List[List[float]],
                     interval_m: float = 100.0) -> List[Dict[str, float]]:
    """Return evenly spaced points along a polyline every *interval_m* metres.

    *coords* is ``[[lon, lat], …]``.  Returns ``[{"latitude", "longitude"}, …]``.
    """
    if _geod is None:
        raise ImportError("pyproj is required for distance calculations")

    sampled: List[Dict[str, float]] = []
    sampled.append({"latitude": coords[0][1], "longitude": coords[0][0]})
    accumulated = 0.0

    for k in range(1, len(coords)):
        lon1, lat1 = coords[k - 1]
        lon2, lat2 = coords[k]
        _, _, seg_dist = _geod.inv(lon1, lat1, lon2, lat2)  # metres

        remaining = interval_m - accumulated
        while remaining <= seg_dist:
            frac = remaining / seg_dist if seg_dist > 0 else 0
            int_lon = lon1 + frac * (lon2 - lon1)
            int_lat = lat1 + frac * (lat2 - lat1)
            sampled.append({"latitude": float(int_lat), "longitude": float(int_lon)})
            seg_dist -= remaining
            lon1, lat1 = int_lon, int_lat
            remaining = interval_m
            accumulated = 0.0
        accumulated += seg_dist

    # Always include the last vertex
    sampled.append({"latitude": coords[-1][1], "longitude": coords[-1][0]})
    return sampled


def cumulative_distances(points: List[Dict[str, float]]) -> List[float]:
    """Return cumulative geodesic distances (metres) for a list of points."""
    if _geod is None:
        raise ImportError("pyproj is required for distance calculations")

    dists = [0.0]
    for i in range(1, len(points)):
        _, _, d = _geod.inv(
            points[i - 1]["longitude"], points[i - 1]["latitude"],
            points[i]["longitude"], points[i]["latitude"],
        )
        dists.append(dists[-1] + d)
    return dists
