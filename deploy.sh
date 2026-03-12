#!/bin/bash
# ============================================================
# GeologgIA Map — Deploy Script for Google Cloud Run
# ============================================================
# Uso: ./deploy.sh [PROJECT_ID]
# Si no se especifica PROJECT_ID, usa 'botboletas'
# ============================================================

set -e

PROJECT_ID="${1:-botboletas}"
SERVICE_NAME="geologgia-map"
REGION="us-central1"

echo "🌍 GeologgIA Map — Deploy to Cloud Run"
echo "========================================"
echo "  Proyecto:  $PROJECT_ID"
echo "  Servicio:  $SERVICE_NAME"
echo "  Región:    $REGION"
echo ""

# 1. Verificar autenticación
echo "🔑 Verificando autenticación de gcloud..."
gcloud auth print-identity-token > /dev/null 2>&1 || {
    echo "❌ No estás autenticado. Ejecuta: gcloud auth login"
    exit 1
}
echo "✅ Autenticado"

# 2. Configurar proyecto
echo "📁 Configurando proyecto $PROJECT_ID..."
gcloud config set project "$PROJECT_ID" --quiet

# 3. Habilitar APIs necesarias
echo "🔧 Habilitando APIs necesarias..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project="$PROJECT_ID" --quiet 2>/dev/null || true

# 4. Deploy con Cloud Build (buildea en la nube, no necesita Docker local)
echo ""
echo "🚀 Iniciando deploy a Cloud Run..."
echo "   (esto puede tomar 3-5 minutos)"
echo ""
gcloud run deploy "$SERVICE_NAME" \
    --source=. \
    --region="$REGION" \
    --allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --set-env-vars="ALLOWED_EMAILS=cavila@geologgia.cl" \
    --project="$PROJECT_ID" \
    --quiet

# 5. Obtener la URL
echo ""
echo "✅ Deploy exitoso!"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(status.url)" 2>/dev/null)

echo ""
echo "🌐 URL: $SERVICE_URL"
echo ""
echo "========================================"
echo "🎉 ¡GeologgIA Map está en producción!"
echo "========================================"
