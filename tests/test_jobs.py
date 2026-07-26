from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from carnetquiz.repositories.jobs import list_jobs
from carnetquiz.repositories.questions import list_questions
from carnetquiz.repositories.videos import get_video, list_segments
from carnetquiz.schemas import SegmentInput
from carnetquiz.services import jobs
from carnetquiz.services.selection import select_questions
from carnetquiz.services.transcripts import import_segments
from carnetquiz.services.videos import add_demo_video


def prepared_job():
    add_demo_video("test-video-01", "Test", 100)
    import_segments("test-video-01", [SegmentInput(start_seconds=0, end_seconds=10, text="Agente tiene prioridad sobre semáforo.")])
    job = jobs.create_job("test-video-01", "10s")
    from carnetquiz.services.transcripts import list_segments
    segment_id = list_segments("test-video-01")[0]["id"]
    concept = {"id":"agent-priority-001","title":"Prioridad agente","topic":"Señales","subtopic":None,"summary":"Agente tiene prioridad sobre semáforo.","importance":"high","difficulty":2,"exam_relevant":True,"source_segment_ids":[segment_id],"source_start":0,"source_end":10}
    question = {"id":"agent-priority-001-q01","concept_id":"agent-priority-001","type":"direct","difficulty":2,"question":"¿Quién tiene prioridad sobre semáforo?","options":[{"id":"a","text":"Agente"},{"id":"b","text":"Semáforo"},{"id":"c","text":"Nadie"}],"correct_option":"a","explanation":"Transcripción indica prioridad del agente.","source_segment_ids":[segment_id],"source_start":0,"source_end":10}
    return job, concept, question


def test_validates_and_commits_transactionally():
    job, concept, question = prepared_job()
    jobs.write_submission(job["id"], "concepts.json", [concept])
    jobs.write_submission(job["id"], "questions.json", [question])
    report = jobs.validate_job(job["id"])
    assert report["valid_question_ids"] == [question["id"]]
    assert jobs.commit_job(job["id"])["questions"] == 1
    assert len(list_questions()) == 1


def test_rejects_missing_segment_and_outside_range():
    job, concept, question = prepared_job()
    question["source_segment_ids"] = [9999]
    question["source_end"] = 15
    jobs.write_submission(job["id"], "concepts.json", [concept])
    jobs.write_submission(job["id"], "questions.json", [question])
    report = jobs.validate_job(job["id"])
    codes = {issue["code"] for issue in report["issues"]}
    assert {"missing_source_segment", "outside_job_range"} <= codes


def test_rejects_duplicate_questions_and_options():
    job, concept, question = prepared_job()
    duplicate = dict(question, id="agent-priority-001-q02")
    duplicate["options"] = [
        {"id":"a","text":"Igual"}, {"id":"b","text":"Igual"}, {"id":"c","text":"Otro"}
    ]
    jobs.write_submission(job["id"], "concepts.json", [concept])
    jobs.write_submission(job["id"], "questions.json", [question, duplicate])
    report = jobs.validate_job(job["id"])
    codes = {issue["code"] for issue in report["issues"]}
    assert "similar_question" in codes
    assert "duplicate_option_text" in codes


def interval_video(video_id: str = "interval-video-01") -> list[dict[str, object]]:
    add_demo_video(video_id, "Vídeo de intervalos", 3600)
    import_segments(
        video_id,
        [
            SegmentInput(start_seconds=0, end_seconds=10, text="Contenido inicial suficientemente descriptivo."),
            SegmentInput(start_seconds=600, end_seconds=610, text="Contenido del intervalo intermedio suficientemente descriptivo."),
            SegmentInput(start_seconds=1790, end_seconds=1799, text="Contenido inmediatamente anterior al límite."),
            SegmentInput(start_seconds=1800, end_seconds=1810, text="Contenido situado exactamente en treinta minutos."),
            SegmentInput(start_seconds=3590, end_seconds=3599, text="Contenido inmediatamente anterior a una hora."),
            SegmentInput(start_seconds=3600, end_seconds=3610, text="Contenido situado exactamente en una hora."),
        ],
    )
    return list_segments(video_id)


def test_create_job_uses_half_open_interval_and_keeps_legacy_default():
    segments = interval_video()
    first = jobs.create_job("interval-video-01", "30m")
    second = jobs.create_job("interval-video-01", "60m", "30m")

    assert (first["start_seconds"], first["end_seconds"]) == (0, 1800)
    assert (second["start_seconds"], second["end_seconds"]) == (1800, 3600)
    request = json.loads((Path(str(second["directory"])) / "request.json").read_text())
    assert request["start_seconds"] == 1800
    assert request["end_seconds"] == 3600
    first_ids = {item["id"] for item in _job_segments(first)}
    second_ids = {item["id"] for item in _job_segments(second)}
    assert first_ids.isdisjoint(second_ids)
    assert next(item["id"] for item in segments if item["start_seconds"] == 1800) in second_ids
    assert next(item["id"] for item in segments if item["start_seconds"] == 3600) not in second_ids
    assert all(item["start_seconds"] < 1800 for item in _job_segments(first))
    assert all(1800 <= item["start_seconds"] < 3600 for item in _job_segments(second))


def _job_segments(job: dict[str, object]) -> list[dict[str, object]]:
    payload = json.loads((Path(str(job["directory"])) / "transcript.json").read_text())
    return payload["segments"]


