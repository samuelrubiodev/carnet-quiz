from __future__ import annotations

import inspect

from fastapi.testclient import TestClient

from carnetquiz.mcp_server.server import build_server
from carnetquiz.repositories.questions import (
    create_attempt,
    get_attempt,
    list_questions,
    question_statistics,
    record_answer,
)
from carnetquiz.services.demo import create_demo
from carnetquiz.services.selection import select_questions, shuffle_options
from carnetquiz.web.app import create_app


def test_selection_modes_and_option_shuffle():
    create_demo()
    for mode in ("random", "balanced", "new", "wrong_review", "smart", "exam"):
        assert select_questions(mode, 1)
    question = select_questions("random", 1, seed=4)[0]
    shown = shuffle_options(question, seed=1)
    assert {item["id"] for item in shown["options"]} == {item["id"] for item in question["options"]}
    assert shown["correct_option"] in {item["id"] for item in shown["options"]}


def test_web_demo_test_and_result():
    create_demo(); client = TestClient(create_app())
    assert client.get("/").status_code == 200
    jobs_page = client.get("/jobs")
    assert "00:00:00 – 00:00:40" in jobs_page.text
    assert "Desde" in jobs_page.text and "Hasta" in jobs_page.text
    created = client.post("/jobs", data={"video_id": "demo-signals-001", "start": "0s", "until": "30s"}, follow_redirects=False)
    assert created.status_code == 303
    assert "warning=" in created.headers["location"]
    response = client.post("/tests", data={"mode":"random", "count":"1"}, follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    page = client.get(location); assert page.status_code == 200
    attempt, position = location.split("/")[2:4]
    response = client.post(location, data={"option":"a"})
    assert response.status_code == 200
    assert client.get(f"/results/{attempt}").status_code == 200


def test_web_resources_empty_states_and_wrong_review_mode():
    client = TestClient(create_app())
    for path in ("/", "/videos", "/jobs", "/tests/new", "/statistics", "/admin/data"):
        assert client.get(path).status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    missing = client.get("/missing")
    assert missing.status_code == 404
    assert "Ir al inicio" in missing.text
    wrong_review = client.get("/tests/new?mode=wrong_review")
    assert 'value="wrong_review" checked' in wrong_review.text


def test_question_feedback_exam_and_presented_result_model():
    create_demo()
    app = create_app()
    client = TestClient(app)
    started = client.post("/tests", data={"mode": "random", "count": "1"}, follow_redirects=False)
    location = started.headers["location"]
    attempt_id = location.split("/")[2]
    question_page = client.get(location)
    question = app.state.tests[attempt_id][0]
    option_ids = {option["id"] for option in question["options"]}
    assert all(f'value="{option_id}"' in question_page.text for option_id in option_ids)
    assert "00:00–00:12" not in question_page.text

    wrong_option = next(option for option in question["options"] if option["id"] != question["correct_option"])
    feedback = client.post(location, data={"option": wrong_option["id"]})
    assert "Respuesta incorrecta" in feedback.text
    assert "Tu respuesta" in feedback.text
    assert "Respuesta correcta" in feedback.text
    assert "Referencia: 00:" in feedback.text
    assert " s–" not in feedback.text

    result = client.get(f"/results/{attempt_id}")
    assert wrong_option["text"] in result.text
    correct_option = next(option for option in question["options"] if option["id"] == question["correct_option"])
    assert correct_option["text"] in result.text
    presentation = get_attempt(attempt_id)["answers"][0]
    assert presentation["chosen_option_text"] == wrong_option["text"]
    assert "options_json" not in presentation

    exam_started = client.post("/tests", data={"mode": "exam", "count": "1"}, follow_redirects=False)
    exam_location = exam_started.headers["location"]
    exam_question = app.state.tests[exam_location.split("/")[2]][0]
    exam_feedback = client.post(exam_location, data={"option": exam_question["options"][0]["id"]})
    assert "Respuesta registrada" in exam_feedback.text
    assert "Respuesta incorrecta" not in exam_feedback.text
    assert "Respuesta correcta" not in exam_feedback.text
    assert "Explicación" not in exam_feedback.text


def test_statistics_distinguish_library_seen_and_remaining_questions():
    create_demo()
    questions = list_questions()
    initial = question_statistics()
    assert initial["total"] == len(questions)
    assert initial["seen"] == 0
    assert initial["remaining"] == len(questions)

    question = questions[0]
    create_attempt("stats-first", [str(question["video_id"])], "random", 1, None)
    record_answer(
        "stats-first",
        str(question["id"]),
        str(question["correct_option"]),
        str(question["correct_option"]),
        None,
        1,
    )
    create_attempt("stats-repeat", [str(question["video_id"])], "random", 1, None)
    record_answer(
        "stats-repeat",
        str(question["id"]),
        str(question["correct_option"]),
        str(question["correct_option"]),
        None,
        1,
    )

    updated = question_statistics()
    assert updated["total"] == len(questions)
    assert updated["seen"] == 1
    assert updated["remaining"] == len(questions) - 1
    assert updated["shown"] == 2

    client = TestClient(create_app())
    statistics_page = client.get("/statistics")
    assert "Preguntas en biblioteca" in statistics_page.text
    assert "Preguntas restantes" in statistics_page.text
    assert "Preguntas vistas" in statistics_page.text


def test_new_mode_reports_exhaustion_and_requires_explicit_repeat():
    empty_client = TestClient(create_app())
    unavailable = empty_client.post("/tests", data={"mode": "new", "count": "1"})
    assert unavailable.status_code == 400
    assert "No hay preguntas disponibles para estos filtros" in unavailable.text
    assert "Repetir preguntas respondidas" not in unavailable.text

    create_demo()
    questions = list_questions()
    create_attempt(
        "exhaust-new",
        sorted({str(question["video_id"]) for question in questions}),
        "new",
        len(questions),
        None,
    )
    for position, question in enumerate(questions, start=1):
        record_answer(
            "exhaust-new",
            str(question["id"]),
            str(question["correct_option"]),
            str(question["correct_option"]),
            None,
            position,
        )

    assert select_questions("new", 1) == []
    assert select_questions("new", 1, repeat_answered=True)

    client = TestClient(create_app())
    exhausted = client.post("/tests", data={"mode": "new", "count": "1"})
    assert exhausted.status_code == 400
    assert "Has agotado las preguntas nuevas" in exhausted.text
    assert "Repetir preguntas respondidas" in exhausted.text

    repeated = client.post(
        "/tests",
        data={"mode": "new", "count": "1", "repeat_answered": "true"},
        follow_redirects=False,
    )
    assert repeated.status_code == 303


def test_mcp_server_builds_and_start_is_optional():
    server = build_server()
    assert server is not None
    tool = server._tool_manager.get_tool("create_generation_job")
    assert inspect.signature(tool.fn).parameters["start"].default == "0s"
    assert "start" not in tool.parameters["required"]
