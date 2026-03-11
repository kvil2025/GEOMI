"""Shapefile Import/Export Service.

Endpoints:
  POST /shapefile/upload  – Upload a .shp + related files, convert to GeoJSON for display
  POST /shapefile/export  – Export GeoJSON features to a downloadable Shapefile (.zip)
"""

import os
import io
import json
import time
import zipfile
import tempfile
import shutil
from typing import Optional, List

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'geodata', 'uploads')
os.makedirs(_UPLOAD_DIR, exist_ok=True)


# ── Upload & Convert Shapefile ────────────────────────────────────────

@router.post("/upload")
async def upload_shapefile(
    files: List[UploadFile] = File(..., description="Upload .shp, .shx, .dbf (and optionally .prj, .cpg)"),
):
    """Upload a shapefile bundle and convert to GeoJSON.

    The user should upload at least .shp, .shx, .dbf files together.
    Optionally also .prj (projection) and .cpg (encoding).
    """
    try:
        import shapefile as pyshp
    except ImportError:
        raise HTTPException(status_code=500, detail="pyshp not installed")

    # Save uploaded files to temp dir
    tmpdir = tempfile.mkdtemp(prefix="shp_upload_")
    saved_files = {}
    shp_basename = None

    try:
        for f in files:
            fname = f.filename
            ext = os.path.splitext(fname)[1].lower()
            base = os.path.splitext(fname)[0]

            if shp_basename is None:
                shp_basename = base

            dest = os.path.join(tmpdir, fname)
            content = await f.read()
            with open(dest, 'wb') as out:
                out.write(content)
            saved_files[ext] = dest

        if '.shp' not in saved_files:
            raise HTTPException(status_code=400, detail="Missing .shp file")
        if '.dbf' not in saved_files:
            raise HTTPException(status_code=400, detail="Missing .dbf file")

        shp_path = saved_files['.shp'].replace('.shp', '')

        # Detect projection
        transformer = None
        prj_path = saved_files.get('.prj')
        if prj_path and os.path.exists(prj_path):
            with open(prj_path, 'r') as pf:
                prj_text = pf.read()
            # Check if it's NOT WGS84
            if 'GEOGCS' not in prj_text or 'GCS_WGS_1984' not in prj_text:
                try:
                    from pyproj import CRS, Transformer
                    src_crs = CRS.from_wkt(prj_text)
                    if src_crs.to_epsg() != 4326:
                        transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
                except Exception:
                    pass

        # Read shapefile
        t0 = time.time()
        sf = pyshp.Reader(shp_path)
        fields = [f[0] for f in sf.fields[1:]]

        shape_type = sf.shapeType
        # 1=Point, 3=PolyLine, 5=Polygon, 8=MultiPoint, 11=PointZ, 13=PolyLineZ, 15=PolygonZ
        geom_type_map = {
            1: "Point", 3: "LineString", 5: "Polygon",
            8: "MultiPoint", 11: "Point", 13: "LineString",
            15: "Polygon", 25: "Polygon", 23: "LineString",
        }
        geom_type = geom_type_map.get(shape_type, "Polygon")

        features = []
        for sr in sf.iterShapeRecords():
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
                points = shape.points
                if transformer:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    lons, lats = transformer.transform(xs, ys)
                    points = list(zip(lons, lats))

                if geom_type == "Point":
                    coords = [round(points[0][0], 6), round(points[0][1], 6)]
                    geometry = {"type": "Point", "coordinates": coords}

                elif geom_type == "LineString":
                    if hasattr(shape, 'parts') and len(shape.parts) > 1:
                        parts_idx = list(shape.parts) + [len(points)]
                        lines = []
                        for pi in range(len(parts_idx) - 1):
                            line = [[round(p[0], 6), round(p[1], 6)]
                                    for p in points[parts_idx[pi]:parts_idx[pi + 1]]]
                            lines.append(line)
                        geometry = {"type": "MultiLineString", "coordinates": lines}
                    else:
                        coords = [[round(p[0], 6), round(p[1], 6)] for p in points]
                        geometry = {"type": "LineString", "coordinates": coords}

                elif geom_type == "Polygon":
                    if hasattr(shape, 'parts'):
                        parts_idx = list(shape.parts) + [len(points)]
                        rings = []
                        for pi in range(len(parts_idx) - 1):
                            ring = [[round(p[0], 6), round(p[1], 6)]
                                    for p in points[parts_idx[pi]:parts_idx[pi + 1]]]
                            if ring and ring[0] != ring[-1]:
                                ring.append(ring[0])
                            rings.append(ring)
                        geometry = {"type": "Polygon", "coordinates": rings}
                    else:
                        coords = [[round(p[0], 6), round(p[1], 6)] for p in points]
                        if coords and coords[0] != coords[-1]:
                            coords.append(coords[0])
                        geometry = {"type": "Polygon", "coordinates": [coords]}
                else:
                    continue

                features.append({
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": props,
                })
            except Exception:
                continue

        elapsed = time.time() - t0

        # Determine a default color based on geometry type
        default_style = {}
        if geom_type in ("LineString", "MultiLineString"):
            default_style = {"stroke": "#ff4444", "stroke-width": 2, "stroke-dasharray": "8,4"}
        elif geom_type == "Point":
            default_style = {"marker-color": "#ff6600", "marker-size": "small"}
        else:
            default_style = {"fill": "#44aaff", "fill-opacity": 0.3, "stroke": "#2288dd", "stroke-width": 1}

        geojson = {
            "type": "FeatureCollection",
            "features": features,
        }

        return {
            "geojson": geojson,
            "name": shp_basename or "shapefile",
            "feature_count": len(features),
            "geometry_type": geom_type,
            "fields": fields,
            "style": default_style,
            "elapsed_ms": round(elapsed * 1000),
        }

    finally:
        # Clean up temp files
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass


