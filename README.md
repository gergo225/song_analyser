# Music Library with Chord Analysis

A Flask-based music library application with advanced chord analysis and analytics capabilities. The application scrapes chord tabs from UltimateGuitar, normalizes chord progressions, and provides comprehensive analytics on chord usage patterns, progression frequencies, and more.

## Features

- **Web Scraping**: Automated ingestion of chord tabs from UltimateGuitar
- **Chord Normalization**: Intelligent parsing and normalization of chord symbols
- **Analytics Engine**: Compute chord frequency, progression patterns, and trends
- **Caching Layer**: Store analytics results for fast retrieval
- **Web Interface**: Browse and visualize chord analytics at `/analytics`
- **CLI Tools**: Command-line interface for data management and analysis

## Requirements

- **Python**: 3.10 or higher (tested with Python 3.12)
- **Database**: SQLite (default) or any SQLAlchemy-compatible database
- **Dependencies**: See `requirements.txt`

## Local Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <project-directory>
```

### 2. Create and Activate Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate on Linux/Mac
source .venv/bin/activate

# Activate on Windows
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The following packages will be installed:
- Flask (>=3.0) - Web framework
- Flask-SQLAlchemy (>=3.1) - Database ORM
- SQLAlchemy (>=2.0) - Database toolkit
- python-dotenv (>=1.0) - Environment configuration
- requests (>=2.31) - HTTP library for scraping
- beautifulsoup4 (>=4.12) - HTML parsing

### 4. Initialize the Database

```bash
python app.py init-db
```

This creates the SQLite database at `instance/app.db` with the following tables:
- `artists` - Artist information
- `albums` - Album metadata
- `songs` - Song details
- `chord_lines` - Parsed chord lines per song
- `cached_analytics_metadata` - Stored analytics results

### 5. (Optional) Configure Environment Variables

Create a `.env` file in the project root for custom configuration:

```bash
# Database (optional - defaults to instance/app.db)
DATABASE_URL=sqlite:///instance/app.db

# Web server settings (optional)
HOST=127.0.0.1
PORT=5000
FLASK_DEBUG=0

# Application secret key (recommended for production)
SECRET_KEY=your-secret-key-here
```

## Running the Application

### Start the Web Server

```bash
python app.py
# or explicitly
python app.py run
```

The application will start on `http://127.0.0.1:5000` by default.

**Available Endpoints:**
- `GET /` - API status endpoint
- `GET /analytics` - Chord analytics dashboard
- `GET /analytics/overall` - Overall chord statistics
- `GET /analytics/album/<id>` - Album-specific analytics
- `GET /analytics/song/<id>` - Song-specific analytics

## Data Ingestion

### Scrape Taylor Swift Tabs

The application includes a built-in scraper for Taylor Swift chord tabs from UltimateGuitar:

```bash
# Basic scrape (respects 1s rate limit)
python app.py scrape-ug-taylor-swift

# Limit number of tabs
python app.py scrape-ug-taylor-swift --limit 50

# Control pagination
python app.py scrape-ug-taylor-swift --max-pages 5

# Adjust rate limiting (seconds between requests)
python app.py scrape-ug-taylor-swift --sleep 2.0

# Force re-scrape existing songs
python app.py scrape-ug-taylor-swift --force

# Skip automatic analytics computation
python app.py scrape-ug-taylor-swift --no-analytics
```

**Expected Output:**
```
Scraping Taylor Swift tabs from UltimateGuitar...
  Page 1: Found 50 tabs
  Page 2: Found 50 tabs
  ...
Created: 45 songs
Updated: 5 songs
Skipped: 0 songs
Computing overall analytics...
Overall analytics computed: songs=45 progressions=238 unique_chords=52
```

### Dataset Caveats

- **Source**: Currently configured for Taylor Swift tabs from UltimateGuitar
- **Rate Limiting**: Default 1 second between requests (configurable with `--sleep`)
- **Duplicates**: Multiple versions of the same song may exist with different chord interpretations
- **Quality**: Tab quality varies based on user submissions; some tabs may be incomplete or inaccurate
- **Chord Format**: Supports UltimateGuitar's `[ch]chord[/ch]` format
- **Legal**: Respect UltimateGuitar's terms of service and rate limits

