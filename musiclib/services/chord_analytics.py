from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import select

from ..chord_analysis import (
    AggregateChordAnalytics,
    ChordAnalysisResult,
    aggregate_analytics,
    aggregate_by_album,
    analyze_song,
    analytics_to_json,
)
from ..extensions import db
from ..models import Album, CachedAnalyticsMetadata, ChordLine, Song


@dataclass(frozen=True, slots=True)
class ChordAnalyticsComputeResult:
    """Result of computing chord analytics."""
    songs_analyzed: int
    progressions_found: int
    unique_chords: int


def compute_and_cache_song_analytics(
    song_id: int,
    commit: bool = True,
) -> ChordAnalysisResult | None:
    """Compute and cache analytics for a single song.
    
    Args:
        song_id: Database song ID
        commit: Whether to commit the transaction
    
    Returns:
        ChordAnalysisResult if successful, None otherwise
    """
    song = db.session.execute(select(Song).where(Song.id == song_id)).scalar_one_or_none()
    
    if song is None:
        return None
    
    # Get chord lines for this song
    chord_lines = db.session.execute(
        select(ChordLine)
        .where(ChordLine.song_id == song_id)
        .order_by(ChordLine.line_number)
    ).scalars().all()
    
    if not chord_lines:
        return None
    
    lines = [cl.content for cl in chord_lines]
    
    result = analyze_song(
        song_id=song.id,
        song_title=song.title,
        artist_id=song.artist_id,
        album_id=song.album_id,
        lines=lines,
    )
    
    # Store result in cache
    _cache_song_analysis(song_id, result)
    
    if commit:
        db.session.commit()
    
    return result


def compute_and_cache_overall_analytics(
    force: bool = False,
    commit: bool = True,
) -> ChordAnalyticsComputeResult:
    """Compute and cache overall analytics across all songs.
    
    Args:
        force: Recompute even if already cached
        commit: Whether to commit the transaction
    
    Returns:
        ChordAnalyticsComputeResult with summary stats
    """
    # Check if already cached
    cached = db.session.execute(
        select(CachedAnalyticsMetadata).where(
            CachedAnalyticsMetadata.subject_type == "global",
            CachedAnalyticsMetadata.subject_id == 0,
            CachedAnalyticsMetadata.metric == "chord_analytics.overall",
        )
    ).scalar_one_or_none()
    
    if cached and not force:
        # Return summary from existing cache
        data = json.loads(cached.payload)
        return ChordAnalyticsComputeResult(
            songs_analyzed=data.get("songs_analyzed", 0),
            progressions_found=data.get("progressions_found", 0),
            unique_chords=data.get("unique_chords", 0),
        )
    
    # Compute analytics for all songs
    all_songs = db.session.execute(select(Song)).scalars().all()
    
    song_results: list[ChordAnalysisResult] = []
    unique_chords_set: set[str] = set()
    total_progressions = 0
    
    for song in all_songs:
        result = compute_and_cache_song_analytics(song.id, commit=False)
        if result:
            song_results.append(result)
            unique_chords_set.update(result.unique_chords)
            total_progressions += len(result.progressions)
    
    if song_results:
        analytics = aggregate_analytics(song_results)
        
        payload_data = {
            "songs_analyzed": len(song_results),
            "progressions_found": total_progressions,
            "unique_chords": len(unique_chords_set),
            "analytics": json.loads(analytics_to_json(analytics)),
        }
        
        payload = json.dumps(payload_data, ensure_ascii=False)
        
        if cached:
            cached.payload = payload
        else:
            cached = CachedAnalyticsMetadata(
                subject_type="global",
                subject_id=0,
                metric="chord_analytics.overall",
                payload=payload,
            )
            db.session.add(cached)
    
    if commit:
        db.session.commit()
    
    return ChordAnalyticsComputeResult(
        songs_analyzed=len(song_results),
        progressions_found=total_progressions,
        unique_chords=len(unique_chords_set),
    )


def compute_and_cache_album_analytics(
    album_id: int | None = None,
    force: bool = False,
    commit: bool = True,
) -> dict[int, ChordAnalyticsComputeResult]:
    """Compute and cache analytics for albums.
    
    Args:
        album_id: Specific album to compute, or None for all
        force: Recompute even if already cached
        commit: Whether to commit the transaction
    
    Returns:
        Dict mapping album_id to ChordAnalyticsComputeResult
    """
    if album_id is not None:
        albums = [
            db.session.execute(select(Album).where(Album.id == album_id)).scalar_one_or_none()
        ]
    else:
        albums = db.session.execute(select(Album)).scalars().all()
    
    albums = [a for a in albums if a is not None]
    results_by_album: dict[int, ChordAnalyticsComputeResult] = {}
    
    for album in albums:
        # Check cache
        cached = db.session.execute(
            select(CachedAnalyticsMetadata).where(
                CachedAnalyticsMetadata.subject_type == "album",
                CachedAnalyticsMetadata.subject_id == album.id,
                CachedAnalyticsMetadata.metric == "chord_analytics.album",
            )
        ).scalar_one_or_none()
        
        if cached and not force:
            data = json.loads(cached.payload)
            results_by_album[album.id] = ChordAnalyticsComputeResult(
                songs_analyzed=data.get("songs_analyzed", 0),
                progressions_found=data.get("progressions_found", 0),
                unique_chords=data.get("unique_chords", 0),
            )
            continue
        
        # Compute for this album
        songs = db.session.execute(
            select(Song).where(Song.album_id == album.id)
        ).scalars().all()
        
        song_results: list[ChordAnalysisResult] = []
        unique_chords_set: set[str] = set()
        total_progressions = 0
        
        for song in songs:
            result = compute_and_cache_song_analytics(song.id, commit=False)
            if result:
                song_results.append(result)
                unique_chords_set.update(result.unique_chords)
                total_progressions += len(result.progressions)
        
        if song_results:
            analytics = aggregate_analytics(song_results)
            
            payload_data = {
                "songs_analyzed": len(song_results),
                "progressions_found": total_progressions,
                "unique_chords": len(unique_chords_set),
                "analytics": json.loads(analytics_to_json(analytics)),
            }
            
            payload = json.dumps(payload_data, ensure_ascii=False)
            
            if cached:
                cached.payload = payload
            else:
                cached = CachedAnalyticsMetadata(
                    subject_type="album",
                    subject_id=album.id,
                    metric="chord_analytics.album",
                    payload=payload,
                )
                db.session.add(cached)
        
        results_by_album[album.id] = ChordAnalyticsComputeResult(
            songs_analyzed=len(song_results),
            progressions_found=total_progressions,
            unique_chords=len(unique_chords_set),
        )
    
    if commit:
        db.session.commit()
    
    return results_by_album


