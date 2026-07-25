from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..database import initialize
from ..repositories.questions import create_attempt, get_attempt, record_answer
from ..services import jobs, transcripts, videos
from ..services.selection import select_questions, shuffle_options
from ..services.statistics import dashboard_statistics

ROOT = Path(__file__).parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))


def create_app() -> FastAPI:
    initialize(); app = FastAPI(title="CarnetQuiz", docs_url=None)
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

    def page(request: Request, name: str, **context: object) -> HTMLResponse:
        return templates.TemplateResponse(request, name, context)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse: return page(request, "home.html", stats=dashboard_statistics(), videos=videos.list_videos())

    @app.get("/videos", response_class=HTMLResponse)
    def video_list(request: Request) -> HTMLResponse: return page(request, "videos.html", videos=videos.list_videos())

    @app.post("/videos")
    def add_video(url: str = Form(...)) -> RedirectResponse:
        try: videos.add_video(url)
        except Exception as error: raise HTTPException(400, str(error)) from error
        return RedirectResponse("/videos", 303)

    @app.get("/videos/{video_id}/transcript", response_class=HTMLResponse)
    def transcript(request: Request, video_id: str, until: float | None = None, search: str | None = None) -> HTMLResponse:
        return page(request, "transcript.html", video=videos.get_video(video_id), segments=transcripts.list_segments(video_id, until, search))

    @app.get("/jobs", response_class=HTMLResponse)
    def job_list(request: Request) -> HTMLResponse:
        return page(request, "jobs.html", jobs=jobs.list_jobs(), videos=videos.list_videos())

    @app.post("/jobs")
    def create_job(video_id: str = Form(...), until: str = Form(...)) -> RedirectResponse:
        try: jobs.create_job(video_id, until)
        except Exception as error: raise HTTPException(400, str(error)) from error
        return RedirectResponse("/jobs", 303)

    @app.post("/jobs/{job_id}/validate")
    def validate_job(job_id: str) -> RedirectResponse: jobs.validate_job(job_id); return RedirectResponse("/jobs", 303)

    @app.post("/jobs/{job_id}/commit")
    def commit_job(job_id: str) -> RedirectResponse: jobs.commit_job(job_id); return RedirectResponse("/jobs", 303)

    @app.get("/tests/new", response_class=HTMLResponse)
    def new_test(request: Request) -> HTMLResponse: return page(request, "new_test.html", videos=videos.list_videos())

    @app.post("/tests")
    def start_test(mode: str = Form("random"), count: int = Form(10), video_ids: list[str] = Form(default=[])) -> RedirectResponse:
        questions = select_questions(mode, count, video_ids or None)
        if not questions: raise HTTPException(400, "No hay preguntas disponibles")
        attempt_id = f"attempt-{uuid.uuid4().hex[:12]}"; create_attempt(attempt_id, video_ids, mode, len(questions), None)
        app.state.tests = getattr(app.state, "tests", {})
        app.state.test_modes = getattr(app.state, "test_modes", {})
        app.state.tests[attempt_id] = [shuffle_options(question) for question in questions]
        app.state.test_modes[attempt_id] = mode
        return RedirectResponse(f"/tests/{attempt_id}/1", 303)

    @app.get("/tests/{attempt_id}/{position}", response_class=HTMLResponse)
    def test_question(request: Request, attempt_id: str, position: int) -> HTMLResponse:
        questions = getattr(app.state, "tests", {}).get(attempt_id)
        if not questions: raise HTTPException(404, "Test no encontrado; reiniciá test")
        if position > len(questions): return RedirectResponse(f"/results/{attempt_id}", 303)
        return page(request, "test.html", attempt_id=attempt_id, position=position, total=len(questions), question=questions[position - 1])

    @app.post("/tests/{attempt_id}/{position}", response_class=HTMLResponse)
    def answer(request: Request, attempt_id: str, position: int, option: str = Form(...)) -> HTMLResponse:
        questions = getattr(app.state, "tests", {}).get(attempt_id)
        if not questions or position > len(questions): raise HTTPException(404, "Test no encontrado")
        question = questions[position - 1]
        correct = record_answer(
            attempt_id, str(question["id"]), option, str(question["correct_option"]), None, position
        )
        return page(
            request,
            "answer.html",
            attempt_id=attempt_id,
            position=position,
            total=len(questions),
            question=question,
            correct=correct,
            selected=option,
            show_explanation=getattr(app.state, "test_modes", {}).get(attempt_id) != "exam",
        )

    @app.get("/results/{attempt_id}", response_class=HTMLResponse)
    def results(request: Request, attempt_id: str) -> HTMLResponse: return page(request, "results.html", attempt=get_attempt(attempt_id))

    @app.get("/statistics", response_class=HTMLResponse)
    def statistics(request: Request) -> HTMLResponse: return page(request, "statistics.html", stats=dashboard_statistics())
    return app
