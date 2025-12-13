from __future__ import annotations

import click
from flask import Flask
from flask.cli import with_appcontext

from .db_utils import init_db
from .services.ultimate_guitar_sync import scrape_taylor_swift_chords_to_db


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    init_db()
    click.echo("Initialized the database")


@click.command("scrape-ug-taylor-swift")
@click.option(
    "--max-pages",
    type=int,
    default=None,
    help="Max pages to scrape from UltimateGuitar",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Stop after scraping N tabs",
)
@click.option(
    "--sleep",
    "sleep_seconds",
    type=float,
    default=1.0,
    show_default=True,
    help="Delay between requests",
)
@click.option("--force", is_flag=True, help="Re-scrape songs even if present")
@with_appcontext
def scrape_ug_taylor_swift_command(
    *,
    max_pages: int | None,
    limit: int | None,
    sleep_seconds: float,
    force: bool,
) -> None:
    result = scrape_taylor_swift_chords_to_db(
        max_pages=max_pages,
        limit=limit,
        sleep_seconds=sleep_seconds,
        force=force,
    )

    click.echo(
        "UltimateGuitar scrape complete: "
        f"seen_tabs={result.seen_tabs} created_songs={result.created_songs} "
        f"updated_songs={result.updated_songs} skipped_songs={result.skipped_songs}"
    )


def register_cli(app: Flask) -> None:
    app.cli.add_command(init_db_command)
    app.cli.add_command(scrape_ug_taylor_swift_command)
