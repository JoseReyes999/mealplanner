"""SQL Server helpers: connection settings from DATABASE_URL, retries while the database
wakes up, one connection per request, and migrations applied at startup."""
import logging
import time
from urllib.parse import parse_qs, unquote, urlsplit

import pymssql
from flask import current_app, g

import config
import migrate

log = logging.getLogger("planner")


def parse_url(url):
    """mssql://user:password@host:1433/database?encrypt=require -> keyword arguments for pymssql.connect."""
    if not url:
        raise RuntimeError("DATABASE_URL is not set, e.g. mssql://user:password@localhost:1433/planner")
    parts = urlsplit(url)
    database = parts.path.strip("/")
    if parts.scheme != "mssql" or not parts.hostname or not database:
        raise RuntimeError("DATABASE_URL must look like mssql://user:password@host:1433/database")
    query = parse_qs(parts.query)
    return {
        "server": parts.hostname,
        "port": str(parts.port or 1433),
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "database": database,
        # "request" encrypts when the server supports it; Azure SQL needs "require".
        "encryption": query.get("encrypt", ["request"])[0],
    }


class Connection:
    """A thin wrapper around a pymssql connection, so the repositories can keep writing
    conn.execute(sql, params) and `with conn:` as they did with sqlite3. Rows are dicts."""

    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, params=None):
        cursor = self.raw.cursor(as_dict=True)
        if params is None:
            cursor.execute(sql)  # no params: the SQL is sent as it is
        else:
            cursor.execute(sql, params)  # pymssql fills each %s, quoting the value safely
        return cursor

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Commit if the block finished, roll back if it raised: one transaction per `with`.
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


def connect(url):
    """Open a connection, retrying with backoff while the database is not ready.

    A paused Azure SQL database answers with error 40613 or a connection timeout
    (pymssql error 20002/20003) for about a minute while it resumes.
    """
    settings = parse_url(url)
    wait = 1
    for attempt in range(1, config.DB_CONNECT_ATTEMPTS + 1):
        try:
            raw = pymssql.connect(
                **settings,
                login_timeout=config.DB_LOGIN_TIMEOUT_S,
                timeout=config.DB_QUERY_TIMEOUT_S,
                tds_version="7.4",
                autocommit=False,
            )
            return Connection(raw)
        except pymssql.OperationalError as exc:
            if attempt == config.DB_CONNECT_ATTEMPTS:
                raise
            log.warning("database not ready (attempt %d/%d): %s - retrying in %ss",
                        attempt, config.DB_CONNECT_ATTEMPTS, exc, wait)
            time.sleep(wait)
            wait = min(wait * 2, config.DB_RETRY_MAX_WAIT_S)


def get_db():
    """Return this request's connection, opening it the first time it is needed."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_URL"])
    return g.db


def close_db(exc=None):
    """Close the request's connection (Flask calls this after every request)."""
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app):
    """Apply any new migrations, then wire the per-request connection into the app."""
    conn = connect(app.config["DATABASE_URL"])
    try:
        for name in migrate.apply_migrations(conn):
            log.info("applied migration %s", name)
    finally:
        conn.close()
    app.teardown_appcontext(close_db)
