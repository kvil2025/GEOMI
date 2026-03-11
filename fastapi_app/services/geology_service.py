"""Geology Map Service – optimized with R-tree spatial index.

Supports two resolution modes:
  - simplified (default): Douglas-Peucker simplified geometry for fast loading
  - full: original geometry with full vertex detail for zoomed-in views
"""

import os
import json
import time
import math
import hashlib
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'geodata')
_SHAPEFILE_PATH = os.path.join(_DATA_DIR, 'GEOL-CHILE')
_CACHE_PATH = os.path.join(_DATA_DIR, 'GEOL-CHILE.geojson')
_OPTIMIZED_CACHE_PATH = os.path.join(_DATA_DIR, 'GEOL-CHILE.optimized.v2.json')

# In-memory caches
_features_cache: Optional[list] = None    # list of dicts with bbox + both coords
_rtree_index = None                        # R-tree spatial index
_raw_geojson_cache: Optional[dict] = None  # keep raw GeoJSON for full-res queries


# ── Geometry simplification (Douglas-Peucker) ─────────────────────────

def _perpendicular_distance(point, line_start, line_end):
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    if dx == 0 and dy == 0:
        return math.sqrt((point[0] - line_start[0])**2 + (point[1] - line_start[1])**2)
    t = ((point[0] - line_start[0]) * dx + (point[1] - line_start[1]) * dy) / (dx*dx + dy*dy)
    t = max(0, min(1, t))
    proj_x = line_start[0] + t * dx
    proj_y = line_start[1] + t * dy
    return math.sqrt((point[0] - proj_x)**2 + (point[1] - proj_y)**2)


def _simplify_ring(coords: list, tolerance: float) -> list:
    if len(coords) <= 4:
        return coords
    dmax = 0
    index = 0
    end = len(coords) - 1
    for i in range(1, end):
        d = _perpendicular_distance(coords[i], coords[0], coords[end])
        if d > dmax:
            index = i
            dmax = d
    if dmax > tolerance:
        left = _simplify_ring(coords[:index + 1], tolerance)
        right = _simplify_ring(coords[index:], tolerance)
        return left[:-1] + right
    else:
        return [coords[0], coords[end]]


def _simplify_polygon(coordinates: list, tolerance: float) -> list:
    simplified = []
    for ring in coordinates:
        s = _simplify_ring(ring, tolerance)
        if len(s) < 3:
            simplified.append(ring)
        else:
            if s[0] != s[-1]:
                s.append(s[0])
            simplified.append(s)
    return simplified


def _compute_bbox(coordinates: list) -> Tuple[float, float, float, float]:
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for ring in coordinates:
        for pt in ring:
            if pt[0] < min_x: min_x = pt[0]
            if pt[0] > max_x: max_x = pt[0]
            if pt[1] < min_y: min_y = pt[1]
            if pt[1] > max_y: max_y = pt[1]
    return (min_x, min_y, max_x, max_y)


# ── Geologically-meaningful color palettes ─────────────────────────────

_LITHO_COLORS = {
    "Qa": "#FFFACD", "Qe": "#FAF0BE", "Qf": "#FFF8DC", "Qm": "#F5DEB3",
    "Ql": "#FAEBD7", "Pl1m": "#F5E6AB",
    "MP1c": "#FFD700", "M1m": "#FFC107", "M1c": "#FFB300", "PPl1l": "#FFCA28",
    "E1m": "#FF8F00", "Eo1c": "#FFA726",
    "Ki2c": "#66BB6A", "Kia2": "#4CAF50", "JK3": "#81C784",
    "Ki1m": "#26A69A", "Ks1c": "#009688",
    "Kiag": "#F48FB1", "Kibg": "#F06292", "Ksg": "#EC407A",
    "J3i": "#388E3C", "J3m": "#2E7D32",
    "Jig": "#CE93D8", "Jsg": "#AB47BC", "Jmg": "#BA68C8",
    "TrJ1c": "#7E57C2", "Tr1c": "#9575CD", "Tr1m": "#B39DDB",
    "DC4": "#5C6BC0", "Pz3i": "#7986CB", "Pz4i": "#9FA8DA", "CO3": "#3F51B5",
    "PE1m": "#B71C1C",
}

