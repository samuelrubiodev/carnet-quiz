from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class VideoMetadata:
    youtube_id: str
    url: str
    title: str
    channel: str | None
    duration_seconds: float | None
    language: str | None
    subtitles: dict[str, list[dict[str, object]]]
    automatic_captions: dict[str, list[dict[str, object]]]


def yt_dlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def fetch_metadata(url: str, timeout: int = 30) -> VideoMetadata:
    if not yt_dlp_available():
        raise RuntimeError("yt-dlp no está instalado o no está en PATH")
    result = subprocess.run(["yt-dlp", "--skip-download", "--dump-single-json", url], text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "error desconocido"
        raise RuntimeError(f"yt-dlp no pudo consultar vídeo: {detail}")
    payload = json.loads(result.stdout)
    return VideoMetadata(payload["id"], url, payload.get("title") or payload["id"], payload.get("channel") or payload.get("uploader"), payload.get("duration"), payload.get("language"), payload.get("subtitles") or {}, payload.get("automatic_captions") or {})
