from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import delete, select

from ..db_utils import init_db
from ..extensions import db
from ..models import Artist, CachedAnalyticsMetadata, ChordLine, Song
from ..scrapers.ultimate_guitar import UltimateGuitarScraper
from .chord_analytics import compute_and_cache_overall_analytics


@dataclass(frozen=True, slots=True)
class UltimateGuitarScrapeResult:
    seen_tabs: int
    created_songs: int
    updated_songs: int
    skipped_songs: int


def scrape_taylor_swift_chords_to_db(
    *,
    max_pages: int | None = None,
    limit: int | None = None,
    sleep_seconds: float = 1.0,
    force: bool = False,
    commit_every: int = 25,
    compute_analytics: bool = True,
) -> UltimateGuitarScrapeResult:
    init_db()
    scraper = UltimateGuitarScraper(sleep_seconds=sleep_seconds)

    artist = _get_or_create_artist("Taylor Swift")

    seen_tabs = 0
    created_songs = 0
    updated_songs = 0
    skipped_songs = 0

    processed_song_titles: set[str] = set()

    for tab in scraper.iter_taylor_swift_chords(max_pages=max_pages, limit=limit):
        seen_tabs += 1

        if not force and tab.song_title in processed_song_titles:
            continue
        processed_song_titles.add(tab.song_title)

        song = (
            db.session.execute(
                select(Song).where(
                    Song.artist_id == artist.id,
                    Song.title == tab.song_title,
                )
            )
            .scalar_one_or_none()
        )

        if song is None:
            song = Song(
                artist_id=artist.id,
                title=tab.song_title,
                source="ultimate_guitar",
                source_url=tab.tab_url,
                tab_type=tab.tab_type,
            )
            db.session.add(song)
            db.session.flush()
            created_songs += 1
        else:
            if not force and song.raw_tab and song.source_url == tab.tab_url:
                skipped_songs += 1
                continue

            song.source = song.source or "ultimate_guitar"
            song.source_url = tab.tab_url
            song.tab_type = tab.tab_type

        ug_tab = scraper.fetch_tab(tab.tab_url)
        song.raw_tab = ug_tab.raw_content
        song.last_scraped_at = db.func.now()

        _replace_chord_lines(song_id=song.id, lines=ug_tab.lines)
        _upsert_song_chord_metadata(
            song_id=song.id,
            tab_url=ug_tab.tab_url,
            chords=ug_tab.normalized_chords,
        )

        updated_songs += 1

        if seen_tabs % commit_every == 0:
            db.session.commit()

    db.session.commit()
    
    if compute_analytics and updated_songs > 0:
        compute_and_cache_overall_analytics(force=True, commit=True)

    return UltimateGuitarScrapeResult(
        seen_tabs=seen_tabs,
        created_songs=created_songs,
        updated_songs=updated_songs,
        skipped_songs=skipped_songs,
    )


def _get_or_create_artist(name: str) -> Artist:
    artist = (
        db.session.execute(select(Artist).where(Artist.name == name))
        .scalar_one_or_none()
    )
    if artist is not None:
        return artist

    artist = Artist(name=name)
    db.session.add(artist)
    db.session.flush()
    return artist


def _replace_chord_lines(*, song_id: int, lines: list[str]) -> None:
    db.session.execute(delete(ChordLine).where(ChordLine.song_id == song_id))

    for idx, line in enumerate(lines, start=1):
        db.session.add(ChordLine(song_id=song_id, line_number=idx, content=line))


def _upsert_song_chord_metadata(
    *,
    song_id: int,
    tab_url: str,
    chords: list[str],
) -> None:
    payload = json.dumps(
        {"tab_url": tab_url, "normalized_chords": chords},
        ensure_ascii=False,
    )

    row = db.session.execute(
        select(CachedAnalyticsMetadata).where(
            CachedAnalyticsMetadata.subject_type == "song",
            CachedAnalyticsMetadata.subject_id == song_id,
            CachedAnalyticsMetadata.metric == "ultimate_guitar.normalized_chords",
        )
    ).scalar_one_or_none()

    if row is None:
        row = CachedAnalyticsMetadata(
            subject_type="song",
            subject_id=song_id,
            metric="ultimate_guitar.normalized_chords",
            payload=payload,
        )
        db.session.add(row)
    else:
        row.payload = payload
