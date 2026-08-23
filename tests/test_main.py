from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "2.0.0"
    assert "message" in data

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "gitops-demo-app"
