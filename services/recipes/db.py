"""SQLite helpers: one connection per request, schema created automatically at startup."""
import os
import sqlite3

from flask import current_app, g

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def connect(db_path):
    """Open a connection that returns rows as dict-like objects and enforces foreign keys."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Return this request's connection, opening it the first time it is needed."""
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db


def close_db(exc=None):
    """Close the request's connection (Flask calls this after every request)."""
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(db_path):
    """Create the data folder and run schema.sql. Safe to run on every start (CREATE TABLE IF NOT EXISTS)."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = f.read()
    conn = connect(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()


def init_app(app):
    """Wire the database into the Flask app."""
    init_db(app.config["DB_PATH"])
    app.teardown_appcontext(close_db)
