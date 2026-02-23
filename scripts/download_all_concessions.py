#!/usr/bin/env python3
"""
Descarga completa de concesiones mineras desde SERNAGEOMIN ArcGIS FeatureServer.
Total estimado: 106,402 registros (con centroides, sin geometría completa).

Uso:
    python scripts/download_all_concessions.py
    python scripts/download_all_concessions.py --limit 100   # solo 100 registros (test)
    python scripts/download_all_concessions.py --resume       # retomar descarga interrumpida
"""

import json
import os
import sys
import time
import argparse
import requests
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────
ARCGIS_URL = (
    "https://services1.arcgis.com/OyjvVdFTl5hfSdX3"
    "/ArcGIS/rest/services/Marcelo_Layer/FeatureServer/2/query"
)

# Todos los campos tabulares disponibles (sin geometría)
ALL_FIELDS = ",".join([
    "OBJECTID", "NUMERO_ROL", "DV_ROL", "NOMBRE", "HECTAREAS",
    "FECHA_VENCIMIENTO", "ESTACAMENTO_SALITRERO", "SITUACION_CONCESION",
    "TIPO_CONCESION", "DATUM", "HUSO", "COMUNA",
    "ID_SITUACION_CONCESION", "ID_TIPO_CONCESION",
    "TITULAR_DIVISION", "TITULAR_NOMBRE", "TITULAR_RUT", "TITULAR_DV",
    "ID_CONCESION", "NRO_INSCRIPCION", "FOJAS", "ANO_INSCRIPCION",
    "ORIGEN", "FECHA_CREACION", "FECHA_ACTUALIZACION",
    "ID_COMUNA", "DPA_COMUNA",
])

PAGE_SIZE = 2000  # Max allowed by the server
MAX_RETRIES = 5
BASE_DELAY = 2  # seconds

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'concesiones_completas.json')
PROGRESS_FILE = os.path.join(DATA_DIR, 'download_progress.json')


