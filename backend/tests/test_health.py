from app.main import app
from fastapi.testclient import TestClient


def test_health_reports_ok_when_database_is_up() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}
