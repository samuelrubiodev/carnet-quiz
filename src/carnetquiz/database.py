from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .config import Settings, ensure_data_dirs, get_settings

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS videos (
 id TEXT PRIMARY KEY, youtube_id TEXT UNIQUE, url TEXT NOT NULL, title TEXT NOT NULL,
 channel TEXT, duration_seconds REAL, language TEXT, added_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'added', transcript_path TEXT, last_processed_seconds REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS transcript_segments (
 id INTEGER PRIMARY KEY AUTOINCREMENT, video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
 start_seconds REAL NOT NULL, end_seconds REAL NOT NULL, text TEXT NOT NULL, original_text TEXT,
 language TEXT, subtitle_type TEXT NOT NULL, segment_index INTEGER NOT NULL,
 UNIQUE(video_id, segment_index)
);
CREATE INDEX IF NOT EXISTS idx_segments_video_time ON transcript_segments(video_id, start_seconds);
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE RESTRICT,
 start_seconds REAL NOT NULL, end_seconds REAL NOT NULL, status TEXT NOT NULL,
 created_at TEXT NOT NULL, validated_at TEXT, imported_at TEXT, directory TEXT NOT NULL,
 concept_count INTEGER NOT NULL DEFAULT 0, question_count INTEGER NOT NULL DEFAULT 0,
 validation_errors TEXT NOT NULL DEFAULT '[]', schema_version INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_video ON jobs(video_id, created_at DESC);
CREATE TABLE IF NOT EXISTS concepts (
 id TEXT PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id), job_id TEXT NOT NULL REFERENCES jobs(id),
 title TEXT NOT NULL, topic TEXT NOT NULL, subtopic TEXT, summary TEXT NOT NULL, importance TEXT NOT NULL,
 difficulty INTEGER NOT NULL, source_segment_ids TEXT NOT NULL, source_start REAL NOT NULL,
 source_end REAL NOT NULL, status TEXT NOT NULL DEFAULT 'valid', created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_concepts_video_topic ON concepts(video_id, topic);
CREATE TABLE IF NOT EXISTS questions (
 id TEXT PRIMARY KEY, concept_id TEXT NOT NULL REFERENCES concepts(id), video_id TEXT NOT NULL REFERENCES videos(id),
 job_id TEXT NOT NULL REFERENCES jobs(id), question TEXT NOT NULL, question_type TEXT NOT NULL,
 difficulty INTEGER NOT NULL, explanation TEXT NOT NULL, options_json TEXT NOT NULL, correct_option TEXT NOT NULL,
 source_segment_ids TEXT NOT NULL, source_start REAL NOT NULL, source_end REAL NOT NULL,
 status TEXT NOT NULL DEFAULT 'valid', rejection_reason TEXT, fingerprint TEXT NOT NULL UNIQUE,
 shown_count INTEGER NOT NULL DEFAULT 0, correct_count INTEGER NOT NULL DEFAULT 0, wrong_count INTEGER NOT NULL DEFAULT 0,
 last_shown_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_questions_video_status ON questions(video_id, status);
CREATE TABLE IF NOT EXISTS attempts (
 id TEXT PRIMARY KEY, created_at TEXT NOT NULL, video_ids TEXT NOT NULL, selection_mode TEXT NOT NULL,
 question_count INTEGER NOT NULL, correct_count INTEGER NOT NULL DEFAULT 0, wrong_count INTEGER NOT NULL DEFAULT 0,
 duration_seconds REAL, seed INTEGER
);
CREATE TABLE IF NOT EXISTS answers (
 id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id TEXT NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
 question_id TEXT NOT NULL REFERENCES questions(id), chosen_option TEXT NOT NULL, correct_option TEXT NOT NULL,
 is_correct INTEGER NOT NULL, elapsed_seconds REAL, position INTEGER NOT NULL,
 UNIQUE(attempt_id, position)
);
CREATE INDEX IF NOT EXISTS idx_answers_attempt ON answers(attempt_id);
"""


def now() -> str:
    return datetime.now(UTC).isoformat()


def connect(settings: Settings | None = None) -> sqlite3.Connection:
    settings = ensure_data_dirs(settings or get_settings())
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize(settings: Settings | None = None) -> Path:
    settings = ensure_data_dirs(settings or get_settings())
    with connect(settings) as connection:
        connection.executescript(_SCHEMA)
        connection.execute(
            "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(SCHEMA_VERSION),)
        )
    return settings.database_path


def backup(settings: Settings | None = None) -> Path:
    settings = ensure_data_dirs(settings or get_settings())
    if not settings.database_path.exists():
        raise FileNotFoundError("Base de datos no inicializada")
    destination = settings.database_path.with_name(f"{settings.database_path.stem}-{datetime.now():%Y%m%d%H%M%S}.bak")
    shutil.copy2(settings.database_path, destination)
    return destination


def integrity_check(settings: Settings | None = None) -> list[str]:
    initialize(settings)
    with connect(settings) as connection:
        return [row[0] for row in connection.execute("PRAGMA integrity_check")]


@contextmanager
def transaction(settings: Settings | None = None) -> Iterator[sqlite3.Connection]:
    initialize(settings)
    connection = connect(settings)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