_COMP_PALETTES = {
    "Secuencias sedimentarias":    ["#F5DEB3", "#D4A574", "#C8A96E", "#BFA05A", "#E8D5A3"],
    "Rocas intrusivas":            ["#F48FB1", "#CE93D8", "#AB47BC", "#E91E63", "#BA68C8"],
    "Secuencias volcanicas":       ["#81C784", "#66BB6A", "#4CAF50", "#388E3C", "#A5D6A7"],
    "Rocas metamorficas":          ["#5C6BC0", "#7986CB", "#3F51B5", "#3949AB", "#9FA8DA"],
    "Secuencias volcanosedimenta": ["#26A69A", "#4DB6AC", "#009688", "#00897B", "#80CBC4"],
    "Depositos no consolidados":   ["#FFFACD", "#FAF0BE", "#FFF8DC", "#FAEBD7", "#FFF3E0"],
    "S I":                         ["#FF69B4", "#FF6EB4", "#FF82AB", "#FFB6C1", "#FFC0CB"],
    "Sin Informacion":             ["#9E9E9E", "#BDBDBD", "#757575", "#E0E0E0", "#EEEEEE"],
}

_auto_color_map: dict = {}
_auto_color_counters: dict = {}


def _get_litho_color(geo_code: str, composicion: str) -> str:
    if geo_code in _LITHO_COLORS:
        return _LITHO_COLORS[geo_code]
    if geo_code in _auto_color_map:
        return _auto_color_map[geo_code]
    palette = _COMP_PALETTES.get(composicion, _COMP_PALETTES.get("Sin Informacion"))
    if palette:
        counter = _auto_color_counters.get(composicion, 0)
        color = palette[counter % len(palette)]
        h = int(hashlib.md5(geo_code.encode()).hexdigest()[:6], 16)
        r = max(0, min(255, int(color[1:3], 16) + (h % 40) - 20))
        g = max(0, min(255, int(color[3:5], 16) + ((h >> 8) % 40) - 20))
        b = max(0, min(255, int(color[5:7], 16) + ((h >> 16) % 40) - 20))
        color = f"#{r:02x}{g:02x}{b:02x}"
        _auto_color_map[geo_code] = color
        _auto_color_counters[composicion] = counter + 1
        return color
    h = int(hashlib.md5(geo_code.encode()).hexdigest()[:6], 16)
    color = f"#{h:06x}"
    _auto_color_map[geo_code] = color
    return color


# ── Data loading & indexing ────────────────────────────────────────────

def _load_raw_geojson() -> dict:
    """Load or convert the raw GeoJSON (full resolution)."""
    global _raw_geojson_cache
    if _raw_geojson_cache is not None:
        return _raw_geojson_cache

    if os.path.exists(_CACHE_PATH):
        print("[GEOLOGY] Loading raw GeoJSON cache (full res)...")
        t0 = time.time()
        with open(_CACHE_PATH, 'r') as f:
            _raw_geojson_cache = json.load(f)
        print(f"[GEOLOGY] Loaded {len(_raw_geojson_cache.get('features', []))} raw features in {time.time()-t0:.1f}s")
        return _raw_geojson_cache
    else:
        print("[GEOLOGY] Converting shapefile...")
        _raw_geojson_cache = _convert_shapefile()
        try:
            with open(_CACHE_PATH, 'w') as f:
                json.dump(_raw_geojson_cache, f)
        except Exception:
            pass
        return _raw_geojson_cache


