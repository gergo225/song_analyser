#!/usr/bin/env python
"""
Debug script to understand the integration test issue.
"""

import tempfile
from pathlib import Path

from musiclib import create_app
from musiclib.db_utils import init_db
from musiclib.models import Album, Artist, ChordLine, Song
from musiclib.services.chord_analytics import compute_and_cache_song_analytics


def debug_integration_issue():
    """Debug the integration test issue."""
    print("=" * 70)
    print("Debug Integration Issue")
    print("=" * 70)
    print()

    # Create a temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_uri = f"sqlite:///{db_path}"

        # Create Flask app with test config
        app = create_app()
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
        app.config["TESTING"] = True

        with app.app_context():
            # Initialize database
            print("1. Initializing database...")
            init_db()
            from musiclib.extensions import db

            # Create test data
            print("2. Creating test data...")
            artist = Artist(name="Test Artist")
            db.session.add(artist)
            db.session.flush()

            album = Album(artist_id=artist.id, title="Test Album", release_year=2024)
            db.session.add(album)
            db.session.flush()

            song1 = Song(
                artist_id=artist.id,
                album_id=album.id,
                title="Song 1",
                source="test",
            )
            db.session.add(song1)
            db.session.flush()

            song2 = Song(
                artist_id=artist.id,
                album_id=album.id,
                title="Song 2",
                source="test",
            )
            db.session.add(song2)
            db.session.flush()

            print(f"   Created song1 with ID: {song1.id}")
            print(f"   Created song2 with ID: {song2.id}")

            # Add chord lines for song 1
            lines1 = ["C F G", "C F G", "Am F G", "C"]
            for idx, line in enumerate(lines1, start=1):
                chord_line = ChordLine(song_id=song1.id, line_number=idx, content=line)
                db.session.add(chord_line)

            # Add chord lines for song 2
            lines2 = ["Dm Am", "Dm Am", "G C"]
            for idx, line in enumerate(lines2, start=1):
                chord_line = ChordLine(song_id=song2.id, line_number=idx, content=line)
                db.session.add(chord_line)

            db.session.commit()

            print("3. Verifying data in database...")

            # Check songs
            all_songs = Song.query.all()
            print(f"   Total songs in DB: {len(all_songs)}")
            for song in all_songs:
                print(f"   - Song {song.id}: {song.title}")

            # Check chord lines
            all_chord_lines = ChordLine.query.all()
            print(f"   Total chord lines in DB: {len(all_chord_lines)}")
            for cl in all_chord_lines:
                print(f"   - ChordLine {cl.id}: song_id={cl.song_id}, content='{cl.content}'")

            # Check relationships
            for song in all_songs:
                chord_count = ChordLine.query.filter_by(song_id=song.id).count()
                print(f"   Song '{song.title}' has {chord_count} chord lines")

            print("4. Testing individual song analysis...")
            result1 = compute_and_cache_song_analytics(song1.id)
            print(f"   Song 1 analysis result: {result1}")

            result2 = compute_and_cache_song_analytics(song2.id)
            print(f"   Song 2 analysis result: {result2}")

    print()
    print("=" * 70)
    print("Debug complete")
    print("=" * 70)


if __name__ == "__main__":
    debug_integration_issue()