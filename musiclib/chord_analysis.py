from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Sequence

_NOTE_RE = re.compile(r"^\s*([A-Ga-g])\s*([#b♯♭]?)\s*(.*)$")
_CHORD_CHORD_RE = re.compile(
    r"\[ch\]([^\[]*?)\[/ch\]", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class ChordProgression:
    """Represents a sequence of chords (typically one per measure/line)."""
    chords: tuple[str, ...]

    def __str__(self) -> str:
        return " - ".join(self.chords)

    def to_dict(self) -> dict:
        return {"chords": list(self.chords)}

    @classmethod
    def from_dict(cls, data: dict) -> ChordProgression:
        return cls(chords=tuple(data.get("chords", [])))


@dataclass(frozen=True, slots=True)
class ChordAnalysisResult:
    """Analytics result for a song."""
    song_id: int
    song_title: str
    artist_id: int
    album_id: int | None
    progressions: tuple[ChordProgression, ...]
    unique_chords: tuple[str, ...]
    chord_frequency: dict[str, int]


@dataclass(frozen=True, slots=True)
class AggregateChordAnalytics:
    """Aggregated analytics across multiple songs."""
    most_common_progressions: list[tuple[str, int]]
    most_common_chords: list[tuple[str, int]]
    chord_frequency: dict[str, int]
    progression_frequency: dict[str, int]


def normalize_chord_symbol(symbol: str) -> str:
    """Normalize a chord symbol to a canonical form."""
    s = symbol.strip()
    if not s:
        return ""

    s = s.replace("♯", "#").replace("♭", "b")
    s = s.strip("()[]{}")

    if s.upper() in {"NC", "N.C."}:
        return "N.C."

    if "/" in s:
        main, bass = s.split("/", 1)
        main_norm = normalize_chord_symbol(main)
        bass_norm = _normalize_bass_note(bass)
        if main_norm and bass_norm:
            return f"{main_norm}/{bass_norm}"
        return main_norm or bass_norm

    m = _NOTE_RE.match(s)
    if not m:
        return s

    root, accidental, rest = m.groups()
    root = root.upper()
    accidental = accidental.replace("♯", "#").replace("♭", "b")

    rest = rest.strip()
    rest_lower = rest.lower()

    if rest_lower.startswith("minor"):
        rest = "m" + rest[5:]
    elif rest_lower.startswith("min"):
        rest = "m" + rest[3:]
    elif rest.startswith("-"):
        rest = "m" + rest[1:]
    elif rest.startswith("M") and (len(rest) == 1 or rest[1].isdigit()):
        rest = "maj" + rest[1:]

    rest = rest.replace(" ", "")
    return f"{root}{accidental}{rest}"


def _normalize_bass_note(note: str) -> str:
    """Normalize a bass note."""
    m = _NOTE_RE.match(note)
    if not m:
        return note.strip()

    root, accidental, _rest = m.groups()
    root = root.upper()
    accidental = accidental.replace("♯", "#").replace("♭", "b")
    return f"{root}{accidental}"


def extract_chords_from_raw_tab(raw_tab: str) -> list[str]:
    """Extract all chords from raw tab text."""
    chords = [
        normalize_chord_symbol(m.group(1))
        for m in _CHORD_CHORD_RE.finditer(raw_tab)
    ]
    unique = sorted({c for c in chords if c})
    return unique


def extract_chords_from_lines(lines: Sequence[str]) -> list[list[str]]:
    """Extract chords from each line of tab text.
    
    Returns a list of chord lists, one per line.
    """
    result: list[list[str]] = []
    
    for line in lines:
        chords: list[str] = []
        # Look for chord symbols in the line
        for token in re.split(r"\s+", line):
            if not token:
                continue
            norm = normalize_chord_symbol(token)
            # Check if this token looks like a chord
            if norm != token or _NOTE_RE.match(token):
                if norm:
                    chords.append(norm)
        result.append(chords)
    
    return result


def detect_key_changes(progressions: Sequence[ChordProgression]) -> list[int]:
    """Detect likely key changes in a sequence of progressions.
    
    Returns indices where key changes are detected.
    This is a heuristic based on chord frequency changes.
    """
    if len(progressions) < 2:
        return []
    
    changes = []
    all_chords: list[str] = []
    
    for prog in progressions:
        all_chords.extend(prog.chords)
    
    chord_freq = Counter(all_chords)
    
    # Very simple heuristic: detect when majority chord changes significantly
    # This is a basic implementation
    for i in range(1, len(progressions)):
        prev_chords = set(progressions[i - 1].chords)
        curr_chords = set(progressions[i].chords)
        
        # If chord sets differ by more than expected, might be a key change
        overlap = len(prev_chords & curr_chords)
        union_size = len(prev_chords | curr_chords)
        
        if union_size > 0:
            similarity = overlap / union_size
            # If similarity is low, might indicate key change
            if similarity < 0.3 and len(curr_chords) > 0:
                changes.append(i)
    
    return changes


def extract_progressions_by_line(
    lines: Sequence[str],
    min_chords_per_line: int = 1,
) -> list[ChordProgression]:
    """Extract chord progressions from lines (one progression per line).
    
    Args:
        lines: List of tab lines
        min_chords_per_line: Minimum chords needed per line to include it
    
    Returns:
        List of ChordProgression objects
    """
    progressions: list[ChordProgression] = []
    
    chords_by_line = extract_chords_from_lines(lines)
    
    for chord_list in chords_by_line:
        if len(chord_list) >= min_chords_per_line:
            prog = ChordProgression(chords=tuple(chord_list))
            progressions.append(prog)
    
    return progressions


def analyze_song(
    song_id: int,
    song_title: str,
    artist_id: int,
    album_id: int | None,
    lines: Sequence[str],
) -> ChordAnalysisResult:
    """Analyze a song's chord structure.
    
    Args:
        song_id: Database song ID
        song_title: Song title
        artist_id: Artist ID
        album_id: Album ID (if any)
        lines: Parsed tab lines
    
    Returns:
        ChordAnalysisResult with analysis data
    """
    progressions = extract_progressions_by_line(lines)
    
    all_chords: list[str] = []
    for prog in progressions:
        all_chords.extend(prog.chords)
    
    unique_chords = sorted(set(all_chords))
    chord_freq = dict(Counter(all_chords))
    
    return ChordAnalysisResult(
        song_id=song_id,
        song_title=song_title,
        artist_id=artist_id,
        album_id=album_id,
        progressions=tuple(progressions),
        unique_chords=tuple(unique_chords),
        chord_frequency=chord_freq,
    )


def aggregate_analytics(
    results: Sequence[ChordAnalysisResult],
    top_n: int = 20,
) -> AggregateChordAnalytics:
    """Aggregate analytics across multiple song analyses.
    
    Args:
        results: Sequence of ChordAnalysisResult objects
        top_n: Number of top items to return
    
    Returns:
        Aggregated analytics
    """
    all_chord_freq: dict[str, int] = defaultdict(int)
    progression_freq: dict[str, int] = defaultdict(int)
    
    for result in results:
        for chord, freq in result.chord_frequency.items():
            all_chord_freq[chord] += freq
        
        for prog in result.progressions:
            prog_str = str(prog)
            progression_freq[prog_str] += 1
    
    most_common_chords = Counter(all_chord_freq).most_common(top_n)
    most_common_progressions = Counter(progression_freq).most_common(top_n)
    
    return AggregateChordAnalytics(
        most_common_progressions=most_common_progressions,
        most_common_chords=most_common_chords,
        chord_frequency=dict(all_chord_freq),
        progression_frequency=progression_freq,
    )


def aggregate_by_album(
    results: Sequence[ChordAnalysisResult],
    top_n: int = 10,
) -> dict[int, AggregateChordAnalytics]:
    """Aggregate analytics grouped by album.
    
    Args:
        results: Sequence of ChordAnalysisResult objects
        top_n: Number of top items to return per album
    
    Returns:
        Dict mapping album_id to AggregateChordAnalytics
    """
    by_album: dict[int, list[ChordAnalysisResult]] = defaultdict(list)
    
    for result in results:
        if result.album_id is not None:
            by_album[result.album_id].append(result)
    
    return {
        album_id: aggregate_analytics(songs, top_n=top_n)
        for album_id, songs in by_album.items()
    }


def analytics_to_json(analytics: AggregateChordAnalytics) -> str:
    """Serialize analytics to JSON."""
    data = {
        "most_common_progressions": [
            {"progression": prog, "count": count}
            for prog, count in analytics.most_common_progressions
        ],
        "most_common_chords": [
            {"chord": chord, "count": count}
            for chord, count in analytics.most_common_chords
        ],
        "chord_frequency": analytics.chord_frequency,
        "progression_frequency": analytics.progression_frequency,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def analytics_from_json(json_str: str) -> AggregateChordAnalytics:
    """Deserialize analytics from JSON."""
    data = json.loads(json_str)
    
    most_common_progressions = [
        (item["progression"], item["count"])
        for item in data.get("most_common_progressions", [])
    ]
    most_common_chords = [
        (item["chord"], item["count"])
        for item in data.get("most_common_chords", [])
    ]
    chord_frequency = data.get("chord_frequency", {})
    progression_frequency = data.get("progression_frequency", {})
    
    return AggregateChordAnalytics(
        most_common_progressions=most_common_progressions,
        most_common_chords=most_common_chords,
        chord_frequency=chord_frequency,
        progression_frequency=progression_frequency,
    )
