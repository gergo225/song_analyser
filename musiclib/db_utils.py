from __future__ import annotations

from sqlalchemy import inspect, text

from .extensions import db


def init_db() -> None:
    db.create_all()
    ensure_sqlite_schema()


def ensure_sqlite_schema() -> None:
    engine = db.engine
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "songs" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("songs")}

    desired = {
        "key": "VARCHAR(50)",
        "source": "VARCHAR(50)",
        "source_url": "VARCHAR(1024)",
        "tab_type": "VARCHAR(50)",
        "raw_tab": "TEXT",
        "last_scraped_at": "DATETIME",
    }

    to_add = {name: ddl for name, ddl in desired.items() if name not in existing}
    if not to_add:
        return

    with engine.begin() as conn:
        for name, ddl in to_add.items():
            conn.execute(text(f"ALTER TABLE songs ADD COLUMN {name} {ddl}"))
