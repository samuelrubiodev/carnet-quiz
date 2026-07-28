from __future__ import annotations

import json

from ..database import connect


def list_questions(
    video_ids: list[str] | None = None,
    start: float | None = None,
    until: float | None = None,
) -> list[dict[str, object]]:
    sql = (
        "SELECT q.*, c.topic, v.url AS video_url, v.title AS video_title "
        "FROM questions q "
        "JOIN concepts c ON c.id=q.concept_id "
        "JOIN videos v ON v.id=q.video_id "
        "WHERE q.status='valid'"
    )
    values: list[object] = []
    if video_ids:
        sql += f" AND q.video_id IN ({','.join('?' * len(video_ids))})"
        values.extend(video_ids)
    if start is not None:
        sql += " AND q.source_start >= ?"
        values.append(start)
    if until is not None:
        sql += " AND q.source_start < ?"
        values.append(until)
    with connect() as db:
        rows = [dict(row) for row in db.execute(sql, values)]
    for row in rows:
        row["options"] = json.loads(str(row.pop("options_json")))
    return rows


def list_concept_ids() -> set[str]:
    with connect() as db:
        return {str(row["id"]) for row in db.execute("SELECT id FROM concepts")}


def list_question_ids() -> set[str]:
    with connect() as db:
        return {str(row["id"]) for row in db.execute("SELECT id FROM questions")}


def question_statistics() -> dict[str, int]:
    with connect() as db:
        row = db.execute(
            "SELECT COUNT(*) total, "
            "SUM(CASE WHEN shown_count > 0 THEN 1 ELSE 0 END) seen, "
            "SUM(CASE WHEN shown_count = 0 THEN 1 ELSE 0 END) remaining, "
            "SUM(shown_count) shown, SUM(correct_count) correct, SUM(wrong_count) wrong "
            "FROM questions WHERE status='valid'"
        ).fetchone()
    return {key: int(row[key] or 0) for key in row.keys()}


def create_attempt(
    attempt_id: str,
    video_ids: list[str],
    mode: str,
    question_count: int,
    seed: int | None,
) -> None:
    from ..database import now

    with connect() as db:
        db.execute(
            "INSERT INTO attempts(id,created_at,video_ids,selection_mode,question_count,seed) "
            "VALUES(?,?,?,?,?,?)",
            (attempt_id, now(), json.dumps(video_ids), mode, question_count, seed),
        )


def record_answer(
    attempt_id: str,
    question_id: str,
    chosen: str,
    correct: str,
    elapsed: float | None,
    position: int,
) -> bool:
    from ..database import now

    result = chosen == correct
    with connect() as db:
        db.execute(
            "INSERT INTO answers(attempt_id,question_id,chosen_option,correct_option,"
            "is_correct,elapsed_seconds,position) VALUES(?,?,?,?,?,?,?)",
            (
                attempt_id,
                question_id,
                chosen,
                correct,
                int(result),
                elapsed,
                position,
            ),
        )
        db.execute(
            "UPDATE questions SET shown_count=shown_count+1, correct_count=correct_count+?, "
            "wrong_count=wrong_count+?, last_shown_at=? WHERE id=?",
            (int(result), int(not result), now(), question_id),
        )
        db.execute(
            "UPDATE attempts SET correct_count=correct_count+?, wrong_count=wrong_count+? WHERE id=?",
            (int(result), int(not result), attempt_id),
        )
    return result


def _fragment_url(url: object, source_start: object) -> str | None:
    if not url or source_start is None:
        return None
    separator = "&" if "?" in str(url) else "?"
    return f"{url}{separator}t={max(0, int(float(source_start)))}s"


def get_attempt(attempt_id: str) -> dict[str, object]:
    """Return attempt plus one prepared presentation model per answer.

    The answer query joins every required parent record once. Templates receive
    readable option text, not the persisted JSON payload.
    """
    with connect() as db:
        attempt = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        answers = db.execute(
            "SELECT a.position, a.question_id, a.chosen_option, a.is_correct, "
            "q.question, q.explanation, q.options_json, q.correct_option, "
            "q.source_start, q.source_end, c.topic, v.url AS video_url "
            "FROM answers a "
            "JOIN questions q ON q.id=a.question_id "
            "JOIN concepts c ON c.id=q.concept_id "
            "LEFT JOIN videos v ON v.id=q.video_id "
            "WHERE a.attempt_id=? ORDER BY a.position",
            (attempt_id,),
        ).fetchall()
    if not attempt:
        raise KeyError("Intento no encontrado")

    presentation: list[dict[str, object]] = []
    for row in answers:
        options = json.loads(str(row["options_json"]))
        options_by_id = {str(option["id"]): str(option["text"]) for option in options}
        chosen_id = str(row["chosen_option"])
        correct_id = str(row["correct_option"])
        source_start = row["source_start"]
        source_end = row["source_end"]
        presentation.append(
            {
                "position": int(row["position"]),
                "question_id": str(row["question_id"]),
                "question": str(row["question"]),
                "is_correct": bool(row["is_correct"]),
                "chosen_option_id": chosen_id,
                "chosen_option_text": options_by_id.get(chosen_id, "Opción no disponible"),
                "correct_option_id": correct_id,
                "correct_option_text": options_by_id.get(correct_id, "Opción no disponible"),
                "explanation": str(row["explanation"]),
                "source_start": source_start,
                "source_end": source_end,
                "topic": row["topic"] or "Sin tema",
                "video_url": row["video_url"],
                "fragment_url": _fragment_url(row["video_url"], source_start),
            }
        )

    result = dict(attempt)
    result["answers"] = presentation
    return result
