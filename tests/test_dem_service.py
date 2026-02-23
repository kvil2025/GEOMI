import pytest
from fastapi.testclient import TestClient
from fastapi_app.main import app

client = TestClient(app)


def test_get_slope_success():
    """Verify the slope endpoint returns elevations, slopes, and stats."""
    bbox = "-71.5,-33.0,-71.0,-32.5"
    response = client.get(f"/dem/slope?bbox={bbox}&resolution=5")
    assert response.status_code == 200
    data = response.json()
    assert "slopes" in data
    assert "elevations" in data
    assert "stats" in data
    assert isinstance(data["slopes"], list)
    assert isinstance(data["elevations"], list)
    assert len(data["slopes"]) == 5  # 5×5 grid
    assert len(data["slopes"][0]) == 5
    assert data["stats"]["min_slope"] >= 0


def test_get_slope_bad_bbox():
    """Invalid bbox should return 400."""
    response = client.get("/dem/slope?bbox=invalid")
    assert response.status_code == 400