def compute_and_cache_artist_analytics(
    force: bool = False,
    commit: bool = True,
) -> ChordAnalyticsComputeResult:
    """Compute and cache analytics for all artists combined.
    
    Args:
        force: Recompute even if already cached
        commit: Whether to commit the transaction
    
    Returns:
        ChordAnalyticsComputeResult with summary stats
    """
    # For now, this is an alias for overall analytics
    # Can be extended later for per-artist breakdowns
    return compute_and_cache_overall_analytics(force=force, commit=commit)


def _cache_song_analysis(
    song_id: int,
    result: ChordAnalysisResult,
) -> None:
    """Cache a song's analysis result."""
    payload_data = {
        "song_id": result.song_id,
        "song_title": result.song_title,
        "artist_id": result.artist_id,
        "album_id": result.album_id,
        "progressions": [p.to_dict() for p in result.progressions],
        "unique_chords": list(result.unique_chords),
        "chord_frequency": result.chord_frequency,
    }
    
    payload = json.dumps(payload_data, ensure_ascii=False)
    
    cached = db.session.execute(
        select(CachedAnalyticsMetadata).where(
            CachedAnalyticsMetadata.subject_type == "song",
            CachedAnalyticsMetadata.subject_id == song_id,
            CachedAnalyticsMetadata.metric == "chord_analytics.song",
        )
    ).scalar_one_or_none()
    
    if cached:
        cached.payload = payload
    else:
        cached = CachedAnalyticsMetadata(
            subject_type="song",
            subject_id=song_id,
            metric="chord_analytics.song",
            payload=payload,
        )
        db.session.add(cached)


def get_overall_analytics() -> AggregateChordAnalytics | None:
    """Retrieve cached overall analytics."""
    cached = db.session.execute(
        select(CachedAnalyticsMetadata).where(
            CachedAnalyticsMetadata.subject_type == "global",
            CachedAnalyticsMetadata.subject_id == 0,
            CachedAnalyticsMetadata.metric == "chord_analytics.overall",
        )
    ).scalar_one_or_none()
    
    if cached is None:
        return None
    
    data = json.loads(cached.payload)
    analytics_data = data.get("analytics", {})
    
    # Reconstruct AggregateChordAnalytics from JSON
    return _reconstruct_analytics(analytics_data)


def get_album_analytics(album_id: int) -> AggregateChordAnalytics | None:
    """Retrieve cached analytics for a specific album."""
    cached = db.session.execute(
        select(CachedAnalyticsMetadata).where(
            CachedAnalyticsMetadata.subject_type == "album",
            CachedAnalyticsMetadata.subject_id == album_id,
            CachedAnalyticsMetadata.metric == "chord_analytics.album",
        )
    ).scalar_one_or_none()
    
    if cached is None:
        return None
    
    data = json.loads(cached.payload)
    analytics_data = data.get("analytics", {})
    
    return _reconstruct_analytics(analytics_data)


def get_song_analysis(song_id: int) -> ChordAnalysisResult | None:
    """Retrieve cached analysis for a specific song."""
    cached = db.session.execute(
        select(CachedAnalyticsMetadata).where(
            CachedAnalyticsMetadata.subject_type == "song",
            CachedAnalyticsMetadata.subject_id == song_id,
            CachedAnalyticsMetadata.metric == "chord_analytics.song",
        )
    ).scalar_one_or_none()
    
    if cached is None:
        return None
    
    data = json.loads(cached.payload)
    
    from ..chord_analysis import ChordProgression
    
    progressions = [
        ChordProgression.from_dict(p) for p in data.get("progressions", [])
    ]
    
    return ChordAnalysisResult(
        song_id=data["song_id"],
        song_title=data["song_title"],
        artist_id=data["artist_id"],
        album_id=data.get("album_id"),
        progressions=tuple(progressions),
        unique_chords=tuple(data.get("unique_chords", [])),
        chord_frequency=data.get("chord_frequency", {}),
    )


def _reconstruct_analytics(analytics_data: dict) -> AggregateChordAnalytics:
    """Reconstruct AggregateChordAnalytics from serialized dict."""
    most_common_progressions = [
        (item["progression"], item["count"])
        for item in analytics_data.get("most_common_progressions", [])
    ]
    most_common_chords = [
        (item["chord"], item["count"])
        for item in analytics_data.get("most_common_chords", [])
    ]
    chord_frequency = analytics_data.get("chord_frequency", {})
    progression_frequency = analytics_data.get("progression_frequency", {})
    
    return AggregateChordAnalytics(
        most_common_progressions=most_common_progressions,
        most_common_chords=most_common_chords,
        chord_frequency=chord_frequency,
        progression_frequency=progression_frequency,
    )
