from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask

from .cli import register_cli
from .config import Config
from .extensions import db


def create_app(config_object: type[Config] | str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_object(Config)
    if config_object is not None:
        app.config.from_object(config_object)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        else:
            db_path = Path(app.instance_path) / "app.db"
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    db.init_app(app)

    from . import models  # noqa: F401

    register_cli(app)

    from .web.analytics import analytics_bp

    app.register_blueprint(analytics_bp)

    @app.get("/")
    def index() -> dict[str, Any]:
        return {
            "status": "ok",
            "database_uri": app.config.get("SQLALCHEMY_DATABASE_URI"),
        }

    return app
