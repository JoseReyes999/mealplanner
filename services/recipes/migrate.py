"""Versioned migrations: files in migrations/ named NNN_description.sql, applied in order, once each.

Every applied file is recorded in the schema_migrations table, so a new deploy only runs
the files it hasn't seen. Each file runs in one transaction: if a statement fails, nothing
of that file is kept and it will be tried again on the next start. A file may hold several
batches separated by a line with only GO, as in sqlcmd.

Migrations run when the service starts. That is safe because the Container App runs at most
one replica, so two copies never migrate at the same time.
"""
import os
import re

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
FILE_NAME = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")
GO = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)

CREATE_TABLE = """
IF OBJECT_ID('schema_migrations', 'U') IS NULL
    CREATE TABLE schema_migrations (
        version NVARCHAR(100) NOT NULL PRIMARY KEY,
        applied_at DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    )
"""


def migration_files(directory=MIGRATIONS_DIR):
    """All migration file names, in the order they must run. A badly named file is an error."""
    names = sorted(f for f in os.listdir(directory) if f.endswith(".sql"))
    for name in names:
        if not FILE_NAME.match(name):
            raise ValueError(f"migration {name} must be named like 001_description.sql")
    return names


def applied_versions(conn):
    return {row["version"] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}


def apply_migrations(conn, directory=MIGRATIONS_DIR):
    """Apply every migration not yet in schema_migrations. Returns the names applied, in order."""
    with conn:
        conn.execute(CREATE_TABLE)
    done = applied_versions(conn)
    applied = []
    for name in migration_files(directory):
        if name in done:
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as f:
            batches = [batch for batch in GO.split(f.read()) if batch.strip()]
        with conn:  # the file's batches and its schema_migrations row commit together
            for batch in batches:
                conn.execute(batch)
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (name,))
        applied.append(name)
    return applied