# ── Export GeoJSON to Shapefile ────────────────────────────────────────

class ExportRequest(BaseModel):
    geojson: dict
    filename: Optional[str] = "export"


@router.post("/export")
async def export_shapefile(req: ExportRequest):
    """Convert GeoJSON to a downloadable Shapefile (.zip).

    The zip contains .shp, .shx, .dbf, .prj files.
    """
    try:
        import shapefile as pyshp
    except ImportError:
        raise HTTPException(status_code=500, detail="pyshp not installed")

    features = req.geojson.get("features", [])
    if not features:
        raise HTTPException(status_code=400, detail="No features to export")

    # Detect geometry type from first feature
    first_geom = features[0].get("geometry", {})
    geom_type = first_geom.get("type", "Polygon")

    # Map GeoJSON type to pyshp type
    shp_type_map = {
        "Point": pyshp.POINT,
        "MultiPoint": pyshp.MULTIPOINT,
        "LineString": pyshp.POLYLINE,
        "MultiLineString": pyshp.POLYLINE,
        "Polygon": pyshp.POLYGON,
        "MultiPolygon": pyshp.POLYGON,
    }
    shp_type = shp_type_map.get(geom_type, pyshp.POLYGON)

    # Collect all property keys
    all_keys = set()
    for feat in features:
        all_keys.update(feat.get("properties", {}).keys())
    # Filter out internal keys
    all_keys = [k for k in sorted(all_keys) if not k.startswith('_')]

    tmpdir = tempfile.mkdtemp(prefix="shp_export_")
    shp_path = os.path.join(tmpdir, req.filename)

    try:
        w = pyshp.Writer(shp_path, shapeType=shp_type)

        # Define fields
        for key in all_keys:
            # Determine field type by sampling values
            sample_vals = [f.get("properties", {}).get(key) for f in features[:100] if f.get("properties", {}).get(key) is not None]
            if sample_vals and all(isinstance(v, (int, float)) for v in sample_vals):
                if all(isinstance(v, int) for v in sample_vals):
                    w.field(key[:10], 'N', 20, 0)
                else:
                    w.field(key[:10], 'N', 20, 6)
            else:
                w.field(key[:10], 'C', 254)

        # Write features
        for feat in features:
            geom = feat.get("geometry", {})
            props = feat.get("properties", {})
            g_type = geom.get("type", "")
            coords = geom.get("coordinates", [])

            try:
                if g_type == "Point":
                    w.point(coords[0], coords[1])
                elif g_type == "LineString":
                    w.line([coords])
                elif g_type == "MultiLineString":
                    w.line(coords)
                elif g_type == "Polygon":
                    w.poly(coords)
                elif g_type == "MultiPolygon":
                    # Flatten multipolygon rings
                    all_rings = []
                    for polygon in coords:
                        all_rings.extend(polygon)
                    w.poly(all_rings)
                else:
                    continue

                # Write record
                record = []
                for key in all_keys:
                    val = props.get(key, "")
                    if val is None:
                        val = ""
                    record.append(val)
                w.record(*record)

            except Exception:
                continue

        w.close()

        # Write .prj (WGS84)
        prj_content = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
        with open(shp_path + '.prj', 'w') as pf:
            pf.write(prj_content)

        # Create zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for ext in ['.shp', '.shx', '.dbf', '.prj']:
                fpath = shp_path + ext
                if os.path.exists(fpath):
                    zf.write(fpath, f"{req.filename}{ext}")

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{req.filename}.zip"'
            },
        )

    finally:
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
