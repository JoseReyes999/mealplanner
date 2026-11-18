"""Smoke tests: the recipes service starts, migrates its database, logs and answers CORS."""
import logging

import pymssql
import pytest

import config
import db
import migrate
from app import create_app


def versions(database_url):
    conn = db.connect(database_url)
    try:
        rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        return [row["version"] for row in rows]
    finally:
        conn.close()


def test_startup_applies_migrations_once(database_url, caplog):
    with caplog.at_level(logging.INFO, logger="recipes"):
        create_app(database_url)
        create_app(database_url)  # a second start (a new deploy) finds nothing new to apply
    assert versions(database_url) == ["001_init.sql"]
    assert [r.getMessage() for r in caplog.records] == ["applied migration 001_init.sql"]


def test_failed_migration_keeps_nothing_of_that_file(database_url, tmp_path):
    (tmp_path / "001_first.sql").write_text("CREATE TABLE a (id INT)")
    (tmp_path / "002_broken.sql").write_text("CREATE TABLE b (id INT)\nGO\nINSERT INTO missing VALUES (1)")
    conn = db.connect(database_url)
    try:
        with pytest.raises(pymssql.DatabaseError):
            migrate.apply_migrations(conn, str(tmp_path))
        tables = {r["name"] for r in conn.execute("SELECT name FROM sys.tables").fetchall()}
    finally:
        conn.close()
    assert versions(database_url) == ["001_first.sql"]
    assert tables == {"schema_migrations", "a"}  # table b was rolled back with its file


def test_badly_named_migration_is_rejected(tmp_path):
    (tmp_path / "2_add_column.sql").write_text("SELECT 1")
    with pytest.raises(ValueError, match="001_description.sql"):
        migrate.migration_files(str(tmp_path))


def test_health_endpoint(database_url):
    response = create_app(database_url).test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}

# ---- request logs and CORS ----

def test_every_request_is_logged(database_url, caplog):
    client = create_app(database_url).test_client()
    caplog.clear()  # forget the startup lines (applied migration ...), keep only the requests
    with caplog.at_level(logging.INFO, logger="recipes"):
        client.get("/health")
        client.get("/does-not-exist")
    lines = [r.getMessage() for r in caplog.records]
    assert lines[0].startswith("GET /health 200 ")
    assert lines[1].startswith("GET /does-not-exist 404 ")
    assert all(line.endswith("ms") for line in lines)


def test_cors_allows_only_the_ui_origin(database_url):
    client = create_app(database_url).test_client()
    allowed = client.get("/health", headers={"Origin": config.UI_ORIGIN})
    assert allowed.headers["Access-Control-Allow-Origin"] == config.UI_ORIGIN
    other = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert "Access-Control-Allow-Origin" not in other.headers


def test_cors_preflight_from_the_ui(database_url):
    client = create_app(database_url).test_client()
    response = client.options("/health", headers={
        "Origin": config.UI_ORIGIN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    })
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == config.UI_ORIGIN
    assert "POST" in response.headers["Access-Control-Allow-Methods"]