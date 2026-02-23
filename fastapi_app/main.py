import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (same dir as this package's parent)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .services.wfs_client import router as wfs_router
from .services.dem_service import router as dem_router
from .services.lidar_service import router as lidar_router
from .services.intersection_service import router as intersect_router
from .services.elevation_profile import router as profile_router

app = FastAPI(title="Mining Intelligence Dashboard Backend", version="0.1.0")

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wfs_router, prefix="/wfs", tags=["WFS"])
app.include_router(dem_router, prefix="/dem", tags=["DEM"])
app.include_router(lidar_router, prefix="/dem", tags=["LiDAR"])
app.include_router(intersect_router, prefix="/intersection", tags=["Intersection"])
app.include_router(profile_router, prefix="/profile", tags=["Elevation Profile"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
