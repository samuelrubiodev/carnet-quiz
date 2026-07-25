from __future__ import annotations

import json
import re
import shutil
import sqlite3
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ..config import Settings, get_settings
from ..database import connect, initialize, transaction
from ..repositories import data_management as data_repo

RESOURCES = ("video", "transcript", "job", "concept", "question", "attempt")
_COUNT_KEYS = (
    "videos",
    "transcript_segments",
    "jobs",
    "concepts",
    "questions",
    "attempts",
    "answers",
)
_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$")
_RESET_CONFIRMATION = "RESET CARNETQUIZ"


class DataManagementError(RuntimeError):
    """Error controlado de una operación de administración de datos."""


class ResourceNotFound(DataManagementError):
    pass


class DeletionBlocked(DataManagementError):
    pass


class PathSafetyError(DataManagementError):
    pass


class IntegrityError(DataManagementError):
    pass


@dataclass(slots=True)
class DeletionPlan:
    operation: str
    resource: str | None
    identifier: str | None
    cascade: bool
    affected: dict[str, list[str]]
    file_paths: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocked: bool = False
    database_path: Path = field(default_factory=Path)
    data_dir: Path = field(default_factory=Path)
    settings: Settings | None = field(default=None, repr=False, compare=False)

    @property
    def affected_counts(self) -> dict[str, int]:
        return {key: len(self.affected.get(key, [])) for key in _COUNT_KEYS} | {
            "files": len(self.file_paths)
        }

    @property
    def counts(self) -> dict[str, int]:
        counts = {key: 0 for key in _COUNT_KEYS} | {"files": len(self.file_paths)}
        if self.operation == "reset" or self.resource == "video":
            return self.affected_counts
        if self.resource == "transcript":
            counts["transcript_segments"] = len(self.affected.get("transcript_segments", []))
            if self.cascade:
                for key in ("jobs", "concepts", "questions", "attempts", "answers"):
                    counts[key] = len(self.affected.get(key, []))
            return counts
        if self.resource == "job":
            for key in ("jobs", "concepts", "questions", "attempts", "answers"):
                counts[key] = len(self.affected.get(key, []))
        elif self.resource == "concept":
            for key in ("concepts", "questions", "attempts", "answers"):
                counts[key] = len(self.affected.get(key, []))
        elif self.resource == "question":
            for key in ("questions", "attempts", "answers"):
                counts[key] = len(self.affected.get(key, []))
        elif self.resource == "attempt":
            for key in ("attempts", "answers"):
                counts[key] = len(self.affected.get(key, []))
        return counts

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "resource": self.resource,
            "identifier": self.identifier,
            "cascade": self.cascade,
            "affected": self.affected,
            "counts": self.counts,
            "affected_counts": self.affected_counts,
            "files": [str(path) for path in self.file_paths],
            "warnings": self.warnings,
            "blocked": self.blocked,
            "database_path": str(self.database_path),
            "data_dir": str(self.data_dir),
        }


def validate_resource_options(resource: str, cascade: bool = False) -> None:
    if resource not in RESOURCES:
        raise DataManagementError(
            f"Recurso desconocido: {resource}. Usá uno de: {', '.join(RESOURCES)}"
        )
    if cascade and resource != "transcript":
        raise DataManagementError(
            f"--cascade solo es válido para el recurso transcript; {resource} se elimina con su semántica fija"
        )


def validate_identifier(identifier: str) -> str:
    if (
        not identifier
        or ".." in identifier
        or "/" in identifier
        or "\\" in identifier
        or Path(identifier).is_absolute()
        or not _ID_PATTERN.fullmatch(identifier)
    ):
        raise DataManagementError(f"Identificador inválido: {identifier!r}")
    return identifier


