"""Smoke tests for the startup contract: the app starts and creates its SQLite file."""
from app import create_app


def test_startup_creates_db_file(tmp_path):
    db_path = tmp_path / "data" / "test.db"
    create_app(str(db_path))
    assert db_path.exists()


def test_health_endpoint(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
