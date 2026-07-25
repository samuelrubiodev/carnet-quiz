from __future__ import annotations

from ..database import initialize
from ..repositories.questions import list_questions
from ..repositories.videos import list_segments
from ..schemas import SegmentInput, SubtitleType
from .jobs import commit_job, create_job, write_submission
from .transcripts import import_segments
from .videos import add_demo_video


def create_demo() -> dict[str, object]:
    initialize()
    video_id = "demo-signals-001"
    existing = [question for question in list_questions([video_id])]
    if existing:
        return {"video_id": video_id, "questions": len(existing), "status": "already_loaded"}
    add_demo_video(video_id, "Demo: prioridad de señales", 180)
    if not list_segments(video_id):
        import_segments(video_id, [
            SegmentInput(start_seconds=0, end_seconds=12, text="Las órdenes de los agentes de tráfico prevalecen sobre las demás señales.", original_text="Las órdenes de los agentes de tráfico prevalecen sobre las demás señales.", subtitle_type=SubtitleType.IMPORTED),
            SegmentInput(start_seconds=12, end_seconds=25, text="Una señal luminosa roja obliga a detenerse antes de la línea de detención.", original_text="Una señal luminosa roja obliga a detenerse antes de la línea de detención.", subtitle_type=SubtitleType.IMPORTED),
            SegmentInput(start_seconds=25, end_seconds=40, text="La señal amarilla fija obliga a detenerse salvo que no pueda hacerlo en condiciones de seguridad.", original_text="La señal amarilla fija obliga a detenerse salvo que no pueda hacerlo en condiciones de seguridad.", subtitle_type=SubtitleType.IMPORTED),
        ], SubtitleType.IMPORTED)
    job = create_job(video_id, "40s")
    segments = list_segments(video_id, 40); ids = [int(item["id"]) for item in segments]
    concepts = [{"id": "priority-signals-001", "title": "Prioridad de agentes", "topic": "Señalización", "subtopic": "Prioridad", "summary": "Las órdenes de los agentes tienen prioridad sobre las demás señales.", "importance": "high", "difficulty": 2, "exam_relevant": True, "source_segment_ids": [ids[0]], "source_start": 0, "source_end": 12}, {"id": "red-light-001", "title": "Luz roja", "topic": "Señalización", "subtopic": "Semáforos", "summary": "La luz roja obliga a detenerse antes de la línea de detención.", "importance": "high", "difficulty": 1, "exam_relevant": True, "source_segment_ids": [ids[1]], "source_start": 12, "source_end": 25}]
    questions = [{"id": "priority-signals-001-q01", "concept_id": "priority-signals-001", "type": "practical_case", "difficulty": 2, "question": "Un agente ordena continuar con semáforo rojo. ¿Qué debe hacer conductor?", "options": [{"id":"a","text":"Detenerse por semáforo rojo"},{"id":"b","text":"Obedecer al agente y continuar"},{"id":"c","text":"Esperar otro vehículo"}], "correct_option":"b", "explanation":"Órdenes de agentes prevalecen sobre demás señales.", "source_segment_ids":[ids[0]], "source_start":0, "source_end":12}, {"id": "red-light-001-q01", "concept_id": "red-light-001", "type": "direct", "difficulty": 1, "question": "¿Qué obliga a hacer señal luminosa roja?", "options": [{"id":"a","text":"Reducir velocidad"},{"id":"b","text":"Continuar con precaución"},{"id":"c","text":"Detenerse antes de línea de detención"}], "correct_option":"c", "explanation":"La señal roja obliga a detenerse antes de la línea de detención.", "source_segment_ids":[ids[1]], "source_start":12, "source_end":25}]
    write_submission(str(job["id"]), "concepts.json", concepts); write_submission(str(job["id"]), "questions.json", questions)
    from .jobs import validate_job
    validate_job(str(job["id"])); imported = commit_job(str(job["id"]))
    return {"video_id": video_id, "job_id": job["id"], **imported}