def _build_optimized_cache() -> list:
    """Build cache with BOTH simplified and full-res coordinates."""

    if os.path.exists(_OPTIMIZED_CACHE_PATH):
        print("[GEOLOGY] Loading optimized v2 cache...")
        t0 = time.time()
        with open(_OPTIMIZED_CACHE_PATH, 'r') as f:
            features = json.load(f)
        print(f"[GEOLOGY] Loaded {len(features)} features in {time.time()-t0:.1f}s")
        return features

    raw = _load_raw_geojson()

    print("[GEOLOGY] Building optimized v2 cache (simplify + bbox + full coords)...")
    t0 = time.time()
    tolerance = 0.003  # ~300m at Chilean latitudes
    features = []

    for feat in raw["features"]:
        coords = feat["geometry"]["coordinates"]
        simplified = _simplify_polygon(coords, tolerance)
        bbox = _compute_bbox(coords)  # use full-res bbox for accuracy

        props = feat["properties"]
        geo_code = props.get("geo", "?")
        composicion = props.get("composicio", "")
        color = _get_litho_color(geo_code, composicion)

        features.append({
            "bbox": bbox,
            "coords_simple": simplified,
            "coords_full": coords,
            "props": props,
            "color": color,
        })

    orig_verts = sum(sum(len(r) for r in f["coords_full"]) for f in features)
    simp_verts = sum(sum(len(r) for r in f["coords_simple"]) for f in features)
    print(f"[GEOLOGY] Vertices: full={orig_verts}, simplified={simp_verts} ({100*(1-simp_verts/orig_verts):.0f}% reduction)")

    try:
        with open(_OPTIMIZED_CACHE_PATH, 'w') as f:
            json.dump(features, f)
        fsize = os.path.getsize(_OPTIMIZED_CACHE_PATH) / 1024 / 1024
        print(f"[GEOLOGY] v2 cache saved ({fsize:.1f} MB) in {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"[GEOLOGY] Warning: Could not save cache: {e}")

    return features


def _build_rtree(features: list):
    from rtree import index
    idx = index.Index()
    for i, feat in enumerate(features):
        idx.insert(i, feat["bbox"])
    return idx


def _ensure_loaded():
    global _features_cache, _rtree_index
    if _features_cache is not None and _rtree_index is not None:
        return

    t0 = time.time()
    _features_cache = _build_optimized_cache()
    print(f"[GEOLOGY] Building R-tree index for {len(_features_cache)} features...")
    _rtree_index = _build_rtree(_features_cache)
    print(f"[GEOLOGY] Ready in {time.time()-t0:.1f}s total")


def _convert_shapefile() -> dict:
    try:
        import shapefile
    except ImportError:
        raise HTTPException(status_code=500, detail="pyshp not installed")

    if not os.path.exists(_SHAPEFILE_PATH + '.shp'):
        raise HTTPException(status_code=404, detail="Shapefile not found")

    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True)

    sf = shapefile.Reader(_SHAPEFILE_PATH)
    fields = [f[0] for f in sf.fields[1:]]
    t0 = time.time()

    features = []
    for i, sr in enumerate(sf.iterShapeRecords()):
        shape = sr.shape
        rec = sr.record
        if shape.shapeType == 0:
            continue

        props = {}
        for fn, val in zip(fields, rec):
            if isinstance(val, bytes):
                val = val.decode('latin-1', errors='replace')
            props[fn] = val

        try:
            if not hasattr(shape, 'parts') or not shape.points:
                continue
            parts_idx = list(shape.parts) + [len(shape.points)]
            rings = []
            for pi in range(len(parts_idx) - 1):
                pts = shape.points[parts_idx[pi]:parts_idx[pi + 1]]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                lons, lats = transformer.transform(xs, ys)
                ring = [[round(lon, 5), round(lat, 5)] for lon, lat in zip(lons, lats)]
                if ring and ring[0] != ring[-1]:
                    ring.append(ring[0])
                rings.append(ring)
            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": rings},
                "properties": props,
            })
        except Exception:
            continue

        if (i + 1) % 5000 == 0:
            print(f"[GEOLOGY] Processed {i + 1} features ({time.time()-t0:.1f}s)...")

    print(f"[GEOLOGY] Converted {len(features)} features in {time.time()-t0:.1f}s")
    return {"type": "FeatureCollection", "features": features}


