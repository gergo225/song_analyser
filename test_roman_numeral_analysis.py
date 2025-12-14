from __future__ import annotations

from musiclib.chord_analysis import analyze_song


def test_analyze_song_roman_numerals_progression() -> None:
    lines = ["I", "V", "vi", "IV"]
    result = analyze_song(
        song_id=1,
        song_title="Roman Numeral Test",
        artist_id=1,
        album_id=None,
        lines=lines,
        tab_type="roman_numerals",
    )

    assert len(result.progressions) == 1
    assert list(result.progressions[0].chords) == lines
    assert "vi" in result.unique_chords


if __name__ == "__main__":
    test_analyze_song_roman_numerals_progression()
    print("Roman numeral analysis test passed")
