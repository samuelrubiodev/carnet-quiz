from __future__ import annotations

from ..database import connect
from ..repositories.questions import question_statistics


def dashboard_statistics() -> dict[str, object]:
    overall = question_statistics()
    with connect() as db:
        topic_rows = db.execute("SELECT c.topic, COUNT(*) questions, SUM(q.correct_count) correct, SUM(q.wrong_count) wrong FROM questions q JOIN concepts c ON c.id=q.concept_id WHERE q.status='valid' GROUP BY c.topic ORDER BY wrong DESC").fetchall()
        recent = db.execute("SELECT * FROM attempts ORDER BY created_at DESC LIMIT 10").fetchall()
    overall["topics"] = [dict(row) for row in topic_rows]; overall["recent_attempts"] = [dict(row) for row in recent]
    return overall
