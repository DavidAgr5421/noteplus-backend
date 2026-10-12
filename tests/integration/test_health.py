from fastapi.testclient import TestClient
from app.main.app import create_app

client = TestClient(create_app())


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "timestamp" in r.json()


def test_404():
    r = client.get("/api/v1/inexistente")
    assert r.status_code == 404


def test_openapi():
    r = client.get("/openapi.json")
    assert r.status_code == 200