def validate_deletion_path(path: Path, allowed_roots: Iterable[Path]) -> Path:
    """Comprueba que path está estrictamente dentro de una raíz permitida."""
    raw = Path(path)
    if ".." in raw.parts:
        raise PathSafetyError(f"Ruta no permitida: contiene '..': {raw}")
    candidate = raw.resolve(strict=False)
    roots = [Path(root).resolve(strict=False) for root in allowed_roots]
    if raw.is_symlink():
        raise PathSafetyError(f"Enlace simbólico no permitido: {raw}")
    if any(candidate == root for root in roots) or not any(
        candidate.is_relative_to(root) for root in roots
    ):
        raise PathSafetyError(f"Ruta fuera de directorios permitidos: {raw}")
    return candidate


def _validate_tree(path: Path, allowed_roots: Iterable[Path]) -> None:
    checked = validate_deletion_path(path, allowed_roots)
    if checked.is_dir() and not checked.is_symlink():
        for child in checked.iterdir():
            _validate_tree(child, allowed_roots)


def _read_connection(settings: Settings) -> sqlite3.Connection | None:
    if not settings.database_path.exists():
        return None
    connection = sqlite3.connect(
        f"file:{settings.database_path}?mode=ro", uri=True, timeout=30
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _rows(connection: sqlite3.Connection, query: str, values: Iterable[object] = ()) -> list[dict[str, object]]:
    return [dict(row) for row in connection.execute(query, tuple(values)).fetchall()]


def _one(connection: sqlite3.Connection, query: str, values: Iterable[object] = ()) -> dict[str, object] | None:
    row = connection.execute(query, tuple(values)).fetchone()
    return dict(row) if row else None


def _in_clause(values: list[str]) -> tuple[str, list[str]]:
    return ",".join("?" for _ in values), values


def _attempt_ids(
    connection: sqlite3.Connection,
    question_ids: list[str],
    video_id: str | None = None,
) -> list[str]:
    ids: set[str] = set()
    if question_ids:
        placeholders, values = _in_clause(question_ids)
        ids.update(
            row["attempt_id"]
            for row in _rows(
                connection,
                f"SELECT DISTINCT attempt_id FROM answers WHERE question_id IN ({placeholders})",
                values,
            )
        )
    if video_id is not None:
        for row in _rows(connection, "SELECT id, video_ids FROM attempts"):
            try:
                selected_videos = json.loads(str(row["video_ids"]))
            except (TypeError, json.JSONDecodeError):
                selected_videos = []
            if video_id in selected_videos:
                ids.add(str(row["id"]))
    return sorted(ids)


def _affected_for_ids(
    connection: sqlite3.Connection,
    *,
    video_ids: list[str],
    job_ids: list[str],
    concept_ids: list[str],
    question_ids: list[str],
    attempt_ids: list[str],
) -> dict[str, list[str]]:
    return {
        "videos": sorted(video_ids),
        "transcript_segments": sorted(
            str(row["id"])
            for row in (
                _rows(
                    connection,
                    f"SELECT id FROM transcript_segments WHERE video_id IN ({_in_clause(video_ids)[0]})",
                    video_ids,
                )
                if video_ids
                else []
            )
        ),
        "jobs": sorted(job_ids),
        "concepts": sorted(concept_ids),
        "questions": sorted(question_ids),
        "attempts": sorted(attempt_ids),
        "answers": sorted(
            str(row["id"])
            for row in (
                _rows(
                    connection,
                    f"SELECT id FROM answers WHERE attempt_id IN ({_in_clause(attempt_ids)[0]})",
                    attempt_ids,
                )
                if attempt_ids
                else []
            )
        ),
    }


def _add_path(
    paths: list[Path],
    warnings: list[str],
    path: Path,
    roots: list[Path],
) -> None:
    checked = validate_deletion_path(path, roots)
    _validate_tree(checked, roots)
    if not checked.exists() and not checked.is_symlink():
        warnings.append(f"Archivo o directorio ausente: {path}")
        return
    if checked not in paths:
        paths.append(checked)


def _transcript_paths(
    video_id: str,
    transcript_path: object,
    settings: Settings,
    paths: list[Path],
    warnings: list[str],
) -> None:
    roots = [settings.transcripts_dir]
    if transcript_path:
        _add_path(paths, warnings, Path(str(transcript_path)), roots)
    if settings.transcripts_dir.is_dir():
        for candidate in sorted(settings.transcripts_dir.glob(f"{video_id}.*")):
            _add_path(paths, warnings, candidate, roots)


def _job_paths(
    jobs: list[dict[str, object]],
    settings: Settings,
    paths: list[Path],
    warnings: list[str],
) -> None:
    roots = [settings.jobs_dir]
    for job in jobs:
        _add_path(paths, warnings, Path(str(job["directory"])), roots)


def _collect_reset_paths(settings: Settings, warnings: list[str]) -> list[Path]:
    paths: list[Path] = []
    roots = [settings.transcripts_dir, settings.jobs_dir]
    for root in roots:
        if not root.exists():
            continue
        if not root.is_dir():
            raise PathSafetyError(f"Directorio de datos inválido: {root}")
        for child in sorted(root.iterdir()):
            if child.name == ".gitkeep":
                continue
            _add_path(paths, warnings, child, roots)
    return paths


def _build_plan_from_db(
    resource: str, identifier: str, cascade: bool, settings: Settings
) -> DeletionPlan:
    validate_resource_options(resource, cascade)
    identifier = validate_identifier(identifier)
    connection = _read_connection(settings)
    if connection is None:
        raise ResourceNotFound(f"{resource.capitalize()} no encontrado: {identifier}")
    try:
        if resource in {"video", "transcript"}:
            video = _one(connection, "SELECT * FROM videos WHERE id=?", (identifier,))
            if video is None:
                raise ResourceNotFound(f"Vídeo no encontrado: {identifier}")
            video_ids = [identifier]
            jobs = _rows(connection, "SELECT * FROM jobs WHERE video_id=?", video_ids)
            job_ids = [str(row["id"]) for row in jobs]
            concepts = _rows(connection, "SELECT id FROM concepts WHERE video_id=?", video_ids)
            concept_ids = [str(row["id"]) for row in concepts]
            questions = _rows(connection, "SELECT id FROM questions WHERE video_id=?", video_ids)
            question_ids = [str(row["id"]) for row in questions]
            attempt_ids = _attempt_ids(connection, question_ids, identifier)
            affected = _affected_for_ids(
                connection,
                video_ids=video_ids,
                job_ids=job_ids,
                concept_ids=concept_ids,
                question_ids=question_ids,
                attempt_ids=attempt_ids,
            )
            warnings: list[str] = []
            file_paths: list[Path] = []
            if resource == "video":
                _transcript_paths(
                    identifier, video.get("transcript_path"), settings, file_paths, warnings
                )
                _job_paths(jobs, settings, file_paths, warnings)
            else:
                _transcript_paths(
                    identifier, video.get("transcript_path"), settings, file_paths, warnings
                )
            blocked = resource == "transcript" and bool(job_ids or concept_ids or question_ids)
            if blocked:
                warnings.append(
                    "El borrado está bloqueado: existen trabajos, conceptos o preguntas derivados; usá --cascade"
                )
            return DeletionPlan(
                operation="delete",
                resource=resource,
                identifier=identifier,
                cascade=cascade,
                affected=affected,
                file_paths=file_paths,
                warnings=warnings,
                blocked=blocked and not cascade,
                database_path=settings.database_path,
                data_dir=settings.data_dir,
                settings=settings,
            )

        row = _one(connection, f"SELECT * FROM {resource}s WHERE id=?", (identifier,))
        if row is None:
            raise ResourceNotFound(f"{resource.capitalize()} no encontrado: {identifier}")
        if resource == "job":
            video_ids = [str(row["video_id"])]
            job_ids = [identifier]
            concept_ids = [
                str(item["id"])
                for item in _rows(connection, "SELECT id FROM concepts WHERE job_id=?", (identifier,))
            ]
            question_ids = [
                str(item["id"])
                for item in _rows(connection, "SELECT id FROM questions WHERE job_id=?", (identifier,))
            ]
        elif resource == "concept":
            video_ids = [str(row["video_id"])]
            job_ids = [str(row["job_id"])]
            concept_ids = [identifier]
            question_ids = [
                str(item["id"])
                for item in _rows(connection, "SELECT id FROM questions WHERE concept_id=?", (identifier,))
            ]
        elif resource == "question":
            video_ids = [str(row["video_id"])]
            job_ids = [str(row["job_id"])]
            concept_ids = [str(row["concept_id"])]
            question_ids = [identifier]
        else:
            video_ids = []
            job_ids = []
            concept_ids = []
            question_ids = []

        attempt_ids = _attempt_ids(connection, question_ids)
        affected = _affected_for_ids(
            connection,
            video_ids=video_ids if resource != "attempt" else [],
            job_ids=job_ids,
            concept_ids=concept_ids,
            question_ids=question_ids,
            attempt_ids=([identifier] if resource == "attempt" else attempt_ids),
        )
        if resource not in {"video", "transcript"}:
            affected["transcript_segments"] = []
        if resource == "attempt":
            affected = {key: (value if key != "attempts" else [identifier]) for key, value in affected.items()}
            affected["answers"] = [
                str(item["id"])
                for item in _rows(connection, "SELECT id FROM answers WHERE attempt_id=?", (identifier,))
            ]
        file_paths: list[Path] = []
        warnings: list[str] = []
        if resource == "job":
            _job_paths(
                _rows(connection, "SELECT * FROM jobs WHERE id=?", (identifier,)),
                settings,
                file_paths,
                warnings,
            )
        return DeletionPlan(
            operation="delete",
            resource=resource,
            identifier=identifier,
            cascade=False,
            affected=affected,
            file_paths=file_paths,
            warnings=warnings,
            database_path=settings.database_path,
            data_dir=settings.data_dir,
            settings=settings,
        )
    finally:
        connection.close()


def build_deletion_plan(
    resource: str, identifier: str, cascade: bool = False, settings: Settings | None = None
) -> DeletionPlan:
    settings = settings or get_settings()
    return _build_plan_from_db(resource, identifier, cascade, settings)


def build_reset_plan(settings: Settings | None = None) -> DeletionPlan:
    settings = settings or get_settings()
    warnings: list[str] = []
    affected = {key: [] for key in _COUNT_KEYS}
    connection = _read_connection(settings)
    if connection is not None:
        try:
            for key, table in (
                ("videos", "videos"),
                ("transcript_segments", "transcript_segments"),
                ("jobs", "jobs"),
                ("concepts", "concepts"),
                ("questions", "questions"),
                ("attempts", "attempts"),
                ("answers", "answers"),
            ):
                id_column = "id"
                affected[key] = [str(row[id_column]) for row in _rows(connection, f"SELECT {id_column} FROM {table}")]
        finally:
            connection.close()
    file_paths = _collect_reset_paths(settings, warnings)
    return DeletionPlan(
        operation="reset",
        resource=None,
        identifier=None,
        cascade=True,
        affected=affected,
        file_paths=file_paths,
        warnings=warnings,
        database_path=settings.database_path,
        data_dir=settings.data_dir,
        settings=settings,
    )


def current_counts(settings: Settings | None = None) -> dict[str, int]:
    settings = settings or get_settings()
    result = {key: 0 for key in _COUNT_KEYS}
    connection = _read_connection(settings)
    if connection is None:
        return result
    try:
        for key, table in (
            ("videos", "videos"),
            ("transcript_segments", "transcript_segments"),
            ("jobs", "jobs"),
            ("concepts", "concepts"),
            ("questions", "questions"),
            ("attempts", "attempts"),
            ("answers", "answers"),
        ):
            result[key] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        connection.close()
    return result


def _backup_database(settings: Settings, destination: Path) -> None:
    source = sqlite3.connect(
        f"file:{settings.database_path}?mode=ro", uri=True, timeout=30
    )
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
        target.commit()
    finally:
        target.close()
        source.close()


def _backup_files(settings: Settings, plan: DeletionPlan, destination: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    roots = [settings.transcripts_dir, settings.jobs_dir]
    for source in plan.file_paths:
        if not source.exists() and not source.is_symlink():
            continue
        root = next(root for root in roots if source.is_relative_to(root.resolve()))
        relative = source.relative_to(root.resolve())
        target = destination / root.name / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir() and not source.is_symlink():
            shutil.copytree(source, target, symlinks=True)
            kind = "directory"
        else:
            shutil.copy2(source, target, follow_symlinks=False)
            kind = "file"
        entries.append({"source": str(source), "backup": str(target), "type": kind})
    return entries


def _create_backup(settings: Settings, plan: DeletionPlan) -> Path:
    backup_root = settings.data_dir.parent / "data-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    destination = backup_root / (
        f"carnetquiz-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
    )
    destination.mkdir(mode=0o700)
    _backup_database(settings, destination / settings.database_path.name)
    entries = _backup_files(settings, plan, destination / "data") if plan.operation == "reset" else []
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "operation": plan.operation,
        "resource": plan.resource,
        "identifier": plan.identifier,
        "database": str(destination / settings.database_path.name),
        "source_database": str(settings.database_path),
        "paths": entries,
        "counts": plan.counts,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destination


def _target_ids(plan: DeletionPlan, key: str) -> list[str]:
    if plan.operation == "reset":
        return plan.affected[key]
    if plan.resource == "video":
        return plan.affected[key]
    if plan.resource == "transcript":
        if key == "transcript_segments":
            return plan.affected[key]
        if key in {"jobs", "concepts", "questions"} and not plan.cascade:
            return []
        if key in {"jobs", "concepts", "questions"}:
            return plan.affected[key]
    if plan.resource == "job":
        if key in {"jobs", "concepts", "questions"}:
            return plan.affected[key]
    if plan.resource == "concept":
        if key in {"concepts", "questions"}:
            return plan.affected[key]
    if plan.resource == "question" and key == "questions":
        return plan.affected[key]
    if plan.resource == "attempt" and key == "attempts":
        return plan.affected[key]
    return []


def _delete_database_rows(
    connection: sqlite3.Connection, plan: DeletionPlan
) -> None:
    affected = plan.affected
    if plan.operation == "reset":
        data_repo.reset_study_data(connection)
        return

    data_repo.delete_ids(connection, "answers", affected["answers"])
    data_repo.delete_ids(connection, "attempts", affected["attempts"])
    data_repo.delete_ids(connection, "questions", _target_ids(plan, "questions"))
    data_repo.delete_ids(connection, "concepts", _target_ids(plan, "concepts"))
    data_repo.delete_ids(connection, "jobs", _target_ids(plan, "jobs"))
    data_repo.delete_ids(
        connection, "transcript_segments", _target_ids(plan, "transcript_segments")
    )

    if plan.resource == "transcript":
        connection.execute(
            "UPDATE videos SET transcript_path=NULL, last_processed_seconds=0, status='added' WHERE id=?",
            (plan.identifier,),
        )
    elif plan.resource == "video":
        data_repo.delete_ids(connection, "videos", affected["videos"])

    if plan.resource in {"job", "concept", "question"}:
        data_repo.recalculate_job_counts(connection)
        data_repo.recalculate_video_progress(connection, affected["videos"])
    if plan.resource in {"video", "transcript", "job", "concept", "question", "attempt"}:
        data_repo.recalculate_question_statistics(connection)


def _check_integrity(connection: sqlite3.Connection) -> None:
    foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    integrity = [row[0] for row in connection.execute("PRAGMA integrity_check").fetchall()]
    if foreign_keys or integrity != ["ok"]:
        raise IntegrityError(
            f"Comprobación SQLite fallida: foreign_key_check={foreign_keys!r}, integrity_check={integrity!r}"
        )


def _post_integrity_check(settings: Settings) -> None:
    with connect(settings) as connection:
        _check_integrity(connection)


def _cleanup_files(plan: DeletionPlan) -> list[str]:
    errors: list[str] = []
    roots = [plan.data_dir / "transcripts", plan.data_dir / "jobs"]
    for path in plan.file_paths:
        try:
            validate_deletion_path(path, roots)
            _validate_tree(path, roots)
            if not path.exists():
                raise FileNotFoundError("ruta ausente durante la limpieza")
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
        except Exception as error:  # report every failed cleanup path
            errors.append(f"{path}: {error}")
    return errors


def _result(
    plan: DeletionPlan,
    *,
    dry_run: bool,
    backup_path: Path | None,
    warnings: list[str],
    cleanup_errors: list[str] | None = None,
) -> dict[str, object]:
    cleanup_errors = cleanup_errors or []
    all_warnings = [*plan.warnings, *warnings, *cleanup_errors]
    return {
        "operation": plan.operation,
        "resource": plan.resource,
        "identifier": plan.identifier,
        "dry_run": dry_run,
        "backup_path": str(backup_path) if backup_path else None,
        "deleted": plan.counts if not dry_run else {},
        "planned": plan.counts,
        "files": [str(path) for path in plan.file_paths],
        "plan": plan.to_dict(),
        "warnings": all_warnings,
        "cleanup_complete": not cleanup_errors,
        "integrity_check": "not_run" if dry_run else "ok",
    }


def execute_plan(
    plan: DeletionPlan,
    *,
    dry_run: bool = False,
    no_backup: bool = False,
) -> dict[str, object]:
    if plan.blocked:
        raise DeletionBlocked("Borrado bloqueado por dependencias; usá --cascade")
    if dry_run:
        warnings = ["No se crea copia de seguridad durante --dry-run"]
        if no_backup:
            warnings.append("--no-backup no tiene efecto durante --dry-run")
        return _result(plan, dry_run=True, backup_path=None, warnings=warnings)

    settings = plan.settings or get_settings()
    # Verify every target again immediately before the transaction.
    _roots = [settings.transcripts_dir, settings.jobs_dir]
    for path in plan.file_paths:
        validate_deletion_path(path, _roots)
        _validate_tree(path, _roots)

    initialize(settings)
    backup_path: Path | None = None
    warnings: list[str] = []
    if no_backup:
        warnings.append("ADVERTENCIA: se omitió la copia de seguridad (--no-backup)")
    else:
        backup_path = _create_backup(settings, plan)

    with transaction(settings) as connection:
        _delete_database_rows(connection, plan)
        _check_integrity(connection)

    cleanup_errors = _cleanup_files(plan)
    _post_integrity_check(settings)
    return _result(
        plan,
        dry_run=False,
        backup_path=backup_path,
        warnings=warnings,
        cleanup_errors=cleanup_errors,
    )


def reset_data(
    *,
    dry_run: bool = False,
    no_backup: bool = False,
    settings: Settings | None = None,
) -> dict[str, object]:
    settings = settings or get_settings()
    plan = build_reset_plan(settings)
    return execute_plan(plan, dry_run=dry_run, no_backup=no_backup)


def delete_data(
    resource: str,
    identifier: str,
    *,
    cascade: bool = False,
    dry_run: bool = False,
    no_backup: bool = False,
    settings: Settings | None = None,
) -> dict[str, object]:
    settings = settings or get_settings()
    plan = build_deletion_plan(resource, identifier, cascade, settings)
    return execute_plan(plan, dry_run=dry_run, no_backup=no_backup)


def confirmation_phrase() -> str:
    return _RESET_CONFIRMATION


def reset_confirmation_is_valid(value: str | None) -> bool:
    return value == _RESET_CONFIRMATION
