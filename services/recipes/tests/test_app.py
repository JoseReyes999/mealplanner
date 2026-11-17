"""Smoke tests: the recipes service starts and creates its own database file."""
import logging

import config
from app import create_app


def test_startup_creates_db_file(tmp_path):
    db_path = tmp_path / "data" / "recipes.db"
    create_app(str(db_path))
    assert db_path.exists()


def test_health_endpoint(tmp_path):
    response = create_app(str(tmp_path / "recipes.db")).test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}

# ---- request logs and CORS ----

def test_every_request_is_logged(tmp_path, caplog):
    client = create_app(str(tmp_path / "recipes.db")).test_client()
    with caplog.at_level(logging.INFO, logger="recipes"):
        client.get("/health")
        client.get("/does-not-exist")
    lines = [r.getMessage() for r in caplog.records]
    assert lines[0].startswith("GET /health 200 ")
    assert lines[1].startswith("GET /does-not-exist 404 ")
    assert all(line.endswith("ms") for line in lines)


def test_cors_allows_only_the_ui_origin(tmp_path):
    client = create_app(str(tmp_path / "recipes.db")).test_client()
    allowed = client.get("/health", headers={"Origin": config.UI_ORIGIN})
    assert allowed.headers["Access-Control-Allow-Origin"] == config.UI_ORIGIN
    other = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert "Access-Control-Allow-Origin" not in other.headers


def test_cors_preflight_from_the_ui(tmp_path):
    client = create_app(str(tmp_path / "recipes.db")).test_client()
    response = client.options("/health", headers={
        "Origin": config.UI_ORIGIN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    })
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == config.UI_ORIGIN
    assert "POST" in response.headers["Access-Control-Allow-Methods"]