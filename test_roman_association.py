#!/usr/bin/env python
"""
Test to specifically verify Roman numeral chord-to-song association.
"""

import tempfile
from pathlib import Path

from musiclib import create_app
from musiclib.db_utils import init_db
from musiclib.models import Artist, ChordLine, Song
from musiclib.scrapers.hooktheory import HooktheoryScraper


def test_roman_numeral_association():
    """Test that Roman numeral chords are properly associated with songs."""
    print("=" * 70)
    print("Roman Numeral Chord-to-Song Association Test")
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
            from musiclib.extensions import db

            # Initialize database
            print("1. Initializing database...")
            init_db()

            # Simulate Hooktheory scraper behavior
            print("2. Testing Hooktheory scraper pattern...")

            # Create artist
            artist = Artist(name="Taylor Swift")
            db.session.add(artist)
            db.session.commit()
            print(f"   Created artist: {artist.name} (ID: {artist.id})")

            # Simulate scraped song data
            song_data = {
                "title": "Love Story",
                "key": "D major",
                "url": "https://www.hooktheory.com/theorytab/view/taylor-swift/love-story",
                "roman_numerals": ["I", "V", "vi", "IV", "I", "V", "vi", "IV"]
            }

            # Check if song exists (simulating the scraper logic)
            existing_song = Song.query.filter_by(
                source="hooktheory",
                source_url=song_data["url"]
            ).first()

            if existing_song:
                print(f"   Existing song found: {existing_song.title} (ID: {existing_song.id})")
                song = existing_song
            else:
                # Create new song (this is what happens in the scraper)
                song = Song(
                    artist_id=artist.id,
                    title=song_data["title"],
                    key=song_data["key"],
                    source="hooktheory",
                    source_url=song_data["url"],
                    tab_type="roman_numerals"
                )
                db.session.add(song)
                db.session.flush()  # This gets the song.id

                print(f"   Created new song: {song.title} (ID: {song.id})")

            print("3. Adding Roman numeral chord lines...")

            # This is the critical part - creating ChordLine entries with song_id
            for line_num, numeral in enumerate(song_data["roman_numerals"], 1):
                chord_line = ChordLine(
                    song_id=song.id,  # This should establish the relationship
                    line_number=line_num,
                    content=numeral
                )
                db.session.add(chord_line)

            db.session.commit()
            print(f"   Added {len(song_data['roman_numerals'])} chord lines")

            print("4. Verifying chord-to-song relationships...")

            # Test 1: Query chord lines and verify they have song_id
            chord_lines = ChordLine.query.filter_by(song_id=song.id).all()
            print(f"   Found {len(chord_lines)} chord lines for song {song.id}")

            # Test 2: Verify each chord line is properly associated
            for cl in chord_lines:
                print(f"   - ChordLine {cl.id}: line {cl.line_number} = '{cl.content}' (song_id: {cl.song_id})")
                if cl.song_id != song.id:
                    print(f"   ERROR: ChordLine {cl.id} has wrong song_id!")
                    return False

            # Test 3: Test the relationship from song to chord lines
            retrieved_song = Song.query.get(song.id)
            associated_chords = retrieved_song.chord_lines
            print(f"   Song.chord_lines relationship: {len(associated_chords)} chords")

            # Test 4: Verify the progression is correct
            progression = [cl.content for cl in sorted(associated_chords, key=lambda x: x.line_number)]
            print(f"   Chord progression: {' - '.join(progression)}")
            
            expected_progression = song_data["roman_numerals"]
            if progression == expected_progression:
                print("   ✓ Chord progression matches expected")
            else:
                print(f"   ✗ Chord progression mismatch!")
                print(f"   Expected: {expected_progression}")
                print(f"   Got: {progression}")
                return False

            print("5. Testing chord analysis integration...")

            # Test that chord analysis can find and process the song
            from musiclib.services.chord_analytics import compute_and_cache_song_analytics
            
            result = compute_and_cache_song_analytics(song.id)
            if result is None:
                print("   ✗ Chord analysis failed - song not found or no chords")
                return False

            print(f"   ✓ Chord analysis succeeded:")
            print(f"     - Song: {result.song_title}")
            print(f"     - Progressions: {len(result.progressions)}")
            print(f"     - Unique chords: {len(result.unique_chords)}")
            print(f"     - Chords: {list(result.unique_chords)}")

            # Verify the analysis found the correct chords
            expected_chords = set(["I", "V", "vi", "IV"])
            found_chords = set(result.unique_chords)
            if found_chords == expected_chords:
                print("   ✓ Roman numerals correctly analyzed")
            else:
                print(f"   ✗ Roman numeral analysis incorrect:")
                print(f"     Expected: {expected_chords}")
                print(f"     Found: {found_chords}")
                return False

    print()
    print("=" * 70)
    print("✓ All Roman numeral association tests passed!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = test_roman_numeral_association()
    if not success:
        exit(1)