from __future__ import annotations

import click
from flask import Flask
from flask.cli import with_appcontext

from .db_utils import init_db
from .services.chord_analytics import (
    compute_and_cache_album_analytics,
    compute_and_cache_overall_analytics,
    compute_and_cache_song_analytics,
)
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
@click.option(
    "--no-analytics",
    is_flag=True,
    default=False,
    help="Skip analytics computation after scraping",
)
@with_appcontext
def scrape_ug_taylor_swift_command(
    *,
    max_pages: int | None,
    limit: int | None,
    sleep_seconds: float,
    force: bool,
    no_analytics: bool,
) -> None:
    result = scrape_taylor_swift_chords_to_db(
        max_pages=max_pages,
        limit=limit,
        sleep_seconds=sleep_seconds,
        force=force,
        compute_analytics=not no_analytics,
    )

    click.echo(
        "UltimateGuitar scrape complete: "
        f"seen_tabs={result.seen_tabs} created_songs={result.created_songs} "
        f"updated_songs={result.updated_songs} skipped_songs={result.skipped_songs}"
    )


@click.command("compute-chord-analytics")
@click.option(
    "--song",
    type=int,
    default=None,
    help="Compute analytics for a specific song ID",
)
@click.option(
    "--album",
    type=int,
    default=None,
    help="Compute analytics for a specific album ID",
)
@click.option(
    "--overall",
    is_flag=True,
    default=False,
    help="Compute overall analytics across all songs",
)
@click.option(
    "--all-albums",
    is_flag=True,
    default=False,
    help="Compute analytics for all albums",
)
@click.option("--force", is_flag=True, help="Recompute even if cached")
@with_appcontext
def compute_chord_analytics_command(
    *,
    song: int | None,
    album: int | None,
    overall: bool,
    all_albums: bool,
    force: bool,
) -> None:
    """Compute and cache chord progression analytics."""
    if song:
        result = compute_and_cache_song_analytics(song)
        if result:
            click.echo(
                f"Analyzed song {song}: "
                f"progressions={len(result.progressions)} "
                f"unique_chords={len(result.unique_chords)}"
            )
        else:
            click.echo(f"Song {song} not found or has no chord data")
    elif album:
        results = compute_and_cache_album_analytics(album_id=album, force=force)
        for aid, compute_result in results.items():
            click.echo(
                f"Album {aid}: "
                f"songs={compute_result.songs_analyzed} "
                f"progressions={compute_result.progressions_found} "
                f"unique_chords={compute_result.unique_chords}"
            )
    elif all_albums:
        results = compute_and_cache_album_analytics(force=force)
        total_songs = sum(r.songs_analyzed for r in results.values())
        total_progressions = sum(r.progressions_found for r in results.values())
        total_chords = len(set().union(
            *[{c for c in r.__dict__.values()} for r in results.values()]
        ))
        click.echo(
            f"All albums analyzed: "
            f"albums={len(results)} "
            f"total_songs={total_songs} "
            f"total_progressions={total_progressions}"
        )
    elif overall:
        result = compute_and_cache_overall_analytics(force=force)
        click.echo(
            f"Overall analytics computed: "
            f"songs={result.songs_analyzed} "
            f"progressions={result.progressions_found} "
            f"unique_chords={result.unique_chords}"
        )
    else:
        result = compute_and_cache_overall_analytics(force=force)
        click.echo(
            f"Overall analytics computed: "
            f"songs={result.songs_analyzed} "
            f"progressions={result.progressions_found} "
            f"unique_chords={result.unique_chords}"
        )


def register_cli(app: Flask) -> None:
    app.cli.add_command(init_db_command)
    app.cli.add_command(scrape_ug_taylor_swift_command)
    app.cli.add_command(compute_chord_analytics_command)
