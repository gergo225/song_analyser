from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from flask import Blueprint, abort, render_template
from sqlalchemy import func, select

from ..extensions import db
from ..models import Album, Artist, CachedAnalyticsMetadata, Song
from ..services.chord_analytics import (
    get_album_analytics,
    get_overall_analytics,
    get_song_analysis,
)


analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@dataclass(frozen=True, slots=True)
class FrequencyBarItem:
    label: str
    count: int
    pct: float
    bar_pct: float


def _safe_json_loads(payload: str) -> dict[str, Any]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _get_cached_metadata(
    *, subject_type: str, subject_id: int, metric: str
) -> CachedAnalyticsMetadata | None:
    return db.session.execute(
        select(CachedAnalyticsMetadata).where(
            CachedAnalyticsMetadata.subject_type == subject_type,
            CachedAnalyticsMetadata.subject_id == subject_id,
            CachedAnalyticsMetadata.metric == metric,
        )
    ).scalar_one_or_none()


def _frequency_bars(
    items: list[tuple[str, int]],
    *,
    total: int,
) -> list[FrequencyBarItem]:
    if not items:
        return []

    max_count = max((count for _label, count in items), default=0) or 1
    total = total or 1

    result: list[FrequencyBarItem] = []
    for label, count in items:
        result.append(
            FrequencyBarItem(
                label=label,
                count=count,
                pct=(count / total) * 100.0,
                bar_pct=(count / max_count) * 100.0,
            )
        )
    return result


@analytics_bp.get("/")
def index() -> str:
    overall_meta = _get_cached_metadata(
        subject_type="global",
        subject_id=0,
        metric="chord_analytics.overall",
    )

    overall_summary: dict[str, Any] | None = None
    overall_top_chords: list[FrequencyBarItem] = []
    overall_top_progressions: list[FrequencyBarItem] = []

    if overall_meta is not None:
        payload_data = _safe_json_loads(overall_meta.payload)
        overall_summary = {
            "songs_analyzed": int(payload_data.get("songs_analyzed", 0)),
            "progressions_found": int(payload_data.get("progressions_found", 0)),
            "unique_chords": int(payload_data.get("unique_chords", 0)),
            "computed_at": overall_meta.computed_at_utc,
        }

        analytics = get_overall_analytics()
        if analytics is not None:
            total_chords = sum(analytics.chord_frequency.values())
            total_progressions = sum(analytics.progression_frequency.values())
            overall_top_chords = _frequency_bars(
                analytics.most_common_chords,
                total=total_chords,
            )
            overall_top_progressions = _frequency_bars(
                analytics.most_common_progressions,
                total=total_progressions,
            )

    library_counts = db.session.execute(
        select(
            select(func.count(Artist.id)).scalar_subquery(),
            select(func.count(Album.id)).scalar_subquery(),
            select(func.count(Song.id)).scalar_subquery(),
        )
    ).one()

    counts = {
        "artists": int(library_counts[0] or 0),
        "albums": int(library_counts[1] or 0),
        "songs": int(library_counts[2] or 0),
    }

    return render_template(
        "analytics/index.html",
        counts=counts,
        overall_summary=overall_summary,
        overall_top_chords=overall_top_chords,
        overall_top_progressions=overall_top_progressions,
    )


@analytics_bp.get("/songs")
def songs() -> str:
    rows = db.session.execute(
        select(Song, Artist, Album)
        .join(Artist, Song.artist_id == Artist.id)
        .outerjoin(Album, Song.album_id == Album.id)
        .order_by(Song.title)
    ).all()

    songs_list: list[Song] = [r[0] for r in rows]
    metadata: dict[int, tuple[Artist, Album | None]] = {
        r[0].id: (r[1], r[2]) for r in rows
    }

    if songs_list:
        song_ids = [s.id for s in songs_list]
        cached_songs = db.session.execute(
            select(CachedAnalyticsMetadata).where(
                CachedAnalyticsMetadata.subject_type == "song",
                CachedAnalyticsMetadata.metric == "chord_analytics.song",
                CachedAnalyticsMetadata.subject_id.in_(song_ids),
            )
        ).scalars().all()
    else:
        cached_songs = []

    cached_by_song_id = {m.subject_id: m for m in cached_songs}

    song_rows: list[dict[str, Any]] = []
    for song in songs_list:
        artist, album = metadata.get(song.id, (None, None))
        cached = cached_by_song_id.get(song.id)
        payload_data = _safe_json_loads(cached.payload) if cached else {}

        song_rows.append(
            {
                "song": song,
                "artist": artist,
                "album": album,
                "unique_chords": len(payload_data.get("unique_chords", [])),
                "progressions": len(payload_data.get("progressions", [])),
                "computed_at": cached.computed_at_utc if cached else None,
                "has_analytics": cached is not None,
            }
        )

    return render_template("analytics/songs.html", song_rows=song_rows)


