from __future__ import annotations

import inspect

from fastapi.testclient import TestClient

from carnetquiz.mcp_server.server import build_server
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


def test_mcp_server_builds_and_start_is_optional():
    server = build_server()
    assert server is not None
    tool = server._tool_manager.get_tool("create_generation_job")
    assert inspect.signature(tool.fn).parameters["start"].default == "0s"
    assert "start" not in tool.parameters["required"]
