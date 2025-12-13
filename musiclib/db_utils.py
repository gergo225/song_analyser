from __future__ import annotations

from .extensions import db


def init_db() -> None:
    db.create_all()