## Chord Analytics

### Compute Analytics

The application provides several commands to compute and cache chord analytics:

#### Overall Analytics (All Songs)

```bash
# Compute analytics for all songs in database
python app.py compute-chord-analytics --overall

# Force recomputation (bypass cache)
python app.py compute-chord-analytics --overall --force
```

**Output Example:**
```
Overall analytics computed: songs=45 progressions=238 unique_chords=52
```

#### Album Analytics

```bash
# Analyze specific album (by ID)
python app.py compute-chord-analytics --album 5

# Analyze all albums
python app.py compute-chord-analytics --all-albums

# Force recomputation
python app.py compute-chord-analytics --all-albums --force
```

**Output Example:**
```
Album 5: songs=12 progressions=64 unique_chords=28
```

#### Song Analytics

```bash
# Analyze specific song (by ID)
python app.py compute-chord-analytics --song 123
```

**Output Example:**
```
Analyzed song 123: progressions=8 unique_chords=6
```

### Analytics Data

The analytics engine computes:

1. **Chord Frequency**: How often each chord appears across songs
2. **Progression Patterns**: Common chord progressions (e.g., "C - F - G - Am")
3. **Unique Chords**: Distinct chords used in each scope (song/album/overall)
4. **Progression Frequency**: How often specific progressions occur

**Example Analytics JSON:**
```json
{
  "most_common_chords": [
    {"chord": "C", "count": 145},
    {"chord": "G", "count": 128},
    {"chord": "Am", "count": 98}
  ],
  "most_common_progressions": [
    {"progression": "C - G - Am - F", "count": 18},
    {"progression": "G - D - Em - C", "count": 12}
  ],
  "chord_frequency": {"C": 145, "G": 128, "Am": 98, ...},
  "progression_frequency": {"C - G - Am - F": 18, ...}
}
```

### Refreshing Analytics

Analytics are cached for performance. To refresh:

**Method 1: Force Recomputation**
```bash
# Recompute overall analytics
python app.py compute-chord-analytics --overall --force

# Recompute all albums
python app.py compute-chord-analytics --all-albums --force

# Recompute specific album
python app.py compute-chord-analytics --album 5 --force
```

**Method 2: Clear Cache and Recompute**
```bash
# Delete cached analytics (requires database access)
sqlite3 instance/app.db "DELETE FROM cached_analytics_metadata;"

# Recompute
python app.py compute-chord-analytics --overall
```

**Method 3: Automatic Refresh After Scraping**
```bash
# Scrape new data (automatically computes analytics)
python app.py scrape-ug-taylor-swift
```

## Chord Normalization

The application normalizes chord symbols to canonical form:

| Input | Normalized Output |
|-------|------------------|
| `Cminor` | `Cm` |
| `D♯maj7` | `D#maj7` |
| `Gminor` | `Gm` |
| `A-7` | `Am7` |
| `Fsus4` | `Fsus4` |
| `F/G` | `F/G` (inversion) |
| `Bdim` | `Bdim` |
| `Caug` | `Caug` |

