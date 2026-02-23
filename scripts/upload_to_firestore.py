#!/usr/bin/env python3
"""
Sube concesiones mineras descargadas a Firebase Firestore.

Uso:
    python scripts/upload_to_firestore.py
    python scripts/upload_to_firestore.py --limit 100         # subir solo 100 (test)
    python scripts/upload_to_firestore.py --count-only         # solo contar registros
    python scripts/upload_to_firestore.py --add-user email@x   # agregar usuario autorizado
    python scripts/upload_to_firestore.py --list-users         # listar autorizados
    python scripts/upload_to_firestore.py --remove-user email  # revocar acceso

Requiere:
    pip install firebase-admin
    Variable de entorno GOOGLE_APPLICATION_CREDENTIALS apuntando al service account JSON
    O bien, un archivo service_account.json en el directorio scripts/
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime

# ── FIREBASE SETUP ────────────────────────────────────────────────────────
import firebase_admin
from firebase_admin import credentials, firestore

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
INPUT_FILE = os.path.join(DATA_DIR, 'concesiones_completas.json')

# Look for service account in multiple locations
SA_PATHS = [
    os.path.join(os.path.dirname(__file__), 'service_account.json'),
    os.path.join(os.path.dirname(__file__), '..', 'service_account.json'),
    os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', ''),
]

COLLECTION_NAME = 'concesiones'
AUTHORIZED_COLLECTION = 'authorized_users'
BATCH_SIZE = 450  # Firestore max is 500, leave margin


def init_firebase():
    """Initialize Firebase Admin SDK."""
    if firebase_admin._apps:
        return firestore.client()

    cred_path = None
    for path in SA_PATHS:
        if path and os.path.exists(path):
            cred_path = path
            break

    if not cred_path:
        print("❌ No se encontró archivo de service account.")
        print("   Opciones:")
        print("   1. Coloca service_account.json en el directorio scripts/ o raíz del proyecto")
        print("   2. Configura GOOGLE_APPLICATION_CREDENTIALS=<ruta>")
        print("\n   Para obtener el archivo:")
        print("   → Firebase Console → Configuración del proyecto → Cuentas de servicio")
        print("   → Generar nueva clave privada")
        sys.exit(1)

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    print(f"✅ Firebase inicializado con: {os.path.basename(cred_path)}")
    return firestore.client()


def load_concessions(limit=None):
    """Load concessions from local JSON file."""
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Archivo no encontrado: {INPUT_FILE}")
        print("   Ejecuta primero: python scripts/download_all_concessions.py")
        sys.exit(1)

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if limit:
        data = data[:limit]

    print(f"📂 Cargados {len(data):,} registros desde archivo local")
    return data


def clean_record(record):
    """Clean and prepare a record for Firestore.
    Firestore doesn't accept None values well in queries, so we convert them.
    """
    cleaned = {}
    for key, value in record.items():
        # Convert None to empty string for string fields, 0 for numeric
        if value is None:
            if key in ('HECTAREAS', 'HUSO', 'ID_SITUACION_CONCESION',
                       'ID_TIPO_CONCESION', 'ID_COMUNA'):
                cleaned[key] = 0
            else:
                cleaned[key] = ''
        else:
            cleaned[key] = value

    # Add metadata
    cleaned['_uploaded_at'] = datetime.now().isoformat()

    return cleaned


def upload_concessions(db, records, limit=None):
    """Upload concessions to Firestore using batch writes."""
    total = len(records)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"📤 SUBIDA A FIRESTORE")
    print(f"{'='*60}")
    print(f"  Registros: {total:,}")
    print(f"  Colección: {COLLECTION_NAME}")
    print(f"  Tamaño de batch: {BATCH_SIZE}")
    print(f"  Batches estimados: {total_batches}")
    print(f"{'='*60}\n")

    uploaded = 0
    errors = 0

    for batch_num in range(total_batches):
        start_idx = batch_num * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, total)
        batch_records = records[start_idx:end_idx]

        batch = db.batch()

        for record in batch_records:
            # Use ID_CONCESION as document ID for deduplication
            doc_id = str(record.get('ID_CONCESION', record.get('OBJECTID', '')))
            if not doc_id:
                doc_id = str(record.get('OBJECTID', ''))

            doc_ref = db.collection(COLLECTION_NAME).document(doc_id)
            cleaned = clean_record(record)
            batch.set(doc_ref, cleaned)

        try:
            batch.commit()
            uploaded += len(batch_records)

            pct = (uploaded / total) * 100
            elapsed = time.time() - start_time
            if batch_num > 0:
                eta = (elapsed / (batch_num + 1)) * (total_batches - batch_num - 1)
                eta_str = f" | ETA: {int(eta//60)}m{int(eta%60)}s"
            else:
                eta_str = ""

            print(f"  Batch {batch_num+1}/{total_batches} | "
                  f"{uploaded:,}/{total:,} ({pct:.1f}%){eta_str}")

        except Exception as e:
            errors += len(batch_records)
            print(f"  ❌ Batch {batch_num+1} falló: {e}")

        # Small delay to avoid quota issues
        if batch_num % 10 == 9:
            time.sleep(0.5)

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"✅ SUBIDA COMPLETADA")
    print(f"{'='*60}")
    print(f"  Subidos: {uploaded:,}")
    print(f"  Errores: {errors:,}")
    print(f"  Tiempo: {int(elapsed//60)}m {int(elapsed%60)}s")
    print(f"{'='*60}")

    return uploaded, errors


def count_documents(db):
    """Count documents in the concesiones collection."""
    # Use aggregation if available, otherwise count manually
    try:
        collection_ref = db.collection(COLLECTION_NAME)
        # Get count using a limit approach
        docs = collection_ref.limit(1).get()
        if not docs:
            print(f"📊 Colección '{COLLECTION_NAME}': 0 documentos")
            return 0

        # For actual count, we need to stream
        print(f"📊 Contando documentos en '{COLLECTION_NAME}'...")
        count = 0
        for _ in collection_ref.stream():
            count += 1
            if count % 10000 == 0:
                print(f"  ... {count:,}")
        print(f"📊 Total: {count:,} documentos")
        return count
    except Exception as e:
        print(f"❌ Error contando: {e}")
        return -1


# ── ACCESS MANAGEMENT ─────────────────────────────────────────────────────

def add_user(db, email):
    """Add a user to the authorized list."""
    doc_ref = db.collection(AUTHORIZED_COLLECTION).document(email)
    doc_ref.set({
        'email': email,
        'authorized_at': datetime.now().isoformat(),
        'active': True,
    })
    print(f"✅ Usuario autorizado: {email}")


def remove_user(db, email):
    """Remove a user from the authorized list."""
    doc_ref = db.collection(AUTHORIZED_COLLECTION).document(email)
    doc_ref.delete()
    print(f"🚫 Acceso revocado: {email}")


def list_users(db):
    """List all authorized users."""
    docs = db.collection(AUTHORIZED_COLLECTION).stream()
    print(f"\n📋 Usuarios autorizados:")
    print(f"{'─'*50}")
    count = 0
    for doc in docs:
        data = doc.to_dict()
        status = "✅ Activo" if data.get('active', True) else "❌ Inactivo"
        print(f"  {data.get('email', doc.id)} | {status} | {data.get('authorized_at', 'N/A')}")
        count += 1
    if count == 0:
        print("  (vacío)")
    print(f"{'─'*50}")
    print(f"  Total: {count}")


# ── MAIN ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Subir concesiones mineras a Firebase Firestore")
    parser.add_argument("--limit", type=int, help="Limitar a N registros")
    parser.add_argument("--count-only", action="store_true", help="Solo contar registros en Firestore")
    parser.add_argument("--add-user", type=str, help="Agregar email autorizado")
    parser.add_argument("--remove-user", type=str, help="Revocar acceso de email")
    parser.add_argument("--list-users", action="store_true", help="Listar usuarios autorizados")
    args = parser.parse_args()

    db = init_firebase()

    if args.count_only:
        count_documents(db)
        return

    if args.add_user:
        add_user(db, args.add_user)
        return

    if args.remove_user:
        remove_user(db, args.remove_user)
        return

    if args.list_users:
        list_users(db)
        return

    # Default: upload concessions
    records = load_concessions(limit=args.limit)
    uploaded, errors = upload_concessions(db, records)

    if errors == 0:
        print(f"\n🎉 {uploaded:,} concesiones subidas exitosamente a Firestore")
    else:
        print(f"\n⚠ {uploaded:,} subidas, {errors:,} errores")


if __name__ == "__main__":
    main()
