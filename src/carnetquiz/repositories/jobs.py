from __future__ import annotations

import json

from ..database import connect


def create_job(job: dict[str, object]) -> None:
    with connect() as db:
        db.execute("INSERT INTO jobs(id,video_id,start_seconds,end_seconds,status,created_at,directory,schema_version) VALUES(:id,:video_id,:start_seconds,:end_seconds,:status,:created_at,:directory,:schema_version)", job)


def list_overlapping_jobs(video_id: str, start: float, until: float) -> list[dict[str, object]]:
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM jobs WHERE video_id=? AND start_seconds < ? AND end_seconds > ? "
            "ORDER BY start_seconds, end_seconds, created_at",
            (video_id, until, start),
        ).fetchall()
    return [dict(row) for row in rows]


def get_job(job_id: str) -> dict[str, object]:
    with connect() as db: row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row: raise KeyError(f"Trabajo no encontrado: {job_id}")
    result = dict(row); result["validation_errors"] = json.loads(result["validation_errors"]); return result


def list_jobs() -> list[dict[str, object]]:
    with connect() as db: rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def update_job(job_id: str, **values: object) -> None:
    if not values: return
    fields = ", ".join(f"{key}=?" for key in values)
    with connect() as db: db.execute(f"UPDATE jobs SET {fields} WHERE id=?", [*values.values(), job_id])
