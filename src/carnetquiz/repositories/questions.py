from __future__ import annotations

import json

from ..database import connect


def list_questions(
    video_ids: list[str] | None = None,
    start: float | None = None,
    until: float | None = None,
) -> list[dict[str, object]]:
    sql = "SELECT q.*, c.topic FROM questions q JOIN concepts c ON c.id=q.concept_id WHERE q.status='valid'"
    values: list[object] = []
    if video_ids:
        sql += f" AND q.video_id IN ({','.join('?' * len(video_ids))})"; values.extend(video_ids)
    if start is not None:
        sql += " AND q.source_start >= ?"; values.append(start)
    if until is not None:
        sql += " AND q.source_start < ?"; values.append(until)
    with connect() as db:
        rows = [dict(row) for row in db.execute(sql, values)]
    for row in rows: row["options"] = json.loads(str(row.pop("options_json")))
    return rows


def list_concept_ids() -> set[str]:
    with connect() as db:
        return {str(row["id"]) for row in db.execute("SELECT id FROM concepts")}


def list_question_ids() -> set[str]:
    with connect() as db:
        return {str(row["id"]) for row in db.execute("SELECT id FROM questions")}


def question_statistics() -> dict[str, int]:
    with connect() as db:
        row = db.execute("SELECT COUNT(*) total, SUM(shown_count) shown, SUM(correct_count) correct, SUM(wrong_count) wrong FROM questions WHERE status='valid'").fetchone()
    return {key: int(row[key] or 0) for key in row.keys()}


def create_attempt(attempt_id: str, video_ids: list[str], mode: str, question_count: int, seed: int | None) -> None:
    from ..database import now
    with connect() as db:
        db.execute("INSERT INTO attempts(id,created_at,video_ids,selection_mode,question_count,seed) VALUES(?,?,?,?,?,?)", (attempt_id, now(), json.dumps(video_ids), mode, question_count, seed))


def record_answer(attempt_id: str, question_id: str, chosen: str, correct: str, elapsed: float | None, position: int) -> bool:
    from ..database import now
    result = chosen == correct
    with connect() as db:
        db.execute("INSERT INTO answers(attempt_id,question_id,chosen_option,correct_option,is_correct,elapsed_seconds,position) VALUES(?,?,?,?,?,?,?)", (attempt_id, question_id, chosen, correct, int(result), elapsed, position))
        db.execute("UPDATE questions SET shown_count=shown_count+1, correct_count=correct_count+?, wrong_count=wrong_count+?, last_shown_at=? WHERE id=?", (int(result), int(not result), now(), question_id))
        db.execute("UPDATE attempts SET correct_count=correct_count+?, wrong_count=wrong_count+? WHERE id=?", (int(result), int(not result), attempt_id))
    return result


def get_attempt(attempt_id: str) -> dict[str, object]:
    with connect() as db:
        attempt = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
        answers = db.execute("SELECT a.*, q.question, q.explanation, q.options_json FROM answers a JOIN questions q ON q.id=a.question_id WHERE a.attempt_id=? ORDER BY a.position", (attempt_id,)).fetchall()
    if not attempt: raise KeyError("Intento no encontrado")
    result = dict(attempt); result["answers"] = [dict(row) for row in answers]
    return result
