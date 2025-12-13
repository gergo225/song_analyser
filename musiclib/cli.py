from __future__ import annotations

import click
from flask import Flask
from flask.cli import with_appcontext

from .db_utils import init_db


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    init_db()
    click.echo("Initialized the database")


def register_cli(app: Flask) -> None:
    app.cli.add_command(init_db_command)
