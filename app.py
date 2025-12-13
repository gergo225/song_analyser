from __future__ import annotations

import argparse
import os
from typing import Sequence

from dotenv import load_dotenv

from musiclib import create_app
from musiclib.db_utils import init_db

load_dotenv()

app = create_app()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Music library Flask application")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Run the development server (default)")
    subparsers.add_parser("init-db", help="Create SQLite database tables")

    args = parser.parse_args(argv)

    if args.command == "init-db":
        with app.app_context():
            init_db()
        return 0

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
