"""Planner service entry point. Start with: python app.py"""
import logging
import sys
import time

import pymssql
from flask import Flask, g, request
from flask_cors import CORS

import config
import db

log = logging.getLogger("planner")


def _setup_logging():
    """One plain line per request on stdout, where Docker and Azure collect logs."""
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
        log.addHandler(handler)
        log.setLevel(logging.INFO)


def create_app(database_url=None):
    """Build the planner service. Tests pass a test database; normal runs use config.DATABASE_URL."""
    _setup_logging()  # first, so the migration log lines are printed too
    app = Flask(__name__)
    app.config["DATABASE_URL"] = database_url or config.DATABASE_URL
    db.init_app(app)
    from api import bp as planner_api
    app.register_blueprint(planner_api)

    # Only the UI's origin may call this API from a browser.
    CORS(app, origins=[config.UI_ORIGIN])


    @app.before_request
    def start_timer():
        g.start = time.perf_counter()

    @app.after_request
    def log_request(response):
        ms = (time.perf_counter() - g.start) * 1000
        log.info("%s %s %s %.1fms", request.method, request.path, response.status_code, ms)
        return response

    @app.route("/health")
    def health():
        """200 if this service can read and write its own database, 503 if it can't.

        The pipeline polls this after every deploy; `version` says which commit is running.
        """
        try:
            conn = db.get_db()
            conn.execute("SELECT COUNT(*) AS n FROM schema_migrations").fetchone()  # read
            # Write: insert a row and roll it back, so the check proves we can write but keeps nothing.
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", ("health-check",))
            conn.rollback()
        except (pymssql.Error, RuntimeError) as exc:
            log.error("health check failed: %s", exc)
            return {"status": "error", "db": "unavailable", "version": config.VERSION}, 503
        return {"status": "ok", "db": "ok", "version": config.VERSION}

    return app


if __name__ == "__main__":
    # 0.0.0.0 so the service is reachable from outside its container.
    create_app().run(host="0.0.0.0", port=config.PORT)