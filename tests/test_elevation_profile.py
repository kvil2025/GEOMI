import pytest
from fastapi.testclient import TestClient
from fastapi_app.main import app

client = TestClient(app)


SAMPLE_LINE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-71.5, -33.0],
                    [-71.4, -32.9],
                    [-71.3, -32.8],
                ],
            },
            "properties": {},
        }
    ],
}


def test_elevation_profile_success():
    """POST a LineString and verify profile with distance and elevation data."""
    response = client.post("/profile/profile", json=SAMPLE_LINE)
    assert response.status_code == 200
    data = response.json()
    assert "profile" in data
    assert isinstance(data["profile"], list)
    assert len(data["profile"]) >= 2
    assert "total_distance" in data
    assert "min_elevation" in data
    assert "max_elevation" in data
    assert "elevation_gain" in data
    # Verify each point has the expected keys
    for point in data["profile"]:
        assert "distance" in point
        assert "elevation" in point
        assert "latitude" in point
        assert "longitude" in point


def test_elevation_profile_bad_input():
    """Non-LineString input should return 400."""
    bad_input = {"type": "Point", "coordinates": [-71.5, -33.0]}
    response = client.post("/profile/profile", json=bad_input)
    assert response.status_code == 400
