"""Elevation Profile Service – samples DEM elevations along a user-provided line."""

from fastapi import APIRouter, HTTPException

from .geo_utils import (
    fetch_elevations,
    interpolate_line,
    cumulative_distances,
)

router = APIRouter()


@router.post("/profile")
async def get_elevation_profile(line_geojson: dict, interval: float = 100.0):
    """Accept a GeoJSON LineString (or Feature / FeatureCollection containing one)
    and return an elevation profile sampled every *interval* metres.

    Response includes per-point data and summary statistics.
    """
    # ------------------------------------------------------------------
    # 1. Extract LineString coordinates
    # ------------------------------------------------------------------
    coords = None
    geom_type = line_geojson.get("type", "")

    if geom_type == "FeatureCollection":
        for feat in line_geojson.get("features", []):
            g = feat.get("geometry", {})
            if g.get("type") == "LineString":
                coords = g["coordinates"]
                break
    elif geom_type == "Feature":
        g = line_geojson.get("geometry", {})
        if g.get("type") == "LineString":
            coords = g["coordinates"]
    elif geom_type == "LineString":
        coords = line_geojson.get("coordinates")

    if not coords or len(coords) < 2:
        raise HTTPException(
            status_code=400,
            detail="Input must contain a LineString with at least 2 coordinates",
        )

    # ------------------------------------------------------------------
    # 2. Interpolate points along the line
    # ------------------------------------------------------------------
    interval_m = max(10.0, min(interval, 5000.0))  # clamp to 10 m – 5 km
    try:
        sampled = interpolate_line(coords, interval_m)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Interpolation error: {exc}")

    # ------------------------------------------------------------------
    # 3. Fetch elevations
    # ------------------------------------------------------------------
    try:
        elevations = await fetch_elevations(sampled)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Elevation lookup failed: {exc}")

    # ------------------------------------------------------------------
    # 4. Compute cumulative distances
    # ------------------------------------------------------------------
    dists = cumulative_distances(sampled)

    # ------------------------------------------------------------------
    # 5. Build response
    # ------------------------------------------------------------------
    profile = []
    for pt, elev, dist in zip(sampled, elevations, dists):
        profile.append({
            "distance": round(dist, 1),
            "elevation": round(elev, 1),
            "latitude": round(pt["latitude"], 6),
            "longitude": round(pt["longitude"], 6),
        })

    elev_arr = [p["elevation"] for p in profile]

    return {
        "profile": profile,
        "total_distance": round(dists[-1], 1),
        "min_elevation": round(min(elev_arr), 1),
        "max_elevation": round(max(elev_arr), 1),
        "elevation_gain": round(
            sum(max(0, elev_arr[i] - elev_arr[i - 1]) for i in range(1, len(elev_arr))), 1
        ),
        "num_points": len(profile),
    }
