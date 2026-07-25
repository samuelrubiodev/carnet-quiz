from __future__ import annotations

import sqlite3

_ALLOWED_TABLES = {
    "answers",
    "attempts",
    "questions",
    "concepts",
    "jobs",
    "transcript_segments",
    "videos",
}


def delete_ids(connection: sqlite3.Connection, table: str, ids: list[str]) -> None:
    """Borra identificadores de tablas de estudio permitidas; nunca SQL arbitrario."""
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Tabla no permitida: {table}")
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    connection.execute(f"DELETE FROM {table} WHERE id IN ({placeholders})", ids)


def reset_study_data(connection: sqlite3.Connection) -> None:
    for table in (
        "answers",
        "attempts",
        "questions",
        "concepts",
        "jobs",
        "transcript_segments",
        "videos",
    ):
        connection.execute(f"DELETE FROM {table}")
    connection.execute(
        "DELETE FROM sqlite_sequence WHERE name IN ('answers', 'transcript_segments')"
    )


def recalculate_job_counts(connection: sqlite3.Connection) -> None:
    connection.execute(
        "UPDATE jobs SET concept_count=(SELECT COUNT(*) FROM concepts WHERE concepts.job_id=jobs.id), "
        "question_count=(SELECT COUNT(*) FROM questions WHERE questions.job_id=jobs.id)"
    )


def recalculate_video_progress(
    connection: sqlite3.Connection, video_ids: list[str]
) -> None:
    for video_id in video_ids:
        connection.execute(
            "UPDATE videos SET last_processed_seconds=COALESCE(("
            "SELECT MAX(end_seconds) FROM jobs WHERE jobs.video_id=? "
            "AND (jobs.imported_at IS NOT NULL OR jobs.status='committed')"
            "), 0) WHERE id=?",
            (video_id, video_id),
        )


def recalculate_question_statistics(connection: sqlite3.Connection) -> None:
    connection.execute(
        "UPDATE questions SET "
        "shown_count=(SELECT COUNT(*) FROM answers WHERE answers.question_id=questions.id), "
        "correct_count=COALESCE((SELECT SUM(is_correct) FROM answers WHERE answers.question_id=questions.id), 0), "
        "wrong_count=COALESCE((SELECT SUM(CASE WHEN is_correct=0 THEN 1 ELSE 0 END) FROM answers WHERE answers.question_id=questions.id), 0), "
        "last_shown_at=(SELECT MAX(attempts.created_at) FROM answers JOIN attempts ON attempts.id=answers.attempt_id WHERE answers.question_id=questions.id)"
    )
