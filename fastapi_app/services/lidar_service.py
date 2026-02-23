"""LiDAR file management — upload, list, delete GeoTIFF files.

Uploaded GeoTIFFs are stored in ``fastapi_app/data/lidar/`` and are used
by the DEM service when they cover the requested bounding box.
"""

import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()

_LIDAR_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'lidar')
os.makedirs(_LIDAR_DIR, exist_ok=True)

# Accepted extensions
_ALLOWED_EXT = {'.tif', '.tiff', '.geotiff'}
_MAX_SIZE_MB = 500  # Max upload size


def _lidar_dir() -> str:
    return _LIDAR_DIR


def list_lidar_files() -> List[dict]:
    """Return metadata for all uploaded LiDAR files."""
    files = []
    for fname in sorted(os.listdir(_LIDAR_DIR)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in _ALLOWED_EXT:
            fpath = os.path.join(_LIDAR_DIR, fname)
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            files.append({
                "filename": fname,
                "size_mb": round(size_mb, 2),
                "path": fpath,
            })
    return files


def find_lidar_for_bbox(bbox_tuple: tuple) -> Optional[str]:
    """Return path to a LiDAR GeoTIFF that covers the given bbox, or None.

    Uses rasterio to check if the GeoTIFF extent intersects the bbox.
    Returns the first matching file (highest resolution if multiple match).
    """
    try:
        import rasterio
    except ImportError:
        return None

    minx, miny, maxx, maxy = bbox_tuple
    for info in list_lidar_files():
        try:
            with rasterio.open(info["path"]) as ds:
                left, bottom, right, top = ds.bounds
                # Check overlap
                if left <= maxx and right >= minx and bottom <= maxy and top >= miny:
                    return info["path"]
        except Exception:
            continue
    return None


def sample_lidar_elevations(filepath: str, points: list) -> Optional[list]:
    """Sample elevation values from a GeoTIFF at the given lat/lon points.

    Returns a list of elevation floats, or None if sampling fails.
    """
    try:
        import rasterio
    except ImportError:
        return None

    try:
        elevations = []
        with rasterio.open(filepath) as ds:
            band = ds.read(1)
            for pt in points:
                lon, lat = pt["longitude"], pt["latitude"]
                # Transform geographic coords to pixel coords
                row, col = ds.index(lon, lat)
                if 0 <= row < band.shape[0] and 0 <= col < band.shape[1]:
                    val = float(band[row, col])
                    # Handle nodata
                    if ds.nodata is not None and val == ds.nodata:
                        elevations.append(0.0)
                    else:
                        elevations.append(val)
                else:
                    elevations.append(0.0)
        return elevations
    except Exception as e:
        print(f"[LIDAR] Sampling failed: {e}")
        return None


# ── API ENDPOINTS ─────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_lidar(file: UploadFile = File(...)):
    """Upload a GeoTIFF LiDAR/DEM file.

    Accepted formats: .tif, .tiff
    Max size: 500 MB
    """
    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {ext}. Use .tif o .tiff (GeoTIFF)"
        )

    # Save to disk
    dest = os.path.join(_LIDAR_DIR, file.filename)
    try:
        with open(dest, 'wb') as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo: {e}")

    size_mb = os.path.getsize(dest) / (1024 * 1024)
    if size_mb > _MAX_SIZE_MB:
        os.remove(dest)
        raise HTTPException(
            status_code=413,
            detail=f"Archivo muy grande: {size_mb:.1f} MB. Máximo: {_MAX_SIZE_MB} MB"
        )

    # Try to read metadata with rasterio
    metadata = {"filename": file.filename, "size_mb": round(size_mb, 2)}
    try:
        import rasterio
        with rasterio.open(dest) as ds:
            metadata.update({
                "crs": str(ds.crs),
                "bounds": {
                    "west": ds.bounds.left,
                    "south": ds.bounds.bottom,
                    "east": ds.bounds.right,
                    "north": ds.bounds.top,
                },
                "resolution": {
                    "x": abs(ds.res[0]),
                    "y": abs(ds.res[1]),
                },
                "width": ds.width,
                "height": ds.height,
            })
    except ImportError:
        metadata["warning"] = "rasterio no instalado — no se pudo leer metadata"
    except Exception as e:
        metadata["warning"] = f"No se pudo leer metadata: {e}"

    return {
        "message": f"Archivo '{file.filename}' cargado exitosamente",
        "file": metadata,
    }


@router.get("/lidar/list")
async def get_lidar_files():
    """List all uploaded LiDAR files."""
    files = list_lidar_files()

    # Enrich with rasterio metadata if available
    try:
        import rasterio
        for info in files:
            try:
                with rasterio.open(info["path"]) as ds:
                    info["crs"] = str(ds.crs)
                    info["bounds"] = {
                        "west": ds.bounds.left,
                        "south": ds.bounds.bottom,
                        "east": ds.bounds.right,
                        "north": ds.bounds.top,
                    }
                    info["resolution_m"] = round(abs(ds.res[0]) * 111320, 1)
            except Exception:
                pass
    except ImportError:
        pass

    return {"files": files, "count": len(files)}


@router.delete("/lidar/{filename}")
async def delete_lidar(filename: str):
    """Delete an uploaded LiDAR file."""
    fpath = os.path.join(_LIDAR_DIR, filename)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"Archivo '{filename}' no encontrado")

    os.remove(fpath)
    return {"message": f"Archivo '{filename}' eliminado", "filename": filename}
