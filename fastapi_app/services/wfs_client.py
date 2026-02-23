import json
import hashlib
import os
import time
from typing import Optional
from fastapi import APIRouter
import requests

router = APIRouter()

# ── PATHS ─────────────────────────────────────────────────────────────────
_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
_SAMPLE_FILE = os.path.join(_DATA_DIR, 'sample_concessions.json')
_CACHE_DIR = os.path.join(_DATA_DIR, 'cache')
os.makedirs(_CACHE_DIR, exist_ok=True)

# ── SERNAGEOMIN ArcGIS FeatureServer ──────────────────────────────────────
# Source: https://appsngmaz.sernageomin.cl/catastro_SNGM/home/index
# Data updated: 04 Feb 2026  |  Total: 106,402 concessions
ARCGIS_FEATURE_URL = (
    "https://services1.arcgis.com/OyjvVdFTl5hfSdX3"
    "/ArcGIS/rest/services/Marcelo_Layer/FeatureServer/2/query"
)

OUT_FIELDS = ",".join([
    "OBJECTID", "NOMBRE", "HECTAREAS", "TIPO_CONCESION",
    "SITUACION_CONCESION", "TITULAR_NOMBRE", "TITULAR_RUT",
    "COMUNA", "ID_CONCESION", "NUMERO_ROL",
    "ANO_INSCRIPCION", "FECHA_ACTUALIZACION",
])

# Cache TTL: 24 hours (concession data doesn't change often)
CACHE_TTL_SECONDS = 24 * 60 * 60


# ── CACHE HELPERS ─────────────────────────────────────────────────────────

def _bbox_cache_key(bbox: str) -> str:
    """Generate a deterministic cache key from a bbox string.
    Rounds coordinates to 2 decimals so nearby viewports share cache."""
    try:
        parts = [round(float(v), 2) for v in bbox.split(',')]
        normalized = ",".join(str(v) for v in parts)
    except Exception:
        normalized = bbox
    return hashlib.md5(normalized.encode()).hexdigest()


def _cache_path(key: str) -> str:
    return os.path.join(_CACHE_DIR, f"concessions_{key}.json")


def _read_cache(bbox: str) -> Optional[dict]:
    """Return cached FeatureCollection if it exists and is fresh."""
    key = _bbox_cache_key(bbox)
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        age = time.time() - os.path.getmtime(path)
        if age > CACHE_TTL_SECONDS:
            os.remove(path)
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[CACHE] HIT — {len(data.get('features',[]))} features (age {age/3600:.1f}h)")
        return data
    except Exception:
        return None


def _write_cache(bbox: str, data: dict):
    """Persist a FeatureCollection to the cache directory."""
    key = _bbox_cache_key(bbox)
    path = _cache_path(key)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        n = len(data.get('features', []))
        print(f"[CACHE] WRITE — {n} features → {os.path.basename(path)}")
    except Exception as e:
        print(f"[CACHE] write failed: {e}")


# ── DATA SOURCES ──────────────────────────────────────────────────────────

def _load_sample():
    with open(_SAMPLE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _normalize_properties(props: dict) -> dict:
    """Map ArcGIS field names to user-friendly Spanish keys."""
    return {
        "nombre": props.get("NOMBRE", ""),
        "tipo": props.get("TIPO_CONCESION", ""),
        "titular": props.get("TITULAR_NOMBRE", ""),
        "estado": props.get("SITUACION_CONCESION", ""),
        "hectareas": props.get("HECTAREAS", 0),
        "expediente": props.get("NUMERO_ROL", ""),
        "comuna": props.get("COMUNA", ""),
        "id_concesion": props.get("ID_CONCESION", ""),
        "ano_inscripcion": props.get("ANO_INSCRIPCION", ""),
        "rut_titular": props.get("TITULAR_RUT", ""),
        "fecha_actualizacion": props.get("FECHA_ACTUALIZACION", ""),
    }


def _query_arcgis(bbox: str, max_features: int = 500) -> dict:
    """Query SERNAGEOMIN FeatureServer, return normalized GeoJSON."""
    params = {
        "f": "geojson",
        "where": "1=1",
        "geometry": bbox,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": OUT_FIELDS,
        "resultRecordCount": max_features,
    }
    resp = requests.get(ARCGIS_FEATURE_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    for feat in data.get("features", []):
        feat["properties"] = _normalize_properties(feat.get("properties", {}))

    return data


def _filter_sample_by_bbox(bbox: str) -> list:
    minx, miny, maxx, maxy = [float(v) for v in bbox.split(',')]
    sample = _load_sample()

    def centroid_in_bbox(feature):
        coords = feature['geometry']['coordinates'][0]
        cx = sum(c[0] for c in coords) / len(coords)
        cy = sum(c[1] for c in coords) / len(coords)
        return minx <= cx <= maxx and miny <= cy <= maxy

    return [f for f in sample['features'] if centroid_in_bbox(f)]


# ── API ENDPOINT ──────────────────────────────────────────────────────────

@router.get("/polygons")
async def get_concessions(bbox: str, refresh: bool = False):
    """Fetch mining concession polygons with local cache.

    Flow:
      1. Check local JSON cache (valid 24h)
      2. If miss → query SERNAGEOMIN ArcGIS API → cache result
      3. If API fails → return sample data

    Args:
        bbox: "minx,miny,maxx,maxy" in EPSG:4326
        refresh: if True, bypass cache and fetch fresh data
    """
    # 1. Check cache (unless forced refresh)
    if not refresh:
        cached = _read_cache(bbox)
        if cached:
            cached["source"] = "cache"
            return cached

    # 2. Fetch from SERNAGEOMIN
    try:
        data = _query_arcgis(bbox)
        features = data.get("features", [])
        result = {
            "type": "FeatureCollection",
            "features": features,
            "source": "sernageomin_catastro",
            "count": len(features),
        }
        # Save to cache
        _write_cache(bbox, result)
        return result
    except Exception as e:
        print(f"[WFS] SERNAGEOMIN ArcGIS failed: {e}")

    # 3. Fallback to sample data (not cached)
    try:
        features = _filter_sample_by_bbox(bbox)
    except Exception:
        features = _load_sample().get("features", [])

    return {
        "type": "FeatureCollection",
        "features": features,
        "source": "sample",
        "count": len(features),
    }


@router.delete("/cache")
async def clear_cache():
    """Clear all cached concession data."""
    count = 0
    for f in os.listdir(_CACHE_DIR):
        if f.startswith("concessions_") and f.endswith(".json"):
            os.remove(os.path.join(_CACHE_DIR, f))
            count += 1
    return {"cleared": count, "message": f"Eliminados {count} archivos de caché"}