@analytics_bp.get("/albums")
def albums() -> str:
    rows = db.session.execute(
        select(Album, Artist)
        .join(Artist, Album.artist_id == Artist.id)
        .order_by(Artist.name, Album.release_year, Album.title)
    ).all()

    albums_list: list[Album] = [r[0] for r in rows]
    artists_by_album_id: dict[int, Artist] = {r[0].id: r[1] for r in rows}

    if albums_list:
        album_ids = [a.id for a in albums_list]
        cached_albums = db.session.execute(
            select(CachedAnalyticsMetadata).where(
                CachedAnalyticsMetadata.subject_type == "album",
                CachedAnalyticsMetadata.metric == "chord_analytics.album",
                CachedAnalyticsMetadata.subject_id.in_(album_ids),
            )
        ).scalars().all()
    else:
        cached_albums = []

    cached_by_album_id = {m.subject_id: m for m in cached_albums}

    song_counts = dict(
        db.session.execute(
            select(Song.album_id, func.count(Song.id))
            .where(Song.album_id.is_not(None))
            .group_by(Song.album_id)
        ).all()
    )

    album_rows: list[dict[str, Any]] = []
    for album in albums_list:
        cached = cached_by_album_id.get(album.id)
        payload_data = _safe_json_loads(cached.payload) if cached else {}

        album_rows.append(
            {
                "album": album,
                "artist": artists_by_album_id.get(album.id),
                "songs_total": int(song_counts.get(album.id, 0)),
                "songs_analyzed": int(payload_data.get("songs_analyzed", 0)),
                "unique_chords": int(payload_data.get("unique_chords", 0)),
                "progressions_found": int(payload_data.get("progressions_found", 0)),
                "computed_at": cached.computed_at_utc if cached else None,
                "has_analytics": cached is not None,
            }
        )

    return render_template("analytics/albums.html", album_rows=album_rows)


@analytics_bp.get("/albums/<int:album_id>")
def album_detail(album_id: int) -> str:
    album = db.session.execute(
        select(Album).where(Album.id == album_id)
    ).scalar_one_or_none()
    if album is None:
        abort(404)

    artist = db.session.execute(
        select(Artist).where(Artist.id == album.artist_id)
    ).scalar_one_or_none()

    songs = db.session.execute(
        select(Song)
        .where(Song.album_id == album.id)
        .order_by(Song.track_number, Song.title)
    ).scalars().all()

    album_meta = _get_cached_metadata(
        subject_type="album",
        subject_id=album.id,
        metric="chord_analytics.album",
    )
    album_payload = _safe_json_loads(album_meta.payload) if album_meta else {}

    album_analytics = get_album_analytics(album.id)
    top_chords: list[FrequencyBarItem] = []
    top_progressions: list[FrequencyBarItem] = []

    if album_analytics is not None:
        top_chords = _frequency_bars(
            album_analytics.most_common_chords,
            total=sum(album_analytics.chord_frequency.values()),
        )
        top_progressions = _frequency_bars(
            album_analytics.most_common_progressions,
            total=sum(album_analytics.progression_frequency.values()),
        )

    song_rows: list[dict[str, Any]] = []
    if songs:
        song_ids = [s.id for s in songs]
        cached_songs = db.session.execute(
            select(CachedAnalyticsMetadata).where(
                CachedAnalyticsMetadata.subject_type == "song",
                CachedAnalyticsMetadata.metric == "chord_analytics.song",
                CachedAnalyticsMetadata.subject_id.in_(song_ids),
            )
        ).scalars().all()

        cached_by_song_id = {m.subject_id: m for m in cached_songs}
    else:
        cached_by_song_id = {}

    for song in songs:
        cached = cached_by_song_id.get(song.id)
        payload_data = _safe_json_loads(cached.payload) if cached else {}
        song_rows.append(
            {
                "song": song,
                "has_analytics": cached is not None,
                "progressions": len(payload_data.get("progressions", [])),
                "unique_chords": len(payload_data.get("unique_chords", [])),
                "computed_at": cached.computed_at_utc if cached else None,
            }
        )

    summary = {
        "songs_analyzed": int(album_payload.get("songs_analyzed", 0)),
        "progressions_found": int(album_payload.get("progressions_found", 0)),
        "unique_chords": int(album_payload.get("unique_chords", 0)),
        "computed_at": album_meta.computed_at_utc if album_meta else None,
    }

    return render_template(
        "analytics/album_detail.html",
        album=album,
        artist=artist,
        summary=summary,
        top_chords=top_chords,
        top_progressions=top_progressions,
        song_rows=song_rows,
    )


@analytics_bp.get("/songs/<int:song_id>")
def song_detail(song_id: int) -> str:
    song = db.session.execute(
        select(Song).where(Song.id == song_id)
    ).scalar_one_or_none()
    if song is None:
        abort(404)

    artist = db.session.execute(
        select(Artist).where(Artist.id == song.artist_id)
    ).scalar_one_or_none()

    album = None
    if song.album_id is not None:
        album = db.session.execute(
            select(Album).where(Album.id == song.album_id)
        ).scalar_one_or_none()

    song_meta = _get_cached_metadata(
        subject_type="song",
        subject_id=song.id,
        metric="chord_analytics.song",
    )

    analysis = get_song_analysis(song.id)

    chord_items: list[FrequencyBarItem] = []
    progression_items: list[FrequencyBarItem] = []

    progressions_by_line: list[dict[str, Any]] = []

    if analysis is not None:
        chord_pairs = sorted(
            analysis.chord_frequency.items(),
            key=lambda x: (-x[1], x[0]),
        )
        chord_items = _frequency_bars(
            chord_pairs[:50],
            total=sum(analysis.chord_frequency.values()),
        )

        progression_strings = [str(p) for p in analysis.progressions]
        progression_counts = Counter(progression_strings)
        progression_items = _frequency_bars(
            progression_counts.most_common(50),
            total=sum(progression_counts.values()),
        )

        progressions_by_line = [
            {
                "line_number": idx + 1,
                "progression": str(p),
                "chords": list(p.chords),
            }
            for idx, p in enumerate(analysis.progressions)
        ]

    computed_at: datetime | None = song_meta.computed_at_utc if song_meta else None

    return render_template(
        "analytics/song_detail.html",
        song=song,
        artist=artist,
        album=album,
        computed_at=computed_at,
        analysis=analysis,
        chord_items=chord_items,
        progression_items=progression_items,
        progressions_by_line=progressions_by_line,
    )
