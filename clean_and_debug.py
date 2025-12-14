#!/usr/bin/env python
"""
Clean database and debug script.
"""

from musiclib import create_app
from musiclib.db_utils import init_db
from musiclib.models import Album, Artist, ChordLine, Song
from musiclib.services.chord_analytics import compute_and_cache_song_analytics


def clean_and_debug():
    """Clean database and debug the issue."""
    print("=" * 70)
    print("Clean and Debug Database")
    print("=" * 70)
    print()

    app = create_app()

    with app.app_context():
        from musiclib.extensions import db

        print("1. Cleaning existing data...")
        
        # Clean cached analytics
        db.session.query(CachedAnalyticsMetadata).delete()
        
        # Clean chord lines
        db.session.query(ChordLine).delete()
        
        # Clean songs
        db.session.query(Song).delete()
        
        # Clean albums
        db.session.query(Album).delete()
        
        # Clean artists
        db.session.query(Artist).delete()
        
        db.session.commit()
        print("   Database cleaned")

        print("2. Creating fresh test data...")
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

        if result1:
            print(f"   Song 1 progressions: {len(result1.progressions)}")
            print(f"   Song 1 unique chords: {result1.unique_chords}")

        result2 = compute_and_cache_song_analytics(song2.id)
        print(f"   Song 2 analysis result: {result2}")

        if result2:
            print(f"   Song 2 progressions: {len(result2.progressions)}")
            print(f"   Song 2 unique chords: {result2.unique_chords}")

        print("5. Testing overall analysis...")
        from musiclib.services.chord_analytics import compute_and_cache_overall_analytics
        
        overall_result = compute_and_cache_overall_analytics(force=True)
        print(f"   Overall result: {overall_result}")
        print(f"   Songs analyzed: {overall_result.songs_analyzed}")

    print()
    print("=" * 70)
    print("Clean and debug complete")
    print("=" * 70)


if __name__ == "__main__":
    from musiclib.models import CachedAnalyticsMetadata
    clean_and_debug()