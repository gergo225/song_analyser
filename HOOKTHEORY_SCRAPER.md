# Hooktheory Scraper

## Overview

This scraper extracts Taylor Swift songs with Roman numeral chord progressions from Hooktheory.com. The scraper is designed to:

- Search for Taylor Swift songs on Hooktheory
- Extract Roman numerals from SVG text elements (rendered via JavaScript)
- Identify and store the song key
- Store data in SQLite via existing Song and ChordLine models
- Support incremental scraping (avoid duplicates)

## Requirements

### System Requirements

The scraper uses Selenium with Chrome/Chromium for JavaScript rendering:

```bash
# Install Chrome/Chromium and chromedriver
sudo apt-get update
sudo apt-get install -y chromium chromium-driver

# Install required libraries
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libatspi2.0-0 libxcomposite1 libxdamage1
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- selenium>=4.15
- webdriver-manager>=4.0
- beautifulsoup4>=4.12
- lxml>=4.9
- requests>=2.31

## Usage

### Basic Scraping

```bash
# Initialize database (first time only)
python app.py init-db

# Scrape Taylor Swift songs from Hooktheory
python app.py scrape-hooktheory-taylor-swift
```

### Command Options

```bash
# Limit number of songs
python app.py scrape-hooktheory-taylor-swift --limit 10

# Adjust rate limiting (seconds between requests)
python app.py scrape-hooktheory-taylor-swift --sleep 3.0

# Force re-scrape existing songs
python app.py scrape-hooktheory-taylor-swift --force

# Combine options
python app.py scrape-hooktheory-taylor-swift --limit 50 --sleep 2.0 --force
```

### Testing

Run the test script to verify the scraper's data storage functionality:

```bash
python test_hooktheory_scraper.py
```

This test demonstrates:
- Song metadata storage (title, key, source, URL)
- Roman numeral chord progression storage
- Incremental scraping (duplicate detection)
- Proper sequencing of Roman numerals

## Data Format

### Song Table

Each scraped song is stored with:
- `title`: Song title (e.g., "Love Story")
- `key`: Musical key (e.g., "D major", "G minor")
- `artist_id`: Foreign key to Taylor Swift artist
- `source`: Always "hooktheory"
- `source_url`: Full Hooktheory URL
- `tab_type`: Always "roman_numerals"
- `last_scraped_at`: Timestamp of last scrape

### ChordLine Table

Roman numerals are stored as individual chord lines:
- `song_id`: Foreign key to song
- `line_number`: Sequential position (1, 2, 3, ...)
- `content`: Roman numeral (e.g., "I", "V", "vi", "IV")

Example progression for "Love Story" (D major):
```
Line 1: I
Line 2: V
Line 3: vi
Line 4: IV
Line 5: I
Line 6: V
Line 7: vi
Line 8: IV
```

## Scraper Architecture

### Key Components

1. **HooktheoryScraper class** (`musiclib/scrapers/hooktheory.py`)
   - Manages Selenium driver initialization
   - Handles HTTP requests with retry logic
   - Extracts song data from Hooktheory pages

2. **search_taylor_swift_songs()**
   - Fetches artist page
   - Extracts all song URLs

3. **extract_song_data(url)**
   - Uses Selenium to render JavaScript
   - Extracts title from H1 or page title
   - Extracts key from metadata, title, or breadcrumbs
   - Extracts Roman numerals from SVG `<tspan class="times">` elements

4. **scrape_taylor_swift()**
   - Main scraping loop
   - Checks for existing songs (incremental scraping)
   - Stores songs and chord lines in database

### Roman Numeral Extraction

The scraper looks for Roman numerals in SVG elements:

```html
<g data-type="chord-label-rel-...">
  <text ...>
    <tspan class="times">I</tspan>
  </text>
</g>
```

Valid Roman numeral patterns:
- Basic: `I`, `ii`, `V`, `vi`
- With accidentals: `#IV`, `bVII`
- With qualities: `vi°`, `viiø`, `V+`
- With extensions: `V7`, `ii7`
- With inversions: `I/iii`

### Key Extraction

The scraper attempts to find the musical key from multiple sources:
1. Meta tags (`<meta name="key" content="...">`)
2. Span/div elements with class "key"
3. H1 title (e.g., "Love Story in D major")
4. Breadcrumb navigation
5. Fallback: empty string if not found

Keys are normalized to format: `"D major"`, `"G minor"`, `"F# major"`, etc.

## Incremental Scraping

The scraper checks for existing songs by `source_url`:

```python
existing = Song.query.filter_by(
    source="hooktheory",
    source_url=url
).first()
```

- If song exists and `--force` not used: Skip
- If song exists and `--force` used: Update key and replace chord lines
- If song doesn't exist: Create new song and chord lines

## Rate Limiting

Default: 2 seconds between requests (configurable with `--sleep`)

The scraper includes:
- Retry logic (3 attempts per request)
- Exponential backoff for 429 (rate limited) responses
- Polite user agent string
- Reduced sleep time (50%) for skipped songs

## Error Handling

The scraper gracefully handles:
- Selenium initialization failures (falls back to requests)
- HTTP errors (logs and continues)
- Missing data (logs error, increments error count)
- Rate limiting (waits and retries)
- Connection timeouts (retries with backoff)

## Limitations

1. **JavaScript Dependency**: Requires Selenium to render SVG elements
2. **Environment-Specific**: Chrome/Chromium setup varies by platform
3. **Single Artist**: Currently hardcoded for Taylor Swift
4. **No API**: Scrapes HTML (subject to website changes)
5. **Rate Limits**: Respects Hooktheory's rate limiting

## Troubleshooting

### Selenium Not Working

If you see: `Warning: Could not initialize Chrome driver`

1. Check Chrome/Chromium installation:
   ```bash
   chromium-browser --version
   chromedriver --version
   ```

2. Install missing dependencies:
   ```bash
   sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0
   ```

3. Try manual driver installation:
   ```bash
   pip install webdriver-manager
   ```

### No Roman Numerals Found

If songs show 0 Roman numerals:
- Selenium may not be properly configured
- JavaScript may not have fully rendered
- Increase wait time in scraper (currently 2 seconds)

### Rate Limiting

If you encounter 429 errors:
```bash
# Increase sleep time
python app.py scrape-hooktheory-taylor-swift --sleep 5.0
```

## Future Enhancements

- [ ] Support for multiple artists
- [ ] Parallel scraping with thread pool
- [ ] Retry failed songs automatically
- [ ] Export scraped data to CSV/JSON
- [ ] Scrape additional metadata (tempo, time signature)
- [ ] Support for chord diagrams/voicings
- [ ] API authentication support
- [ ] Progress bar with tqdm

## License

Same as parent project.
