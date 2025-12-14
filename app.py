from __future__ import annotations

import argparse
import os
from typing import Sequence

from dotenv import load_dotenv

from musiclib import create_app
from musiclib.db_utils import init_db
from musiclib.scrapers.hooktheory import HooktheoryScraper
from musiclib.services.chord_analytics import (
    compute_and_cache_album_analytics,
    compute_and_cache_overall_analytics,
    compute_and_cache_song_analytics,
)

load_dotenv()

app = create_app()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Music library Flask application")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Run the development server (default)")
    subparsers.add_parser("init-db", help="Create SQLite database tables")

    analytics_parser = subparsers.add_parser(
        "compute-chord-analytics",
        help="Compute and cache chord progression analytics",
    )
    analytics_parser.add_argument(
        "--song", type=int, default=None, help="Compute analytics for specific song"
    )
    analytics_parser.add_argument(
        "--album", type=int, default=None, help="Compute analytics for specific album"
    )
    analytics_parser.add_argument(
        "--overall", action="store_true", help="Compute overall analytics"
    )
    analytics_parser.add_argument(
        "--all-albums", action="store_true", help="Compute analytics for all albums"
    )
    analytics_parser.add_argument(
        "--force", action="store_true", help="Recompute even if cached"
    )

    hooktheory_parser = subparsers.add_parser(
        "scrape-hooktheory-taylor-swift",
        help="Scrape Taylor Swift songs from Hooktheory",
    )
    hooktheory_parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of songs to scrape"
    )
    hooktheory_parser.add_argument(
        "--sleep", type=float, default=2.0, help="Sleep time between requests (seconds)"
    )
    hooktheory_parser.add_argument(
        "--force", action="store_true", help="Re-scrape existing songs"
    )

    args = parser.parse_args(argv)

    if args.command == "init-db":
        with app.app_context():
            init_db()
        return 0

    if args.command == "scrape-hooktheory-taylor-swift":
        with app.app_context():
            scraper = HooktheoryScraper(sleep_time=args.sleep)
            scraper.scrape_taylor_swift(limit=args.limit, force=args.force)
        return 0

    if args.command == "compute-chord-analytics":
        with app.app_context():
            if args.song:
                result = compute_and_cache_song_analytics(args.song)
                if result:
                    print(
                        f"Analyzed song {args.song}: "
                        f"progressions={len(result.progressions)} "
                        f"unique_chords={len(result.unique_chords)}"
                    )
                else:
                    print(f"Song {args.song} not found or has no chord data")
            elif args.album:
                results = compute_and_cache_album_analytics(album_id=args.album, force=args.force)
                for aid, compute_result in results.items():
                    print(
                        f"Album {aid}: "
                        f"songs={compute_result.songs_analyzed} "
                        f"progressions={compute_result.progressions_found} "
                        f"unique_chords={compute_result.unique_chords}"
                    )
            elif args.all_albums:
                results = compute_and_cache_album_analytics(force=args.force)
                print(
                    f"All albums analyzed: "
                    f"albums={len(results)} "
                )
            else:
                result = compute_and_cache_overall_analytics(force=args.force)
                print(
                    f"Overall analytics computed: "
                    f"songs={result.songs_analyzed} "
                    f"progressions={result.progressions_found} "
                    f"unique_chords={result.unique_chords}"
                )
        return 0

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
