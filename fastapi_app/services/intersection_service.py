"""Spatial Intersection Service – intersects user geometry with mining concessions."""

from fastapi import APIRouter, HTTPException
import requests

from .geo_utils import geojson_to_shapely

try:
    from shapely.geometry import mapping as shapely_mapping
    from shapely.ops import unary_union
except ImportError:  # pragma: no cover
    shapely_mapping = None
    unary_union = None

router = APIRouter()

# SERNAGEOMIN WFS endpoint
WFS_URL = "https://ide.sernageomin.cl/geoserver/wfs"


def _fetch_concessions_geojson(bbox_str: str) -> dict:
    """Fetch mining concession features from SERNAGEOMIN WFS."""
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "ide:concesiones",
        "outputFormat": "application/json",
        "bbox": bbox_str,
        "srsName": "EPSG:4326",
    }
    try:
        resp = requests.get(WFS_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {"type": "FeatureCollection", "features": []}


@router.post("/intersect")
async def intersect_geology(private_geojson: dict):
    """Receive a user GeoJSON and return the intersecting mining concession
    polygons together with overlap statistics.

    Input can be a FeatureCollection, Feature, or bare Geometry.
    """
    # ------------------------------------------------------------------
    # 1. Convert input to Shapely geometries
    # ------------------------------------------------------------------
    try:
        user_geoms = geojson_to_shapely(private_geojson)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid GeoJSON: {exc}")

    if not user_geoms:
        raise HTTPException(status_code=400, detail="No geometries found in input")

    user_union = unary_union(user_geoms) if unary_union else user_geoms[0]

    # ------------------------------------------------------------------
    # 2. Determine the bbox of the user area and fetch concessions
    # ------------------------------------------------------------------
    bounds = user_union.bounds  # (minx, miny, maxx, maxy)
    bbox_str = f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]}"
    concessions_gj = _fetch_concessions_geojson(bbox_str)

    # ------------------------------------------------------------------
    # 3. Compute intersections
    # ------------------------------------------------------------------
    intersecting_features = []
    for feat in concessions_gj.get("features", []):
        try:
            from shapely.geometry import shape as shapely_shape
            conc_geom = shapely_shape(feat["geometry"])
            if user_union.intersects(conc_geom):
                inter = user_union.intersection(conc_geom)
                overlap_area = inter.area  # in deg² (approximate)
                user_area = user_union.area if user_union.area > 0 else 1
                intersecting_features.append({
                    "type": "Feature",
                    "geometry": shapely_mapping(inter),
                    "properties": {
                        **feat.get("properties", {}),
                        "overlap_area_deg2": round(overlap_area, 8),
                        "overlap_pct": round(overlap_area / user_area * 100, 2),
                    },
                })
        except Exception:
            continue  # skip malformed features

    return {
        "type": "FeatureCollection",
        "features": intersecting_features,
        "summary": {
            "input_features": len(user_geoms),
            "concessions_in_bbox": len(concessions_gj.get("features", [])),
            "intersecting": len(intersecting_features),
        },
    }
