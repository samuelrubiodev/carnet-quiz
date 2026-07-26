from __future__ import annotations

import json
import math
import re
import uuid
from pathlib import Path

from ..config import ensure_data_dirs
from ..database import SCHEMA_VERSION, now, transaction
from ..repositories import jobs as repo
from ..repositories import videos as video_repo
from ..schemas import ConceptInput, QuestionInput, ReviewInput
from .validation import fingerprint, validate_job_directory

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{3,100}$")


def parse_duration(value: str | int | float) -> float:
    if isinstance(value, (int, float)): return float(value)
    value = value.strip().lower()
    if re.fullmatch(r"\d+(?:\.\d+)?", value): return float(value)
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([hms])", value)
    if match: return float(match[1]) * {"h": 3600, "m": 60, "s": 1}[match[2]]
    parts = value.split(":")
    if len(parts) in (2, 3) and all(part.isdigit() for part in parts):
        nums = [int(part) for part in parts]; return float(nums[0] * 60 + nums[1] if len(nums) == 2 else nums[0] * 3600 + nums[1] * 60 + nums[2])
    raise ValueError("Duración inválida. Usá 30m, 90s, 01:30:00 o segundos")


def _write_json(path: Path, payload: object) -> None: path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_job_boundary(value: str | int | float, label: str) -> float:
    if isinstance(value, str) and value.strip().startswith("-"):
        raise ValueError(f"{label} no puede ser negativo")
    seconds = parse_duration(value)
    if seconds < 0:
        raise ValueError(f"{label} no puede ser negativo")
    if not math.isfinite(seconds):
        raise ValueError(f"{label} no es válido")
    return seconds


def create_job(
    video_id: str,
    until: str | int | float,
    start: str | int | float = "0s",
) -> dict[str, object]:
    start_seconds = _parse_job_boundary(start, "Inicio")
    end_seconds = _parse_job_boundary(until, "Fin")

    settings = ensure_data_dirs()
    video = video_repo.get_video(video_id)
    if end_seconds <= start_seconds:
        raise ValueError("Fin debe ser mayor que inicio")
    duration = video["duration_seconds"]
    if duration is not None:
        duration_seconds = float(duration)
        if start_seconds >= duration_seconds:
            raise ValueError("Inicio debe ser anterior a duración de vídeo")
        if end_seconds > duration_seconds:
            raise ValueError("Intervalo posterior a duración de vídeo")

    segments = video_repo.list_segments(
        video_id,
        start=start_seconds,
        until=end_seconds,
    )
    if not segments:
        raise ValueError("No hay transcripción en intervalo solicitado")

    overlaps = repo.list_overlapping_jobs(video_id, start_seconds, end_seconds)
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    directory = settings.jobs_dir / job_id
    directory.mkdir(mode=0o700)
    request = {
        "video_id": video_id,
        "title": video["title"],
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "language": video["language"] or settings.preferred_language,
        "recommended_questions_per_concept": settings.questions_per_concept,
        "allowed_question_types": [
            "definition", "direct", "practical_case", "comparison", "negative",
            "priority", "exception", "sign_interpretation", "true_false_group",
        ],
        "difficulty": "mixed",
        "rules": [
            "Use only transcript evidence",
            "Do not write SQLite",
            "One review and one optional repair maximum",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    _write_json(directory / "request.json", request)
    _write_json(directory / "transcript.json", {"video_id": video_id, "segments": segments})
    _write_json(directory / "concepts.json", [])
    _write_json(directory / "questions.json", [])
    _write_json(
        directory / "review.json",
        {"reviewed_question_ids": [], "rejected_question_ids": [], "notes": "", "repaired": False},
    )
    _write_json(directory / "concepts.schema.json", ConceptInput.model_json_schema())
    _write_json(directory / "questions.schema.json", QuestionInput.model_json_schema())
    _write_json(directory / "review.schema.json", ReviewInput.model_json_schema())
    payload = {
        "id": job_id,
        "video_id": video_id,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "status": "ready",
        "created_at": now(),
        "directory": str(directory),
        "schema_version": SCHEMA_VERSION,
    }
    repo.create_job(payload)
    result = repo.get_job(job_id)
    if overlaps:
        result["warnings"] = [
            "Advertencia: intervalo solapado con "
            + ", ".join(str(item["id"]) for item in overlaps)
        ]
    return result


def get_job(job_id: str) -> dict[str, object]: return repo.get_job(job_id)
def list_jobs() -> list[dict[str, object]]: return repo.list_jobs()


def validate_job(job_id: str) -> dict[str, object]:
    job = repo.get_job(job_id)
    if job["status"] in {"rejected", "committed"}: raise ValueError(f"Trabajo en estado {job['status']}")
    report, concepts, questions = validate_job_directory(job)
    directory = Path(str(job["directory"])); _write_json(directory / "validation-report.json", report.model_dump())
    # Keep an invalid job repairable once; explicit `job reject` is terminal.
    status = "validated" if not report.errors else "partially_valid"
    repo.update_job(job_id, status=status, validated_at=now(), concept_count=len(concepts), question_count=len(questions), validation_errors=json.dumps([item.model_dump() for item in report.errors], ensure_ascii=False))
    return report.model_dump()


def commit_job(job_id: str) -> dict[str, int]:
    job = repo.get_job(job_id)
    if job["status"] not in {"validated", "partially_valid"}: raise ValueError("Validá trabajo antes de importarlo")
    report, concepts, questions = validate_job_directory(job)
    if not questions: raise ValueError("No hay preguntas válidas para importar")
    with transaction() as db:
        for concept in concepts:
            db.execute("INSERT INTO concepts(id,video_id,job_id,title,topic,subtopic,summary,importance,difficulty,source_segment_ids,source_start,source_end,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (concept.id, job["video_id"], job_id, concept.title, concept.topic, concept.subtopic, concept.summary, concept.importance, concept.difficulty, json.dumps(concept.source_segment_ids), concept.source_start, concept.source_end, "valid", now()))
        for question in questions:
            db.execute("INSERT INTO questions(id,concept_id,video_id,job_id,question,question_type,difficulty,explanation,options_json,correct_option,source_segment_ids,source_start,source_end,status,fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (question.id, question.concept_id, job["video_id"], job_id, question.question, question.type, question.difficulty, question.explanation, json.dumps([item.model_dump() for item in question.options], ensure_ascii=False), question.correct_option, json.dumps(question.source_segment_ids), question.source_start, question.source_end, "valid", fingerprint(question.question)))
        db.execute("UPDATE jobs SET status='committed', imported_at=?, concept_count=?, question_count=? WHERE id=?", (now(), len(concepts), len(questions), job_id))
        db.execute("UPDATE videos SET last_processed_seconds=MAX(last_processed_seconds, ?) WHERE id=?", (job["end_seconds"], job["video_id"]))
    return {"concepts": len(concepts), "questions": len(questions)}


def reject_job(job_id: str) -> None:
    job = repo.get_job(job_id)
    if job["status"] == "committed": raise ValueError("No se puede rechazar trabajo importado")
    repo.update_job(job_id, status="rejected")


def write_submission(job_id: str, name: str, payload: object) -> None:
    if name not in {"concepts.json", "questions.json", "review.json"}: raise ValueError("Archivo no admitido")
    job = repo.get_job(job_id); target = Path(str(job["directory"])) / name
    _write_json(target, payload)
