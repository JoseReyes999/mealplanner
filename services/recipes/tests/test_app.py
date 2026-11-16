"""Smoke tests: the recipes service starts and creates its own database file."""
from app import create_app


def test_startup_creates_db_file(tmp_path):
    db_path = tmp_path / "data" / "recipes.db"
    create_app(str(db_path))
    assert db_path.exists()


def test_health_endpoint(tmp_path):
    response = create_app(str(tmp_path / "recipes.db")).test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}