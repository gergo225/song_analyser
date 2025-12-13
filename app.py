from __future__ import annotations

import argparse
import os
from typing import Sequence

from dotenv import load_dotenv

from musiclib import create_app
from musiclib.db_utils import init_db
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
            )
        return 0

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
