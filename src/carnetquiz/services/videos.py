from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from ..database import initialize
from ..repositories import videos as repo
from ..youtube.metadata import fetch_metadata


def video_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    value = parse_qs(parsed.query).get("v", [""])[0] if "youtu" in parsed.netloc else parsed.path.strip("/").split("/")[-1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,30}", value):
        raise ValueError("URL de YouTube inválida o identificador no reconocido")
    return value


def add_video(url: str, metadata: object | None = None) -> dict[str, object]:
    initialize(); video_id = video_id_from_url(url)
    if metadata is None: metadata = fetch_metadata(url)
    return repo.create_video(video_id, url, getattr(metadata, "title"), getattr(metadata, "channel"), getattr(metadata, "duration_seconds"), getattr(metadata, "language"))


def add_demo_video(video_id: str, title: str, duration: float = 120.0) -> dict[str, object]:
    initialize()
    try: return repo.get_video(video_id)
    except KeyError: return repo.create_video(video_id, f"https://www.youtube.com/watch?v={video_id}", title, "CarnetQuiz Demo", duration, "es")


def get_video(video_id: str) -> dict[str, object]: return repo.get_video(video_id)
def list_videos() -> list[dict[str, object]]: return repo.list_videos()
