import pytest
from fastapi.testclient import TestClient
from fastapi_app.main import app

client = TestClient(app)

@pytest.fixture
def bbox():
    # Example bbox covering a small area in Chile (minx,miny,maxx,maxy)
    return "-71.5,-33.0,-71.0,-32.5"

def test_get_concessions_success(bbox):
    response = client.get(f"/wfs/polygons?bbox={bbox}")
    # Since we are using a live WFS service, we expect a 200 response and JSON content
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    # The response should contain a "type" field for GeoJSON FeatureCollection
    assert response.json().get("type") == "FeatureCollection"
