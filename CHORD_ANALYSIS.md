# Chord Analysis Engine

A comprehensive chord analysis and analytics system for music library applications. The engine parses raw chord/tab text into normalized chord progressions and computes various analytics including pattern detection, frequency analysis, and trend identification.

## Features

### 1. Chord Parsing & Normalization
- Parse raw UltimateGuitar format tabs with `[ch]chord[/ch]` markers
- Normalize chord symbols to canonical form (e.g., `Cminor` → `Cm`, `D♯maj7` → `D#maj7`)
- Support for complex chords: suspended, augmented, diminished, inversions, etc.
- Extract chord progressions from tab lines

### 2. Song-Level Analysis
- Extract progressions by line/measure
- Compute unique chords per song
- Track chord frequency within a song
- Detect potential key changes

### 3. Aggregate Analytics
- **Overall Statistics**: Most common progressions and chords across all songs
- **Album Analytics**: Per-album chord usage and progression patterns
- **Frequency Analysis**: Detailed chord and progression frequency counts
- **Caching**: Store results in `CachedAnalyticsMetadata` table for fast retrieval

### 4. Integration
- Hook into scraper workflow to auto-compute analytics after data ingestion
- CLI commands for manual analytics computation
- Support for force re-computation

## Core Components

### `musiclib/chord_analysis.py`
Core analysis functions:
- `normalize_chord_symbol(symbol)` - Normalize chord names
- `extract_chords_from_raw_tab(raw_tab)` - Extract chords from raw text
- `extract_chords_from_lines(lines)` - Extract chords from individual lines
- `analyze_song(...)` - Full song analysis
- `aggregate_analytics(results)` - Aggregate multiple song analyses
- `aggregate_by_album(results)` - Group analytics by album
- `detect_key_changes(progressions)` - Detect key change points

### `musiclib/services/chord_analytics.py`
Database service layer:
- `compute_and_cache_song_analytics(song_id)` - Analyze and cache single song
- `compute_and_cache_overall_analytics()` - Analyze all songs
- `compute_and_cache_album_analytics(album_id)` - Analyze albums
- `get_overall_analytics()` - Retrieve cached overall analytics
- `get_album_analytics(album_id)` - Retrieve cached album analytics
- `get_song_analysis(song_id)` - Retrieve cached song analysis

## Data Model

### ChordProgression
Represents a sequence of chords (typically one per measure/line):
```python
progression = ChordProgression(chords=('C', 'F', 'G'))
```

### ChordAnalysisResult
Analysis result for a single song:
- `progressions`: Tuple of ChordProgression objects
- `unique_chords`: Sorted list of unique chords in song
- `chord_frequency`: Dict mapping chords to their frequency

### AggregateChordAnalytics
Aggregated analytics across multiple songs:
- `most_common_progressions`: List of (progression, count) tuples
- `most_common_chords`: List of (chord, count) tuples
- `chord_frequency`: Dict of all chord frequencies
- `progression_frequency`: Dict of progression frequencies

### CachedAnalyticsMetadata Table
Stores computed analytics:
- `subject_type`: 'song', 'album', or 'global'
- `subject_id`: ID of the subject (or 0 for global)
- `metric`: Type of metric (e.g., 'chord_analytics.song')
- `payload`: JSON-serialized analytics data

## Usage

### CLI Commands

#### Compute Overall Analytics
```bash
# Compute analytics for all songs
python app.py compute-chord-analytics --overall

# Force recomputation (skip cache)
python app.py compute-chord-analytics --overall --force
```

#### Compute Album Analytics
```bash
# Analyze specific album
python app.py compute-chord-analytics --album 5

# Analyze all albums
python app.py compute-chord-analytics --all-albums
```

#### Compute Song Analytics
```bash
# Analyze specific song
python app.py compute-chord-analytics --song 123
```

#### Scrape with Auto-Analytics
```bash
# Scrape and compute analytics
python app.py scrape-ug-taylor-swift

# Scrape without analytics
python app.py scrape-ug-taylor-swift --no-analytics
```

### Python API

#### Basic Song Analysis
```python
from musiclib.chord_analysis import analyze_song

result = analyze_song(
    song_id=1,
    song_title="Song Title",
    artist_id=1,
    album_id=1,
    lines=["C F G", "Am F G", "C"],
)

print(result.unique_chords)  # ('Am', 'C', 'F', 'G')
print(result.chord_frequency)  # {'C': 2, 'F': 2, 'G': 2, 'Am': 1}
```

#### Database Service
```python
from musiclib.services.chord_analytics import (
    compute_and_cache_overall_analytics,
    get_overall_analytics,
)

# Compute analytics
result = compute_and_cache_overall_analytics(force=True)
print(f"Analyzed {result.songs_analyzed} songs")

# Retrieve cached analytics
analytics = get_overall_analytics()
if analytics:
    for prog, count in analytics.most_common_progressions[:5]:
        print(f"{prog}: {count} occurrences")
```

### Chord Normalization Examples
```python
from musiclib.chord_analysis import normalize_chord_symbol

normalize_chord_symbol("Cminor")        # → "Cm"
normalize_chord_symbol("D♯maj7")        # → "D#maj7"
normalize_chord_symbol("F/G")           # → "F/G"
normalize_chord_symbol("Gsus4")         # → "Gsus4"
normalize_chord_symbol("Bbm7b5")        # → "Bbm7b5"
normalize_chord_symbol("A-7")           # → "Am7"
```

## Analytics Storage

Analytics are stored in the `CachedAnalyticsMetadata` table with the following structure:

```json
{
  "most_common_progressions": [
    {"progression": "C - F - G", "count": 15},
    {"progression": "Am - F - G - C", "count": 12}
  ],
  "most_common_chords": [
    {"chord": "C", "count": 123},
    {"chord": "G", "count": 89}
  ],
  "chord_frequency": {"C": 123, "G": 89, "Am": 67, ...},
  "progression_frequency": {"C - F - G": 15, "Am - F - G - C": 12, ...}
}
```

## Key Patterns & Trends

The engine detects:

1. **Chord Frequency**: Identifies most commonly used chords
2. **Progressions**: Tracks recurring chord sequences
3. **Key Changes**: Heuristic detection based on chord similarity
4. **Temporal Patterns**: (Future) Track evolution over albums/eras

## Future Enhancements

- [ ] Per-artist analytics breakdown
- [ ] Temporal analysis (by era/year)
- [ ] Harmonic function detection (I, IV, V, vi, etc.)
- [ ] Modulation pattern analysis
- [ ] Relation to song key/scale
- [ ] Genre-specific chord patterns
- [ ] Statistical significance tests
- [ ] Visualization endpoints

## Testing

Run the example:
```bash
python test_chord_analysis_example.py
```

This demonstrates:
- Chord normalization
- Line-by-line chord extraction
- Song analysis
- Progression detection
- Key change detection
- Analytics aggregation
- JSON serialization/deserialization

## Performance Notes

- Songs with many progressions may slow analytics computation
- Analytics are cached to avoid repeated computation
- Use `--force` flag to bypass cache when needed
- Album analytics can be computed independently or as batch
