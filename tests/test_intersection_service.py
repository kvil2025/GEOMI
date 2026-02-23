import pytest
from fastapi.testclient import TestClient
from fastapi_app.main import app

client = TestClient(app)


SAMPLE_POLYGON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-70.65, -27.35],
                        [-70.60, -27.35],
                        [-70.60, -27.30],
                        [-70.65, -27.30],
                        [-70.65, -27.35],
                    ]
                ],
            },
            "properties": {"name": "Test Area"},
        }
    ],
}


def test_intersection_success():
    """POST a polygon and verify the response is a FeatureCollection with summary."""
    response = client.post("/intersection/intersect", json=SAMPLE_POLYGON)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)
    assert "summary" in data
    assert data["summary"]["input_features"] == 1


def test_intersection_empty_input():
    """Empty geometry list should return 400."""
    response = client.post(
        "/intersection/intersect",
        json={"type": "FeatureCollection", "features": []},
    )
    assert response.status_code == 400
