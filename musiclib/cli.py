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


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    init_db()
    click.echo("Initialized the database")


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
    app.cli.add_command(compute_chord_analytics_command)