@pytest.mark.parametrize(
    ("start", "until", "expected"),
    [("0", "1800", (0, 1800)), ("30m", "1h", (1800, 3600)), ("1h", "01:30:00", (3600, 5400)), (0, 1800, (0, 1800))],
)
def test_create_job_accepts_all_duration_formats(start: str | int, until: str | int, expected: tuple[int, int]):
    video_id = f"formats-{expected[0]}"
    add_demo_video(video_id, "Formatos", 7200)
    import_segments(
        video_id,
        [SegmentInput(start_seconds=expected[0], end_seconds=expected[0] + 10, text="Segmento válido para formato de duración.")],
    )
    job = jobs.create_job(video_id, until, start)
    assert (job["start_seconds"], job["end_seconds"]) == expected


@pytest.mark.parametrize(
    ("start", "until", "message"),
    [("60m", "30m", "Fin debe ser mayor que inicio"), ("30m", "30m", "Fin debe ser mayor que inicio"), ("-1m", "30m", "Inicio no puede ser negativo")],
)
def test_invalid_interval_creates_no_job(start: str, until: str, message: str):
    interval_video()
    with pytest.raises(ValueError, match=message):
        jobs.create_job("interval-video-01", until, start)
    assert list_jobs() == []
    assert not list(Path(os.environ["CARNETQUIZ_DATA_DIR"]).joinpath("jobs").glob("job-*"))


def test_rejects_interval_outside_video_duration_and_without_transcript():
    interval_video()
    with pytest.raises(ValueError, match="Inicio debe ser anterior"):
        jobs.create_job("interval-video-01", "3601", "3600")
    with pytest.raises(ValueError, match="posterior a duración"):
        jobs.create_job("interval-video-01", "3601", "30m")
    with pytest.raises(ValueError, match="No hay transcripción"):
        jobs.create_job("interval-video-01", "20m", "15m")
    with pytest.raises(KeyError, match="Vídeo no encontrado"):
        jobs.create_job("missing-video", "30m")
    assert list_jobs() == []


def _submit_single(job: dict[str, object], prefix: str, segment: dict[str, object]) -> None:
    concept_id = f"{prefix}-concept"
    question_id = f"{prefix}-question"
    concept = {
        "id": concept_id, "title": f"Concepto {prefix}", "topic": "Intervalos", "subtopic": None,
        "summary": "Resumen suficientemente descriptivo del concepto generado.", "importance": "high",
        "difficulty": 2, "exam_relevant": True, "source_segment_ids": [segment["id"]],
        "source_start": segment["start_seconds"], "source_end": segment["end_seconds"],
    }
    question = {
        "id": question_id, "concept_id": concept_id, "type": "direct", "difficulty": 2,
        "question": f"¿Qué contenido corresponde a {prefix}?",
        "options": [{"id": "a", "text": "La opción correcta"}, {"id": "b", "text": "Otra opción"}, {"id": "c", "text": "Una tercera opción"}],
        "correct_option": "a", "explanation": "La fuente respalda esta respuesta de forma suficiente.",
        "source_segment_ids": [segment["id"]], "source_start": segment["start_seconds"], "source_end": segment["end_seconds"],
    }
    jobs.write_submission(str(job["id"]), "concepts.json", [concept])
    jobs.write_submission(str(job["id"]), "questions.json", [question])
    assert not jobs.validate_job(str(job["id"]))["issues"]
    jobs.commit_job(str(job["id"]))


def test_last_processed_seconds_only_moves_forward_and_tests_are_cumulative():
    segments = interval_video("progress-video-01")
    first = jobs.create_job("progress-video-01", "30m")
    second = jobs.create_job("progress-video-01", "60m", "30m")
    earlier = jobs.create_job("progress-video-01", "20m", "10m")
    _submit_single(first, "first", segments[0])
    _submit_single(second, "second", next(item for item in segments if item["start_seconds"] == 1800))
    assert get_video("progress-video-01")["last_processed_seconds"] == 3600
    selected = select_questions("random", 2, ["progress-video-01"], until="60m")
    assert {item["id"] for item in selected} == {"first-question", "second-question"}
    selected_range = select_questions("random", 1, ["progress-video-01"], start="30m", until="60m")
    assert [item["id"] for item in selected_range] == ["second-question"]
    _submit_single(earlier, "earlier", segments[1])
    assert get_video("progress-video-01")["last_processed_seconds"] == 3600


def test_validator_uses_lower_and_upper_job_boundaries():
    segments = interval_video("validation-range-01")
    job = jobs.create_job("validation-range-01", "60m", "30m")
    outside = {
        "id": "outside-concept", "title": "Concepto fuera", "topic": "Intervalos", "subtopic": None,
        "summary": "Resumen suficientemente descriptivo del concepto generado.", "importance": "high", "difficulty": 2,
        "exam_relevant": True, "source_segment_ids": [segments[0]["id"]], "source_start": 0, "source_end": 10,
    }
    jobs.write_submission(str(job["id"]), "concepts.json", [outside])
    report = jobs.validate_job(str(job["id"]))
    assert "outside_job_range" in {issue["code"] for issue in report["issues"]}

    upper_job = jobs.create_job("validation-range-01", "60m", "30m")
    upper = dict(outside, id="upper-concept", source_segment_ids=[segments[-1]["id"]], source_start=3600, source_end=3610)
    jobs.write_submission(str(upper_job["id"]), "concepts.json", [upper])
    upper_report = jobs.validate_job(str(upper_job["id"]))
    upper_codes = {issue["code"] for issue in upper_report["issues"]}
    assert {"outside_job_range", "missing_source_segment"} <= upper_codes


def test_overlapping_job_is_allowed_with_warning():
    interval_video("overlap-video-01")
    jobs.create_job("overlap-video-01", "30m")
    second = jobs.create_job("overlap-video-01", "40m", "20m")
    assert second["warnings"]
