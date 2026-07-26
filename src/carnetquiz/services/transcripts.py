from __future__ import annotations

from pathlib import Path

from ..config import ensure_data_dirs, get_settings
from ..repositories import videos as repo
from ..schemas import SegmentInput, SubtitleType
from ..youtube.metadata import fetch_metadata
from ..youtube.normalizer import normalize_segments
from ..youtube.parsers import parse_transcript_file
from ..youtube.subtitles import download_subtitles


def import_segments(video_id: str, segments: list[SegmentInput], subtitle_type: SubtitleType = SubtitleType.IMPORTED) -> int:
    settings = ensure_data_dirs(); normalized = normalize_segments(segments, settings.min_segment_seconds, settings.max_segment_seconds)
    target = settings.transcripts_dir / f"{video_id}.json"
    repo.save_transcript_json(target, video_id, normalized)
    return repo.replace_segments(video_id, normalized, target, subtitle_type.value)


def import_file(video_id: str, source: Path, language: str = "es") -> int:
    settings = get_settings()
    if not source.is_file() or source.stat().st_size > settings.max_import_bytes: raise ValueError("Archivo inválido o demasiado grande")
    return import_segments(video_id, parse_transcript_file(source, language), SubtitleType.IMPORTED)


def fetch(video_id: str, language: str | None = None) -> int:
    video = repo.get_video(video_id); metadata = fetch_metadata(str(video["url"]))
    settings = ensure_data_dirs(); raw = settings.transcripts_dir / f"{video_id}.vtt"
    path, selected, automatic = download_subtitles(metadata, raw, settings.preferred_language, language)
    subtitle_type = SubtitleType.AUTOMATIC if automatic else SubtitleType.MANUAL
    return import_segments(video_id, parse_transcript_file(path, selected), subtitle_type)


def list_segments(
    video_id: str,
    start: float | None = None,
    until: float | None = None,
    search: str | None = None,
) -> list[dict[str, object]]:
    return repo.list_segments(video_id, start=start, until=until, search=search)
