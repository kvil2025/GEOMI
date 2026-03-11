# ============================================================
# GeologgIA Map — Dockerfile Multi-Stage
# ============================================================
# Stage 1: Build frontend (React/Vite)
# Stage 2: Run backend (FastAPI) + serve frontend static files
# ============================================================

# --- Stage 1: Build Frontend ---
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Production ---
FROM python:3.11-slim AS production
WORKDIR /app

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt python-dotenv pyshp python-multipart

# Copy backend code
COPY fastapi_app/ ./fastapi_app/

# Copy geodata (geology shapefiles)
COPY geodata/ ./geodata/

# Copy built frontend from Stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Add static file serving to FastAPI
ENV PYTHONPATH=/app
ENV PORT=8080

# Expose port (Cloud Run uses 8080)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Start server
CMD ["python", "-m", "uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8080"]
