"""Entry point. Start with: python app.py"""
from flask import Flask, render_template

import config
import db


def create_app(db_path=None):
    """Build the Flask app. Tests pass their own db_path; normal runs use config.DB_PATH."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or config.DB_PATH
    db.init_app(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/health")
    def health():
        # Lightweight readiness check for the Assignment 2 deployment.
        db.get_db().execute("SELECT 1")
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    # 0.0.0.0 so the app is reachable from outside a container (contract §7.2).
    create_app().run(host="0.0.0.0", port=config.PORT)
