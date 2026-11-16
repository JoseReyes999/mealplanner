"""Recipes service entry point. Start with: python app.py"""
from flask import Flask

import config
import db


def create_app(db_path=None):
    """Build the recipes service. Tests pass their own db_path; normal runs use config.DB_PATH."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or config.DB_PATH
    db.init_app(app)
    from api import bp as recipes_api
    app.register_blueprint(recipes_api)

    @app.route("/health")
    def health():
        # Basic check for now; it will also test a write to the database in the observability step.
        db.get_db().execute("SELECT 1")
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    # 0.0.0.0 so the service is reachable from outside its container.
    create_app().run(host="0.0.0.0", port=config.PORT)