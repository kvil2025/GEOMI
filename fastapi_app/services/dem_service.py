"""DEM Slope Service – computes slope from elevation data.

Uses Horn's method (3×3 weighted kernel, same as ArcGIS/QGIS) with optional
Gaussian pre-smoothing to reduce DEM noise artifacts.

Elevation source priority:
  1. LiDAR local (highest resolution)
  2. OpenTopography ALOS World 3D 30m (needs API key)
  3. Open-Elevation SRTM
  4. Synthetic fallback
"""

from fastapi import APIRouter, HTTPException
import numpy as np
from scipy.ndimage import gaussian_filter

from .geo_utils import parse_bbox, bbox_grid, fetch_elevations, get_last_elevation_source

router = APIRouter()


@router.get("/slope")
async def get_slope(bbox: str, resolution: int = 10):
    """Generate a slope map for the given bounding box.

    ``bbox`` format: ``"minx,miny,maxx,maxy"`` (EPSG:4326).
    ``resolution`` controls the grid size (n×n points, default 10, max 100).

    Returns elevations, computed slopes in both degrees and percent,
    the coordinate grid, and the elevation data source used.
    """
    try:
        parsed = parse_bbox(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Clamp resolution to a sensible range (up to 100 for detailed maps)
    n = max(3, min(resolution, 100))

    # Build the sample grid and fetch elevations
    points = bbox_grid(parsed, n)
    try:
        elev_flat = await fetch_elevations(points, bbox=parsed)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Elevation lookup failed: {exc}")

    source = get_last_elevation_source()

    # Reshape into 2-D arrays (rows = latitude, cols = longitude)
    elev_grid = np.array(elev_flat, dtype=float).reshape(n, n)

    # ── Gaussian pre-smoothing to reduce DEM noise ──────────────
    # sigma=0.8 is mild: removes single-pixel noise (checkerboard)
    # while preserving real topographic features
    elev_smooth = gaussian_filter(elev_grid, sigma=0.8)

    # Compute spatial resolution in metres (approx at bbox centre)
    minx, miny, maxx, maxy = parsed
    lat_centre = (miny + maxy) / 2.0
    dx_deg = (maxx - minx) / (n - 1)
    dy_deg = (maxy - miny) / (n - 1)
    m_per_deg_lon = 111_320 * np.cos(np.radians(lat_centre))
    m_per_deg_lat = 110_540.0
    dx_m = dx_deg * m_per_deg_lon
    dy_m = dy_deg * m_per_deg_lat

    # ── Horn's method (3×3 weighted kernel) ─────────────────────
    # Same algorithm used by ArcGIS, QGIS, and GDAL.
    # Weights 8 neighbours (cardinals ×2, diagonals ×1).
    #
    #   a  b  c        dz/dx = ((c+2f+i) - (a+2d+g)) / (8·dx)
    #   d  e  f        dz/dy = ((g+2h+i) - (a+2b+c)) / (8·dy)
    #   g  h  i
    #
    z = elev_smooth
    # Pad the grid by 1 to handle edges (reflect mode keeps values natural)
    zp = np.pad(z, 1, mode='reflect')

    a = zp[:-2, :-2];  b = zp[:-2, 1:-1];  c = zp[:-2, 2:]
    d = zp[1:-1, :-2];                      f = zp[1:-1, 2:]   # noqa: E702
    g = zp[2:, :-2];   h = zp[2:, 1:-1];   i = zp[2:, 2:]

    dzdx = ((c + 2*f + i) - (a + 2*d + g)) / (8.0 * dx_m)
    dzdy = ((g + 2*h + i) - (a + 2*b + c)) / (8.0 * dy_m)

    slope_rad = np.arctan(np.sqrt(dzdx**2 + dzdy**2))
    slope_deg = np.degrees(slope_rad)
    # Slope in percent: tan(angle) × 100
    slope_pct = np.tan(slope_rad) * 100.0

    source_labels = {
        "lidar": "LiDAR Local",
        "alos_world3d": "ALOS World 3D (30m)",
        "open_elevation_srtm": "Open-Elevation SRTM (30m)",
        "synthetic": "Datos Sintéticos (offline)",
    }

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
        },
        "source": source,
        "source_label": source_labels.get(source, source),
    }