def get_total_count():
    """Get total number of records available."""
    params = {
        "where": "1=1",
        "returnCountOnly": "true",
        "f": "json",
    }
    resp = requests.get(ARCGIS_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["count"]


def compute_centroid(geometry):
    """Compute centroid from a GeoJSON polygon/multipolygon geometry."""
    if not geometry:
        return None, None

    geom_type = geometry.get("type", "")
    rings = geometry.get("coordinates", [])

    if not rings:
        return None, None

    all_points = []
    if geom_type == "Polygon":
        # Use outer ring (first ring)
        all_points = rings[0] if rings else []
    elif geom_type == "MultiPolygon":
        # Collect points from all outer rings
        for polygon in rings:
            if polygon:
                all_points.extend(polygon[0])
    else:
        return None, None

    if not all_points:
        return None, None

    n = len(all_points)
    cx = sum(p[0] for p in all_points) / n  # longitude
    cy = sum(p[1] for p in all_points) / n  # latitude
    return round(cy, 6), round(cx, 6)  # lat, lng


def fetch_page(offset: int, page_size: int = PAGE_SIZE) -> list:
    """Fetch a page of records with geometry, compute centroids, discard polygons."""
    params = {
        "where": "1=1",
        "outFields": ALL_FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
        "orderByFields": "OBJECTID ASC",
        "resultOffset": offset,
        "resultRecordCount": page_size,
        "f": "geojson",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(ARCGIS_URL, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                raise Exception(f"API error: {data['error']}")

            features = data.get("features", [])
            results = []
            for f in features:
                attrs = f.get("properties", {})
                # Compute centroid from geometry
                lat, lng = compute_centroid(f.get("geometry"))
                attrs["CENTROID_LAT"] = lat
                attrs["CENTROID_LNG"] = lng
                results.append(attrs)
            return results

        except Exception as e:
            delay = BASE_DELAY * (2 ** (attempt - 1))
            print(f"  ⚠ Intento {attempt}/{MAX_RETRIES} falló: {e}")
            if attempt < MAX_RETRIES:
                print(f"    Reintentando en {delay}s...")
                time.sleep(delay)
            else:
                raise Exception(f"Falló después de {MAX_RETRIES} intentos: {e}")


def save_progress(offset: int, records: list):
    """Save progress for resume capability."""
    progress = {
        "last_offset": offset,
        "records_downloaded": len(records),
        "timestamp": datetime.now().isoformat(),
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)


def load_progress():
    """Load progress from previous run."""
    if not os.path.exists(PROGRESS_FILE):
        return None
    with open(PROGRESS_FILE, 'r') as f:
        return json.load(f)


def load_existing_records():
    """Load previously downloaded records."""
    if not os.path.exists(OUTPUT_FILE):
        return []
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def download_all(limit: int = None, resume: bool = False):
    """Download all concessions from SERNAGEOMIN."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Get total count
    print("🔍 Consultando total de registros...")
    total = get_total_count()
    print(f"📊 Total disponible: {total:,} concesiones")

    if limit:
        total = min(total, limit)
        print(f"⚡ Limitado a {total:,} registros")

    # Resume logic
    all_records = []
    start_offset = 0

    if resume:
        progress = load_progress()
        if progress:
            all_records = load_existing_records()
            start_offset = progress["last_offset"] + PAGE_SIZE
            print(f"🔄 Retomando desde offset {start_offset} ({len(all_records):,} registros previos)")

    # Calculate batches
    remaining = total - start_offset
    total_batches = (remaining + PAGE_SIZE - 1) // PAGE_SIZE
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"📥 DESCARGA DE CONCESIONES MINERAS - SERNAGEOMIN")
    print(f"{'='*60}")
    print(f"  Registros: {total:,}")
    print(f"  Tamaño de página: {PAGE_SIZE:,}")
    print(f"  Batches estimados: {total_batches}")
    print(f"  Centroides: ✅ (sin geometría completa)")
    print(f"{'='*60}\n")

    batch_num = 0
    offset = start_offset

    while offset < total:
        batch_num += 1
        page_size = min(PAGE_SIZE, total - offset) if limit else PAGE_SIZE

        # Progress bar
        pct = (offset / total) * 100
        elapsed = time.time() - start_time
        if batch_num > 1:
            eta = (elapsed / batch_num) * (total_batches - batch_num)
            eta_str = f" | ETA: {int(eta//60)}m{int(eta%60)}s"
        else:
            eta_str = ""

        print(f"  Batch {batch_num}/{total_batches} | Offset {offset:,}/{total:,} ({pct:.1f}%){eta_str}", end="")

        records = fetch_page(offset, page_size)

        if not records:
            print(" → Sin más datos")
            break

        all_records.extend(records)
        print(f" → {len(records):,} registros (total: {len(all_records):,})")

        # Save progress every 5 batches
        if batch_num % 5 == 0:
            save_progress(offset, all_records)
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_records, f, ensure_ascii=False)
            print(f"  💾 Guardado intermedio ({len(all_records):,} registros)")

        offset += PAGE_SIZE

        # Brief pause to be nice to the server
        time.sleep(0.5)

    # Final save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False)

    # Cleanup progress file
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"✅ DESCARGA COMPLETADA")
    print(f"{'='*60}")
    print(f"  Total registros: {len(all_records):,}")
    print(f"  Archivo: {OUTPUT_FILE}")
    print(f"  Tamaño: {os.path.getsize(OUTPUT_FILE) / (1024*1024):.1f} MB")
    print(f"  Tiempo: {int(elapsed//60)}m {int(elapsed%60)}s")
    print(f"{'='*60}")

    return all_records


def main():
    parser = argparse.ArgumentParser(description="Descargar concesiones mineras de SERNAGEOMIN")
    parser.add_argument("--limit", type=int, help="Limitar a N registros (para testing)")
    parser.add_argument("--resume", action="store_true", help="Retomar descarga interrumpida")
    args = parser.parse_args()

    try:
        records = download_all(limit=args.limit, resume=args.resume)
        print(f"\n🎉 {len(records):,} concesiones descargadas exitosamente")
    except KeyboardInterrupt:
        print("\n\n⏸ Descarga pausada. Usa --resume para continuar.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Usa --resume para reintentar desde el último punto guardado.")
        sys.exit(1)


if __name__ == "__main__":
    main()
