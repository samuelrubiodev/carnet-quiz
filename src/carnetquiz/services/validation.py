from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from pydantic import ValidationError

from ..config import get_settings
from ..repositories import questions as question_repo
from ..repositories import videos as video_repo
from ..schemas import ConceptInput, QuestionInput, ValidationIssue, ValidationReport

_HTML = re.compile(r"<[^>]+>")
_WORDS = re.compile(r"\b(?:el|la|los|las|un|una|de|del|y|o|en|a|que|es|se)\b", re.I)


def normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value)).strip()


def fingerprint(question: str) -> str:
    compact = _WORDS.sub(" ", normalized_text(question)); return hashlib.sha256(compact.encode()).hexdigest()


def _read_array(path: Path) -> list[object]:
    if not path.exists(): return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list): raise ValueError(f"{path.name} debe contener lista JSON")
    return payload


def validate_job_directory(job: dict[str, object]) -> tuple[ValidationReport, list[ConceptInput], list[QuestionInput]]:
    directory = Path(str(job["directory"])); report = ValidationReport(job_id=str(job["id"]))
    try: raw_concepts = _read_array(directory / "concepts.json")
    except (ValueError, json.JSONDecodeError) as error: raw_concepts = []; report.issues.append(ValidationIssue(level="error", code="concepts_json", message=str(error)))
    try: raw_questions = _read_array(directory / "questions.json")
    except (ValueError, json.JSONDecodeError) as error: raw_questions = []; report.issues.append(ValidationIssue(level="error", code="questions_json", message=str(error)))
    segments = {
        int(segment["id"]): segment
        for segment in video_repo.list_segments(
            str(job["video_id"]),
            start=float(job["start_seconds"]),
            until=float(job["end_seconds"]),
        )
    }
    concepts: list[ConceptInput] = []; seen_concepts: set[str] = set()
    existing_concept_ids = question_repo.list_concept_ids()
    for raw in raw_concepts:
        try: concept = ConceptInput.model_validate(raw)
        except ValidationError as error:
            report.issues.append(ValidationIssue(level="error", code="invalid_concept", message=str(error), item_id=str(raw.get("id")) if isinstance(raw, dict) else None)); continue
        if concept.id in seen_concepts or concept.id in existing_concept_ids:
            report.issues.append(ValidationIssue(level="error", code="duplicate_concept_id", message="ID de concepto ya utilizado", item_id=concept.id)); continue
        seen_concepts.add(concept.id)
        _validate_sources(concept.id, concept.source_segment_ids, concept.source_start, concept.source_end, segments, job, report)
        if not any(issue.item_id == concept.id and issue.level == "error" for issue in report.issues): concepts.append(concept); report.valid_concept_ids.append(concept.id)
    questions: list[QuestionInput] = []; seen_questions: set[str] = set(); normalized_questions: list[tuple[str, str]] = []
    existing = [(str(row["id"]), str(row["question"])) for row in question_repo.list_questions()]
    existing_question_ids = question_repo.list_question_ids()
    for raw in raw_questions:
        try: question = QuestionInput.model_validate(raw)
        except ValidationError as error:
            report.issues.append(ValidationIssue(level="error", code="invalid_question", message=str(error), item_id=str(raw.get("id")) if isinstance(raw, dict) else None)); continue
        error_before = len(report.errors)
        if question.id in seen_questions or question.id in existing_question_ids:
            report.issues.append(ValidationIssue(level="error", code="duplicate_question_id", message="ID de pregunta ya utilizado", item_id=question.id))
        seen_questions.add(question.id)
        if question.concept_id not in report.valid_concept_ids: report.issues.append(ValidationIssue(level="error", code="unknown_concept", message="Concepto inexistente o inválido", item_id=question.id))
        _validate_sources(question.id, question.source_segment_ids, question.source_start, question.source_end, segments, job, report)
        option_ids = [option.id for option in question.options]; option_texts = [normalized_text(option.text) for option in question.options]
        if len(set(option_ids)) != len(option_ids): report.issues.append(ValidationIssue(level="error", code="duplicate_option_id", message="Opciones con ID repetido", item_id=question.id))
        if len(set(option_texts)) != len(option_texts): report.issues.append(ValidationIssue(level="error", code="duplicate_option_text", message="Opciones idénticas", item_id=question.id))
        if question.correct_option not in option_ids: report.issues.append(ValidationIssue(level="error", code="missing_correct_option", message="Respuesta correcta ausente", item_id=question.id))
        if _HTML.search(question.question + question.explanation + " ".join(option.text for option in question.options)): report.issues.append(ValidationIssue(level="error", code="html", message="HTML no permitido", item_id=question.id))
        if question.type == "negative" and not any(token in question.question.upper() for token in ("NO", "EXCEPTO", "INCORRECTA")): report.issues.append(ValidationIssue(level="error", code="unclear_negative", message="Pregunta negativa debe destacar NO, EXCEPTO o INCORRECTA", item_id=question.id))
        candidate = normalized_text(question.question)
        for previous_id, previous in [*normalized_questions, *existing]:
            if SequenceMatcher(None, candidate, normalized_text(previous)).ratio() >= get_settings().duplicate_threshold:
                report.issues.append(ValidationIssue(level="error", code="similar_question", message=f"Demasiado similar a {previous_id}", item_id=question.id)); break
        normalized_questions.append((question.id, question.question))
        if len(report.errors) == error_before: questions.append(question); report.valid_question_ids.append(question.id)
    return report, concepts, questions


def _validate_sources(item_id: str, ids: list[int], start: float, end: float, segments: dict[int, dict[str, object]], job: dict[str, object], report: ValidationReport) -> None:
    if end <= start or start < float(job["start_seconds"]) or end > float(job["end_seconds"]): report.issues.append(ValidationIssue(level="error", code="outside_job_range", message="Tiempos fuera del intervalo del trabajo", item_id=item_id))
    missing = [segment_id for segment_id in ids if segment_id not in segments]
    if missing: report.issues.append(ValidationIssue(level="error", code="missing_source_segment", message=f"Segmentos inexistentes o fuera de intervalo: {missing}", item_id=item_id))
