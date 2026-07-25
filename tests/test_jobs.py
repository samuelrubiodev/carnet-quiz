from __future__ import annotations

from carnetquiz.repositories.questions import list_questions
from carnetquiz.schemas import SegmentInput
from carnetquiz.services import jobs
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
