"""Smoke tests: the recipes service starts, migrates its database, logs and answers CORS."""
import logging

import os
import shutil

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
    assert versions(database_url) == ["001_init.sql", "002_add_prep_minutes.sql"]
    assert [r.getMessage() for r in caplog.records] == [
        "applied migration 001_init.sql", "applied migration 002_add_prep_minutes.sql"]


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

def test_migration_002_keeps_existing_recipes(database_url, tmp_path):
    """What happens on Azure: a database at 001 already holds data, then 002 is deployed."""
    shutil.copy(os.path.join(migrate.MIGRATIONS_DIR, "001_init.sql"), tmp_path)
    conn = db.connect(database_url)
    try:
        migrate.apply_migrations(conn, str(tmp_path))  # the database as it was before 002
        with conn:
            conn.execute("INSERT INTO recipes (name, base_servings, instructions) VALUES ('Bread', 2, 'Bake.')")
        assert migrate.apply_migrations(conn) == ["002_add_prep_minutes.sql"]  # the deploy
        row = conn.execute("SELECT name, base_servings, instructions, prep_minutes FROM recipes").fetchone()
    finally:
        conn.close()
    assert row == {"name": "Bread", "base_servings": 2, "instructions": "Bake.", "prep_minutes": 0}

def test_badly_named_migration_is_rejected(tmp_path):
    (tmp_path / "2_add_column.sql").write_text("SELECT 1")
    with pytest.raises(ValueError, match="001_description.sql"):
        migrate.migration_files(str(tmp_path))


def test_health_reads_and_writes_the_database(database_url, monkeypatch):
    monkeypatch.setattr(config, "VERSION", "3f2a9c1")
    response = create_app(database_url).test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "db": "ok", "version": "3f2a9c1"}
    assert versions(database_url) == ["001_init.sql", "002_add_prep_minutes.sql"]  # write test rolled back


def test_health_is_503_when_the_database_is_down(database_url, monkeypatch, caplog):
    client = create_app(database_url).test_client()

    def database_down():
        raise pymssql.OperationalError("20009 unable to connect")

    monkeypatch.setattr(db, "get_db", database_down)
    with caplog.at_level(logging.ERROR, logger="recipes"):
        response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "db": "unavailable", "version": config.VERSION}
    assert "health check failed" in caplog.text

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
