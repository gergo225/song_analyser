from __future__ import annotations

from datetime import datetime

from sqlalchemy import UniqueConstraint, func

from .extensions import db


class Artist(db.Model):
    __tablename__ = "artists"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    albums = db.relationship(
        "Album", back_populates="artist", cascade="all, delete-orphan"
    )
    songs = db.relationship(
        "Song", back_populates="artist", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Artist id={self.id} name={self.name!r}>"


class Album(db.Model):
    __tablename__ = "albums"
    __table_args__ = (
        UniqueConstraint("artist_id", "title", name="uq_albums_artist_title"),
    )

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey("artists.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False, index=True)
    release_year = db.Column(db.Integer, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    artist = db.relationship("Artist", back_populates="albums")
    songs = db.relationship("Song", back_populates="album")

    def __repr__(self) -> str:
        return f"<Album id={self.id} title={self.title!r}>"


class Song(db.Model):
    __tablename__ = "songs"
    __table_args__ = (
        UniqueConstraint("artist_id", "title", name="uq_songs_artist_title"),
    )

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey("artists.id"), nullable=False)
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"), nullable=True)

    title = db.Column(db.String(255), nullable=False, index=True)
    track_number = db.Column(db.Integer, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    artist = db.relationship("Artist", back_populates="songs")
    album = db.relationship("Album", back_populates="songs")

    chord_lines = db.relationship(
        "ChordLine",
        back_populates="song",
        cascade="all, delete-orphan",
        order_by="ChordLine.line_number",
    )

    def __repr__(self) -> str:
        return f"<Song id={self.id} title={self.title!r}>"


class ChordLine(db.Model):
    __tablename__ = "chord_lines"
    __table_args__ = (
        UniqueConstraint("song_id", "line_number", name="uq_chord_lines_song_line"),
    )

    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey("songs.id"), nullable=False, index=True)
    line_number = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    song = db.relationship("Song", back_populates="chord_lines")

    def __repr__(self) -> str:
        return f"<ChordLine id={self.id} song_id={self.song_id} line={self.line_number}>"


class CachedAnalyticsMetadata(db.Model):
    __tablename__ = "cached_analytics_metadata"
    __table_args__ = (
        UniqueConstraint(
            "subject_type",
            "subject_id",
            "metric",
            name="uq_cached_analytics_subject_metric",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    subject_type = db.Column(db.String(50), nullable=False, index=True)
    subject_id = db.Column(db.Integer, nullable=False, index=True)
    metric = db.Column(db.String(100), nullable=False, index=True)

    payload = db.Column(db.Text, nullable=False)
    computed_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<CachedAnalyticsMetadata id={self.id} subject={self.subject_type}:{self.subject_id} "
            f"metric={self.metric!r}>"
        )

    @property
    def computed_at_utc(self) -> datetime | None:
        return self.computed_at
