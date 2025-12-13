#!/usr/bin/env python
"""
Integration test for the chord analysis engine.
Tests the full pipeline from chord normalization through analytics caching.
"""

import json
import tempfile
from pathlib import Path

from musiclib import create_app
from musiclib.chord_analysis import (
    ChordProgression,
    analyze_song,
    aggregate_analytics,
    normalize_chord_symbol,
)
from musiclib.db_utils import init_db
from musiclib.models import Album, Artist, ChordLine, Song
from musiclib.services.chord_analytics import (
    compute_and_cache_overall_analytics,
    compute_and_cache_song_analytics,
    get_overall_analytics,
    get_song_analysis,
)


def test_integration():
    """Run integration tests."""
    print("=" * 70)
    print("Chord Analysis Engine - Integration Test")
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

            # Test chord analysis
            print("3. Testing chord analysis...")
            result1 = compute_and_cache_song_analytics(song1.id)
            assert result1 is not None, "Failed to analyze song 1"
            assert len(result1.progressions) > 0, "No progressions found for song 1"
            assert "C" in result1.unique_chords, "C not found in song 1 chords"
            print(f"   Song 1: {len(result1.progressions)} progressions, "
                  f"{len(result1.unique_chords)} unique chords")

            result2 = compute_and_cache_song_analytics(song2.id)
            assert result2 is not None, "Failed to analyze song 2"
            assert "Dm" in result2.unique_chords, "Dm not found in song 2 chords"
            print(f"   Song 2: {len(result2.progressions)} progressions, "
                  f"{len(result2.unique_chords)} unique chords")

            # Test retrieval
            print("4. Testing analytics retrieval...")
            retrieved1 = get_song_analysis(song1.id)
            assert retrieved1 is not None, "Failed to retrieve song 1 analysis"
            assert retrieved1.song_title == "Song 1"
            print(f"   Retrieved song 1 analysis: {retrieved1.song_title}")

            # Test overall analytics
            print("5. Computing overall analytics...")
            overall_result = compute_and_cache_overall_analytics(force=True)
            assert overall_result.songs_analyzed == 2, "Should have analyzed 2 songs"
            assert overall_result.progressions_found > 0, "Should have found progressions"
            print(f"   Overall: {overall_result.songs_analyzed} songs, "
                  f"{overall_result.progressions_found} progressions, "
                  f"{overall_result.unique_chords} unique chords")

            # Test analytics retrieval
            print("6. Testing overall analytics retrieval...")
            overall_analytics = get_overall_analytics()
            assert overall_analytics is not None, "Failed to retrieve overall analytics"
            assert len(overall_analytics.most_common_chords) > 0
            print(f"   Top 3 chords: {overall_analytics.most_common_chords[:3]}")

            # Test JSON serialization
            print("7. Testing JSON serialization...")
            from musiclib.chord_analysis import analytics_to_json, analytics_from_json

            json_str = analytics_to_json(overall_analytics)
            data = json.loads(json_str)
            assert "most_common_chords" in data
            assert "most_common_progressions" in data
            print(f"   JSON size: {len(json_str)} bytes")

            restored = analytics_from_json(json_str)
            assert len(restored.most_common_chords) == len(overall_analytics.most_common_chords)
            print("   JSON round-trip successful")

    print()
    print("=" * 70)
    print("All integration tests passed!")
    print("=" * 70)


if __name__ == "__main__":
    test_integration()