# ── API Endpoints ──────────────────────────────────────────────────────

@router.get("/features")
async def get_geology_features(
    bbox: str = Query(..., description="minx,miny,maxx,maxy in EPSG:4326"),
    limit: int = Query(5000, description="Max features to return"),
    simplify: bool = Query(True, description="Use simplified geometry (faster) or full resolution"),
):
    """Return geological features within the bounding box.

    Args:
        simplify: True = fast mode with simplified geometry,
                  False = full resolution for detailed zoom views.
    """
    try:
        parts = [float(p.strip()) for p in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError()
        minx, miny, maxx, maxy = parts
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid bbox format")

    t0 = time.time()
    _ensure_loaded()
    load_time = time.time() - t0

    # R-tree spatial query
    t1 = time.time()
    candidate_ids = list(_rtree_index.intersection((minx, miny, maxx, maxy)))
    query_time = time.time() - t1

    coord_key = "coords_simple" if simplify else "coords_full"

    features_out = []
    legend_entries = {}

    for idx in candidate_ids:
        if len(features_out) >= limit:
            break

        feat = _features_cache[idx]
        props = feat["props"]
        geo_code = props.get("geo", "?")
        color = feat["color"]

        if geo_code not in legend_entries:
            legend_entries[geo_code] = {
                "color": color,
                "geo": geo_code,
                "composicion": props.get("composicio", ""),
                "epoca": props.get("epoca", ""),
                "era": props.get("era", ""),
                "periodo": props.get("periodo", ""),
                "count": 0,
            }
        legend_entries[geo_code]["count"] += 1

        features_out.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": feat[coord_key]},
            "properties": {**props, "_color": color},
        })

    # Sort legend
    era_order = {"CENOZOICO": 0, "MEZOZOICO": 1, "PALEOZOICO": 2, "PRECAMBRICO": 3, "S I": 4, "Sin Informacion": 5}
    sorted_legend = sorted(
        legend_entries.values(),
        key=lambda x: (era_order.get(x["era"], 9), x["geo"])
    )

    total_time = time.time() - t0
    mode = "simplified" if simplify else "FULL-RES"
    print(f"[GEOLOGY] Query ({mode}): {len(candidate_ids)} candidates, "
          f"{len(features_out)} returned in {total_time*1000:.0f}ms "
          f"(rtree={query_time*1000:.0f}ms)")

    return {
        "type": "FeatureCollection",
        "features": features_out,
        "total": len(features_out),
        "legend": sorted_legend,
        "simplified": simplify,
        "timing": {
            "total_ms": round(total_time * 1000),
            "query_ms": round(query_time * 1000),
            "candidates": len(candidate_ids),
        },
    }


@router.get("/stats")
async def get_geology_stats():
    _ensure_loaded()
    features = _features_cache

    eras, periodos, composiciones = {}, {}, {}
    for feat in features:
        p = feat["props"]
        era = p.get("era", "Desconocido")
        periodo = p.get("periodo", "Desconocido")
        comp = p.get("composicio", "Desconocido")
        eras[era] = eras.get(era, 0) + 1
        periodos[periodo] = periodos.get(periodo, 0) + 1
        composiciones[comp] = composiciones.get(comp, 0) + 1

    return {
        "total_features": len(features),
        "eras": dict(sorted(eras.items(), key=lambda x: -x[1])),
        "periodos": dict(sorted(periodos.items(), key=lambda x: -x[1])),
        "composiciones": dict(sorted(composiciones.items(), key=lambda x: -x[1])),
    }
