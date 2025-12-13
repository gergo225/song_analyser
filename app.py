from __future__ import annotations

import argparse
import os
from typing import Sequence

from dotenv import load_dotenv

from musiclib import create_app
from musiclib.db_utils import init_db
from musiclib.services.chord_analytics import (
    compute_and_cache_album_analytics,
    compute_and_cache_overall_analytics,
    compute_and_cache_song_analytics,
)
from musiclib.services.ultimate_guitar_sync import (
    scrape_taylor_swift_chords_to_db,
)

load_dotenv()

app = create_app()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Music library Flask application")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Run the development server (default)")
    subparsers.add_parser("init-db", help="Create SQLite database tables")

    scrape_parser = subparsers.add_parser(
        "scrape-ug-taylor-swift",
        help="Scrape Taylor Swift chord tabs from UltimateGuitar into SQLite",
    )
    scrape_parser.add_argument("--max-pages", type=int, default=None)
    scrape_parser.add_argument("--limit", type=int, default=None)
    scrape_parser.add_argument("--sleep", dest="sleep_seconds", type=float, default=1.0)
    scrape_parser.add_argument("--force", action="store_true")
    scrape_parser.add_argument(
        "--no-analytics", action="store_true", help="Skip analytics computation"
    )

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

    args = parser.parse_args(argv)

    if args.command == "init-db":
        with app.app_context():
            init_db()
        return 0

    if args.command == "scrape-ug-taylor-swift":
        with app.app_context():
            scrape_taylor_swift_chords_to_db(
                max_pages=args.max_pages,
                limit=args.limit,
                sleep_seconds=args.sleep_seconds,
                force=args.force,
                compute_analytics=not args.no_analytics,
            )
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
