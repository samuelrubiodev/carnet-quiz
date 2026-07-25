from __future__ import annotations

import json
from pathlib import Path

from ..database import connect, now
from ..schemas import SegmentInput


def create_video(video_id: str, url: str, title: str, channel: str | None = None, duration_seconds: float | None = None, language: str | None = None) -> dict[str, object]:
    with connect() as db:
        db.execute("INSERT INTO videos(id,youtube_id,url,title,channel,duration_seconds,language,added_at,status) VALUES(?,?,?,?,?,?,?,?,?)", (video_id, video_id, url, title, channel, duration_seconds, language, now(), "added"))
    return get_video(video_id)


def get_video(video_id: str) -> dict[str, object]:
    with connect() as db:
        row = db.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()
    if not row:
        raise KeyError(f"Vídeo no encontrado: {video_id}")
    return dict(row)


def list_videos() -> list[dict[str, object]]:
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM videos ORDER BY added_at DESC")]


def replace_segments(video_id: str, segments: list[SegmentInput], transcript_path: Path, subtitle_type: str) -> int:
    with connect() as db:
        if not db.execute("SELECT 1 FROM videos WHERE id=?", (video_id,)).fetchone():
            raise KeyError(f"Vídeo no encontrado: {video_id}")
        db.execute("DELETE FROM transcript_segments WHERE video_id=?", (video_id,))
        db.executemany("INSERT INTO transcript_segments(video_id,start_seconds,end_seconds,text,original_text,language,subtitle_type,segment_index) VALUES(?,?,?,?,?,?,?,?)", [(video_id, s.start_seconds, s.end_seconds, s.text, s.original_text, s.language, subtitle_type, index) for index, s in enumerate(segments)])
        db.execute("UPDATE videos SET transcript_path=?, status='transcript_ready' WHERE id=?", (str(transcript_path), video_id))
    return len(segments)


def list_segments(video_id: str, until: float | None = None, search: str | None = None) -> list[dict[str, object]]:
    sql, values = "SELECT * FROM transcript_segments WHERE video_id=?", [video_id]
    if until is not None:
        sql += " AND start_seconds < ?"; values.append(until)
    if search:
        sql += " AND text LIKE ?"; values.append(f"%{search}%")
    sql += " ORDER BY start_seconds, segment_index"
    with connect() as db:
        return [dict(row) for row in db.execute(sql, values)]


def save_transcript_json(path: Path, video_id: str, segments: list[SegmentInput]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"video_id": video_id, "segments": [segment.model_dump() for segment in segments]}, ensure_ascii=False, indent=2), encoding="utf-8")