Supported features:
- Major, minor, augmented, diminished chords
- 7th, 9th, 11th, 13th extensions
- Suspended chords (sus2, sus4)
- Inversions (e.g., C/G)
- Accidentals (sharp #/♯, flat b/♭)
- Complex jazz chords (maj7, m7b5, etc.)

## Testing

### Integration Tests

Run the full integration test suite:

```bash
python test_integration.py
```

**Expected Output:**
```
======================================================================
Chord Analysis Engine - Integration Test
======================================================================

1. Initializing database...
2. Creating test data...
3. Testing chord analysis...
   Song 1: 4 progressions, 4 unique chords
   Song 2: 3 progressions, 4 unique chords
4. Testing analytics retrieval...
   Retrieved song 1 analysis: Song 1
5. Computing overall analytics...
   Overall: 2 songs, 7 progressions, 5 unique chords
6. Testing overall analytics retrieval...
   Top 3 chords: [('C', 4), ('G', 4), ('F', 3)]
7. Testing JSON serialization...
   JSON size: 836 bytes
   JSON round-trip successful

======================================================================
All integration tests passed!
======================================================================
```

### Chord Analysis Examples

Run the chord analysis demonstration:

```bash
python test_chord_analysis_example.py
```

This demonstrates:
- Chord normalization across various formats
- Line-by-line chord extraction
- Song-level progression analysis
- Key change detection
- Aggregate analytics computation

## Project Structure

```
.
├── app.py                          # CLI entry point and Flask app runner
├── requirements.txt                # Python dependencies
├── musiclib/                       # Main application package
│   ├── __init__.py                 # Flask app factory
│   ├── config.py                   # Configuration classes
│   ├── extensions.py               # Flask extensions (SQLAlchemy)
│   ├── models.py                   # Database models
│   ├── db_utils.py                 # Database utilities
│   ├── cli.py                      # CLI command registration
│   ├── chord_analysis.py           # Core chord analysis logic
│   ├── scrapers/                   # Web scraping modules
│   │   └── ultimate_guitar.py      # UltimateGuitar scraper
│   ├── services/                   # Business logic layer
│   │   ├── chord_analytics.py      # Analytics service
│   │   └── ultimate_guitar_sync.py # Scraper integration
│   ├── web/                        # Web blueprints
│   │   └── analytics.py            # Analytics endpoints
│   ├── templates/                  # Jinja2 templates
│   │   └── analytics/              # Analytics UI templates
│   └── static/                     # Static assets (CSS, JS)
│       ├── css/style.css
│       └── js/tables.js
├── instance/                       # Instance folder (created on init)
│   └── app.db                      # SQLite database
├── test_integration.py             # Integration test suite
└── test_chord_analysis_example.py  # Chord analysis examples
```

## Development Workflow

### Typical Workflow for New Data

1. **Initialize Database** (first time only)
   ```bash
   python app.py init-db
   ```

2. **Scrape Data**
   ```bash
   python app.py scrape-ug-taylor-swift --limit 100
   ```

3. **Verify Data**
   ```bash
   sqlite3 instance/app.db "SELECT COUNT(*) FROM song;"
   ```

4. **Compute Analytics**
   ```bash
   python app.py compute-chord-analytics --overall
   ```

5. **Launch Web Interface**
   ```bash
   python app.py run
   ```

6. **View Analytics**
   - Open browser to `http://127.0.0.1:5000/analytics`

### Database Management

**View Database Schema:**
```bash
sqlite3 instance/app.db ".schema"
```

**Query Songs:**
```bash
sqlite3 instance/app.db "SELECT id, title FROM songs LIMIT 10;"
```

**Check Analytics Cache:**
```bash
sqlite3 instance/app.db "SELECT subject_type, subject_id, metric, created_at FROM cached_analytics_metadata;"
```

**Clear All Data (Destructive):**
```bash
rm -f instance/app.db
python app.py init-db
```

## Troubleshooting

### Database Locked Error

If you see "database is locked" errors:
```bash
# Stop all Python processes accessing the database
pkill -f "python app.py"

# Or restart with a fresh database
rm -f instance/app.db
python app.py init-db
```

### Scraper Rate Limited

If UltimateGuitar blocks requests:
```bash
# Increase sleep time between requests
python app.py scrape-ug-taylor-swift --sleep 3.0
```

### Missing Dependencies

If imports fail:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use

If port 5000 is occupied:
```bash
# Use different port via environment variable
PORT=5001 python app.py run
```

## Additional Documentation

- **[CHORD_ANALYSIS.md](CHORD_ANALYSIS.md)** - Detailed documentation on the chord analysis engine, API usage, and technical implementation
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Development summary and implementation details
- **[IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md)** - Feature checklist and project status

## Future Enhancements

- [ ] Support for additional artists and music sources
- [ ] Key detection and harmonic function analysis
- [ ] Temporal analysis (chord usage trends over time)
- [ ] Export analytics to CSV/JSON
- [ ] REST API for programmatic access
- [ ] Real-time analytics updates
- [ ] Chord chart visualization
- [ ] Machine learning for pattern detection

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

For issues, questions, or contributions, please [add contact information or issue tracker URL here].
