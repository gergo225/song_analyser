#!/usr/bin/env python
"""
Example usage of the chord analysis engine.
This demonstrates the core functionality without requiring database setup.
"""

from musiclib.chord_analysis import (
    ChordProgression,
    analyze_song,
    aggregate_analytics,
    detect_key_changes,
    extract_chords_from_lines,
    extract_progressions_by_line,
    normalize_chord_symbol,
)


def main():
    print("=" * 60)
    print("Chord Analysis Engine - Example Usage")
    print("=" * 60)
    print()

    # Example 1: Chord normalization
    print("1. Chord Normalization")
    print("-" * 40)
    test_chords = [
        "C",
        "Cm",
        "Cm7",
        "Caug",
        "C/G",
        "Fsus2",
        "Am7b5",
        "Gminor",
        "D#maj7",
        "Bb",
    ]
    for chord in test_chords:
        normalized = normalize_chord_symbol(chord)
        print(f"  {chord:15} -> {normalized}")
    print()

    # Example 2: Extract chords from lines
    print("2. Extract Chords from Tab Lines")
    print("-" * 40)
    lines = [
        "Verse: C F G",
        "Em Am F G",
        "Chorus: C Dm Em",
        "F G C",
    ]
    chords_by_line = extract_chords_from_lines(lines)
    for line, chords in zip(lines, chords_by_line):
        print(f"  {line:20} -> {chords}")
    print()

    # Example 3: Extract progressions by line
    print("3. Extract Progressions")
    print("-" * 40)
    progressions = extract_progressions_by_line(lines)
    for i, prog in enumerate(progressions, 1):
        print(f"  Progression {i}: {prog}")
    print()

    # Example 4: Analyze a song
    print("4. Song Analysis")
    print("-" * 40)
    song_lines = [
        "Verse 1:",
        "C F G",
        "C F G",
        "Chorus:",
        "Em Am",
        "F G C",
        "Verse 2:",
        "C F G",
        "Am F G",
    ]

    result = analyze_song(
        song_id=1,
        song_title="Example Song",
        artist_id=1,
        album_id=1,
        lines=song_lines,
    )

    print(f"  Song: {result.song_title}")
    print(f"  Artist ID: {result.artist_id}")
    print(f"  Album ID: {result.album_id}")
    print(f"  Progressions found: {len(result.progressions)}")
    print(f"  Unique chords: {sorted(result.unique_chords)}")
    print(f"  Chord frequency: {result.chord_frequency}")
    print()

    # Example 5: Detect key changes
    print("5. Key Change Detection")
    print("-" * 40)
    key_changes = detect_key_changes(result.progressions)
    print(f"  Potential key changes at positions: {key_changes}")
    print()

    # Example 6: Aggregate analytics
    print("6. Aggregate Analytics")
    print("-" * 40)
    # Create multiple song results for aggregation
    song2_lines = [
        "Dm Am",
        "Dm Am",
        "Dm Em F G",
    ]
    result2 = analyze_song(
        song_id=2,
        song_title="Another Song",
        artist_id=1,
        album_id=1,
        lines=song2_lines,
    )

    analytics = aggregate_analytics([result, result2], top_n=5)
    print("  Most common progressions:")
    for prog, count in analytics.most_common_progressions[:3]:
        print(f"    {prog:20} (count: {count})")
    print()
    print("  Most common chords:")
    for chord, count in analytics.most_common_chords:
        print(f"    {chord:10} (frequency: {count})")
    print()

    # Example 7: JSON serialization
    print("7. Analytics Serialization")
    print("-" * 40)
    from musiclib.chord_analysis import analytics_to_json, analytics_from_json

    json_str = analytics_to_json(analytics)
    print(f"  JSON representation (first 200 chars):")
    print(f"  {json_str[:200]}...")
    print()

    # Deserialize and verify
    restored = analytics_from_json(json_str)
    print(f"  Restored analytics - Top chord: {restored.most_common_chords[0]}")
    print()

    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
