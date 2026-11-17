"""Planner service entry point. Start with: python app.py"""
import logging
import sys
import time

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


def create_app(db_path=None):
    """Build the planner service. Tests pass their own db_path; normal runs use config.DB_PATH."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or config.DB_PATH
    db.init_app(app)
    from api import bp as planner_api
    app.register_blueprint(planner_api)

    # Only the UI's origin may call this API from a browser.
    CORS(app, origins=[config.UI_ORIGIN])

    _setup_logging()

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
        # Basic check for now; it will also test a write to the database in the observability step.
        db.get_db().execute("SELECT 1")
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    # 0.0.0.0 so the service is reachable from outside its container.
    create_app().run(host="0.0.0.0", port=config.PORT)