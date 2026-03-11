"""DEM Slope Service – computes slope from elevation data.

Uses Horn's method (3×3 weighted kernel, same as ArcGIS/QGIS) with adaptive
Gaussian pre-smoothing to reduce DEM noise artifacts.

Elevation source priority:
  1. LiDAR local (highest resolution)
  2. OpenTopography ALOS World 3D 30m (needs API key)
  3. Open-Elevation SRTM
  4. Synthetic fallback
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import numpy as np
from scipy.ndimage import gaussian_filter

from .geo_utils import parse_bbox, bbox_grid, fetch_elevations

router = APIRouter()

# ── In-memory cache for elevation data ──────────────────────────────────
_elevation_cache: dict = {}
_CACHE_MAX_SIZE = 50  # Max cached grids


def _cache_key(bbox_str: str, n: int) -> str:
    """Create a stable cache key from bbox + resolution."""
    return f"{bbox_str}|{n}"


def _adaptive_sigma(elev_grid: np.ndarray) -> float:
    """Compute adaptive Gaussian sigma based on terrain roughness.

    Flat terrain → higher sigma (more smoothing to suppress noise).
    Rough terrain → lower sigma (preserve real features).
    Returns sigma in range [0.3, 1.5].
    """
    std = np.std(elev_grid)
    if std < 5:
        return 1.2    # Very flat – smooth aggressively
    elif std < 20:
        return 0.8    # Moderate relief
    elif std < 100:
        return 0.5    # Hilly
    else:
        return 0.3    # Mountainous – minimal smoothing


def _compute_slope(elev_grid: np.ndarray, parsed_bbox: tuple, n: int):
    """Core slope computation using Horn's method.

    Returns (slope_deg, slope_pct, sigma_used).
    """
    # ── Adaptive Gaussian pre-smoothing ─────────────────────────
    sigma = _adaptive_sigma(elev_grid)
    elev_smooth = gaussian_filter(elev_grid, sigma=sigma)

    # Compute spatial resolution in metres (approx at bbox centre)
    minx, miny, maxx, maxy = parsed_bbox
    lat_centre = (miny + maxy) / 2.0
    dx_deg = (maxx - minx) / (n - 1)
    dy_deg = (maxy - miny) / (n - 1)
    m_per_deg_lon = 111_320 * np.cos(np.radians(lat_centre))
    m_per_deg_lat = 110_540.0
    dx_m = dx_deg * m_per_deg_lon
    dy_m = dy_deg * m_per_deg_lat

    # ── Horn's method (3×3 weighted kernel) ─────────────────────
    #   a  b  c        dz/dx = ((c+2f+i) - (a+2d+g)) / (8·dx)
    #   d  e  f        dz/dy = ((g+2h+i) - (a+2b+c)) / (8·dy)
    #   g  h  i
    z = elev_smooth
    zp = np.pad(z, 1, mode='reflect')

    a = zp[:-2, :-2];  b = zp[:-2, 1:-1];  c = zp[:-2, 2:]
    d = zp[1:-1, :-2];                      f = zp[1:-1, 2:]   # noqa: E702
    g = zp[2:, :-2];   h = zp[2:, 1:-1];   i = zp[2:, 2:]

    dzdx = ((c + 2*f + i) - (a + 2*d + g)) / (8.0 * dx_m)
    dzdy = ((g + 2*h + i) - (a + 2*b + c)) / (8.0 * dy_m)

    slope_rad = np.arctan(np.sqrt(dzdx**2 + dzdy**2))
    slope_deg = np.degrees(slope_rad)
    slope_pct = np.tan(slope_rad) * 100.0

    return slope_deg, slope_pct, sigma


def _compute_histogram(slope_pct: np.ndarray,
                       ranges: list = None) -> list:
    """Compute slope distribution histogram.

    If ranges are provided, use them as bins.
    Otherwise, use default bins.
    """
    if ranges is None:
        ranges = [
            {"min": 0, "max": 3},
            {"min": 3, "max": 7},
            {"min": 7, "max": 12},
            {"min": 12, "max": 25},
            {"min": 25, "max": 50},
            {"min": 50, "max": 75},
            {"min": 75, "max": 999},
        ]

    flat = slope_pct.flatten()
    total = len(flat)
    histogram = []

    for r in ranges:
        count = int(np.sum((flat >= r["min"]) & (flat < r["max"])))
        histogram.append({
            "min": r["min"],
            "max": r["max"],
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0,
        })

    return histogram


SOURCE_LABELS = {
    "lidar": "LiDAR Local",
    "alos_world3d": "ALOS World 3D (30m)",
    "open_elevation_srtm": "Open-Elevation SRTM (30m)",
    "synthetic": "Datos Sintéticos (offline)",
}


@router.get("/slope")
async def get_slope(bbox: str, resolution: int = 10):
    """Generate a slope map for the given bounding box.

    ``bbox`` format: ``"minx,miny,maxx,maxy"`` (EPSG:4326).
    ``resolution`` controls the grid size (n×n points, default 10, max 100).

    Returns elevations, computed slopes in both degrees and percent,
    the coordinate grid, histogram, and the elevation data source used.
    """
    try:
        parsed = parse_bbox(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Clamp resolution to a sensible range
    n = max(3, min(resolution, 100))

    # ── Check cache first ───────────────────────────────────────
    ck = _cache_key(bbox, n)
    cached = _elevation_cache.get(ck)

    if cached:
        elev_flat, source = cached["elevations"], cached["source"]
        print(f"[DEM] Cache hit for {ck}")
    else:
        # Build the sample grid and fetch elevations
        points = bbox_grid(parsed, n)
        try:
            elev_flat, source = await fetch_elevations(points, bbox=parsed)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Error obteniendo elevaciones: {exc}"
            )

        # Store in cache (evict oldest if full)
        if len(_elevation_cache) >= _CACHE_MAX_SIZE:
            oldest = next(iter(_elevation_cache))
            del _elevation_cache[oldest]
        _elevation_cache[ck] = {"elevations": elev_flat, "source": source}

    # Reshape into 2-D arrays (rows = latitude, cols = longitude)
    elev_grid = np.array(elev_flat, dtype=float).reshape(n, n)

    # ── Compute slopes ──────────────────────────────────────────
    slope_deg, slope_pct, sigma_used = _compute_slope(elev_grid, parsed, n)

    # ── Histogram ───────────────────────────────────────────────
    histogram = _compute_histogram(slope_pct)

    # ── Spatial resolution info ─────────────────────────────────
    minx, miny, maxx, maxy = parsed
    lat_centre = (miny + maxy) / 2.0
    dx_m = ((maxx - minx) / (n - 1)) * 111_320 * np.cos(np.radians(lat_centre))
    dy_m = ((maxy - miny) / (n - 1)) * 110_540.0

    return {
        "bbox": bbox,
        "grid_size": n,
        "elevations": elev_grid.tolist(),
        "slopes": slope_deg.tolist(),
        "slopes_percent": slope_pct.tolist(),
        "stats": {
            "min_slope": round(float(slope_deg.min()), 2),
            "max_slope": round(float(slope_deg.max()), 2),
            "mean_slope": round(float(slope_deg.mean()), 2),
            "min_slope_pct": round(float(slope_pct.min()), 2),
            "max_slope_pct": round(float(slope_pct.max()), 2),
            "mean_slope_pct": round(float(slope_pct.mean()), 2),
            "std_slope_pct": round(float(slope_pct.std()), 2),
        },
        "histogram": histogram,
        "processing": {
            "gaussian_sigma": round(sigma_used, 2),
            "pixel_size_m": {
                "x": round(float(dx_m), 1),
                "y": round(float(dy_m), 1),
            },
        },
        "source": source,
        "source_label": SOURCE_LABELS.get(source, source),
    }


@router.get("/slope/export")
async def export_slope_geojson(bbox: str, resolution: int = 10):
    """Export slope data as a GeoJSON FeatureCollection.

    Each cell becomes a polygon feature with slope properties.
    Useful for importing into QGIS or other GIS tools.
    """
    try:
        parsed = parse_bbox(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    n = max(3, min(resolution, 100))

    # Use cache or fetch
    ck = _cache_key(bbox, n)
    cached = _elevation_cache.get(ck)

    if cached:
        elev_flat, source = cached["elevations"], cached["source"]
    else:
        points = bbox_grid(parsed, n)
        try:
            elev_flat, source = await fetch_elevations(points, bbox=parsed)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Error obteniendo elevaciones: {exc}"
            )
        if len(_elevation_cache) >= _CACHE_MAX_SIZE:
            oldest = next(iter(_elevation_cache))
            del _elevation_cache[oldest]
        _elevation_cache[ck] = {"elevations": elev_flat, "source": source}

    elev_grid = np.array(elev_flat, dtype=float).reshape(n, n)
    slope_deg, slope_pct, _ = _compute_slope(elev_grid, parsed, n)

    minx, miny, maxx, maxy = parsed
    dx = (maxx - minx) / n
    dy = (maxy - miny) / n

    features = []
    for r in range(slope_pct.shape[0]):
        for c in range(slope_pct.shape[1]):
            x0 = minx + c * dx
            y0 = miny + r * dy
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [x0, y0],
                        [x0 + dx, y0],
                        [x0 + dx, y0 + dy],
                        [x0, y0 + dy],
                        [x0, y0],
                    ]],
                },
                "properties": {
                    "slope_deg": round(float(slope_deg[r, c]), 2),
                    "slope_pct": round(float(slope_pct[r, c]), 2),
                    "elevation": round(float(elev_grid[r, c]), 1),
                    "row": r,
                    "col": c,
                },
            })

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "source": source,
            "source_label": SOURCE_LABELS.get(source, source),
            "grid_size": n,
            "bbox": bbox,
        },
    }

    return JSONResponse(
        content=geojson,
        headers={
            "Content-Disposition": f"attachment; filename=slope_map_{n}x{n}.geojson",
        },
    )
