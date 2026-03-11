import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (same dir as this package's parent)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .services.wfs_client import router as wfs_router
from .services.dem_service import router as dem_router
from .services.lidar_service import router as lidar_router
from .services.intersection_service import router as intersect_router
from .services.elevation_profile import router as profile_router
from .services.geology_service import router as geology_router
from .services.shapefile_service import router as shapefile_router

app = FastAPI(title="GeologgIA Map API", version="2.0.0")

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Google Auth Verification -----
ALLOWED_EMAILS = [
    e.strip().lower()
    for e in os.getenv("ALLOWED_EMAILS", "").split(",")
    if e.strip()
]
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


@app.post("/auth/verify")
async def verify_google_token(request: Request):
    """Verify a Google ID token and check if the email is authorized."""
    try:
        body = await request.json()
        credential = body.get("credential", "")

        if not credential:
            raise HTTPException(status_code=400, detail="No credential provided")

        # Decode the JWT token (Google ID token)
        import json, base64
        # Split the JWT
        parts = credential.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail="Invalid token format")

        # Decode payload (part 2)
        payload = parts[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload))

        email = decoded.get("email", "").lower()
        name = decoded.get("name", "")
        picture = decoded.get("picture", "")

        # Check if email is in allowed list (if list is configured)
        if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
            return JSONResponse(
                status_code=403,
                content={
                    "authorized": False,
                    "email": email,
                    "message": f"El correo {email} no está autorizado. Contacta al administrador."
                }
            )

        return {
            "authorized": True,
            "email": email,
            "name": name,
            "picture": picture,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error verifying token: {str(e)}")


@app.get("/auth/config")
async def auth_config():
    """Return auth configuration for the frontend."""
    return {
        "googleClientId": GOOGLE_CLIENT_ID,
        "authRequired": bool(GOOGLE_CLIENT_ID and ALLOWED_EMAILS),
    }


# ----- API Routers -----
app.include_router(wfs_router, prefix="/wfs", tags=["WFS"])
app.include_router(dem_router, prefix="/dem", tags=["DEM"])
app.include_router(lidar_router, prefix="/dem", tags=["LiDAR"])
app.include_router(intersect_router, prefix="/intersection", tags=["Intersection"])
app.include_router(profile_router, prefix="/profile", tags=["Elevation Profile"])
app.include_router(geology_router, prefix="/geology", tags=["Geology"])
app.include_router(shapefile_router, prefix="/shapefile", tags=["Shapefile"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "GeologgIA Map", "version": "2.0.0"}


# ----- Serve Frontend Static Files (Production) -----
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _frontend_dist.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    # Catch-all route for SPA — must be LAST
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = _frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Return index.html for SPA routing
        return FileResponse(str(_frontend_dist / "index.html"))
