from fastapi.testclient import TestClient

def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "HealthAI Platform API is Running", "status": "active"}

def test_device_status(client: TestClient):
    response = client.get("/api/device/current")
    assert response.status_code == 200
    data = response.json()
    assert "hr" in data
