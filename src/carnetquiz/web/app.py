from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..database import initialize
from ..repositories.questions import (
    create_attempt,
    get_attempt,
    list_questions,
    record_answer,
)
from ..services import data_management, transcripts
from ..services import jobs as job_service
from ..services import videos as video_service
from ..services.selection import select_questions, shuffle_options
from ..services.statistics import dashboard_statistics

ROOT = Path(__file__).parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))

MODE_LABELS = {
    "random": "Aleatorio",
    "balanced": "Equilibrado",
    "new": "Preguntas nuevas",
    "wrong_review": "Repaso de fallos",
    "smart": "Repaso inteligente",
    "exam": "Examen",
}
JOB_STATUS_LABELS = {
    "prepared": "Preparado",
    "partially_valid": "Parcialmente válido",
    "validated": "Validado",
    "committed": "Importado",
    "rejected": "Rechazado",
}
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def format_seconds(value: float | int | None) -> str:
    if value is None:
        return "--:--:--"
    total = max(0, int(float(value)))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_timestamp(value: float | int | None) -> str:
    if value is None:
        return "--:--"
    total = max(0, int(float(value)))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def format_date(value: object) -> str:
    if not value:
        return "Sin fecha"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    return f"{parsed.day} {MONTHS[parsed.month - 1]} {parsed.year}, {parsed:%H:%M}"


def percentage(correct: object, total: object) -> int:
    denominator = int(total or 0)
    return round(int(correct or 0) * 100 / denominator) if denominator else 0


templates.env.filters["duration"] = format_seconds
templates.env.filters["timestamp"] = format_timestamp
templates.env.filters["date_es"] = format_date


def _attempt_view(attempt: dict[str, object]) -> dict[str, object]:
    view = dict(attempt)
    correct = int(view.get("correct_count") or 0)
    total = int(view.get("question_count") or 0)
    score = percentage(correct, total)
    view["percentage"] = score
    view["result_state"] = "Sólido" if score >= 80 else "En progreso" if score >= 50 else "Repaso recomendado"
    view["result_tone"] = "positive" if score >= 80 else "warning" if score >= 50 else "negative"
    return view


def _dashboard_view(video_count: int) -> dict[str, object]:
    stats = dict(dashboard_statistics())
    stats["video_count"] = video_count
    stats["answered"] = int(stats.get("shown") or 0)
    stats["accuracy"] = percentage(stats.get("correct"), stats.get("answered"))
    stats["recent_attempts"] = [_attempt_view(dict(item)) for item in stats.get("recent_attempts", [])]
    topics = []
    for item in stats.get("topics", []):
        topic = dict(item)
        topic["answered"] = int(topic.get("correct") or 0) + int(topic.get("wrong") or 0)
        topic["accuracy"] = percentage(topic.get("correct"), topic["answered"])
        topics.append(topic)
    stats["topics"] = topics
    return stats


def _video_views() -> list[dict[str, object]]:
    available_questions = list_questions()
    question_counts: dict[str, int] = {}
    remaining_question_counts: dict[str, int] = {}
    for question in available_questions:
        video_id = str(question["video_id"])
        question_counts[video_id] = question_counts.get(video_id, 0) + 1
        if not int(question["shown_count"]):
            remaining_question_counts[video_id] = remaining_question_counts.get(video_id, 0) + 1

    result = []
    for source in video_service.list_videos():
        video = dict(source)
        duration = float(video.get("duration_seconds") or 0)
        processed = min(duration, max(0.0, float(video.get("last_processed_seconds") or 0))) if duration else 0
        video["progress_percent"] = round(processed * 100 / duration) if duration else 0
        video_id = str(video["id"])
        video["question_count"] = question_counts.get(video_id, 0)
        video["remaining_question_count"] = remaining_question_counts.get(video_id, 0)
        result.append(video)
    return result


def _job_views() -> list[dict[str, object]]:
    video_titles = {str(video["id"]): str(video["title"]) for video in video_service.list_videos()}
    result = []
    for source in job_service.list_jobs():
        job = dict(source)
        raw_errors = job.get("validation_errors")
        try:
            issues = json.loads(str(raw_errors)) if raw_errors else []
        except (TypeError, json.JSONDecodeError):
            issues = []
        job["validation_issues"] = issues if isinstance(issues, list) else []
        job["validation_error_count"] = len(job["validation_issues"])
        job["status_label"] = JOB_STATUS_LABELS.get(str(job.get("status")), str(job.get("status", "Desconocido")))
        job["video_title"] = video_titles.get(str(job.get("video_id")), "Vídeo no disponible")
        result.append(job)
    return result


def _new_test_context(
    mode: str = "random",
    error: str | None = None,
    selected_video_ids: list[str] | None = None,
    new_questions_exhausted: bool = False,
) -> dict[str, object]:
    selected_mode = mode if mode in MODE_LABELS else "random"
    return {
        "videos": _video_views(),
        "modes": MODE_LABELS,
        "selected_mode": selected_mode,
        "selected_count": 10,
        "selected_video_ids": selected_video_ids,
        "new_questions_exhausted": new_questions_exhausted,
        "error": error,
    }


def create_app() -> FastAPI:
    initialize()
    app = FastAPI(title="CarnetQuiz", docs_url=None)
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

    def page(
        request: Request,
        name: str,
        *,
        status_code: int = 200,
        **context: object,
    ) -> HTMLResponse:
        response = templates.TemplateResponse(request, name, context)
        response.status_code = status_code
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> HTMLResponse:
        detail = str(exc.detail)
        return page(
            request,
            "error.html",
            status_code=exc.status_code,
            error_message=detail,
            error_code=exc.status_code,
        )

    @app.exception_handler(KeyError)
    async def missing_resource(request: Request, exc: KeyError) -> HTMLResponse:
        message = str(exc).strip("'") or "Recurso no encontrado"
        return page(
            request,
            "error.html",
            status_code=404,
            error_message=message,
            error_code=404,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> HTMLResponse:
        return page(
            request,
            "error.html",
            status_code=422,
            error_message="Revisa los datos del formulario e inténtalo de nuevo.",
            error_code=422,
        )

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        videos = _video_views()
        return page(request, "home.html", stats=_dashboard_view(len(videos)), videos=videos)

    @app.get("/videos", response_class=HTMLResponse)
    def video_list(request: Request) -> HTMLResponse:
        return page(request, "videos.html", videos=_video_views())

    @app.post("/videos", response_class=HTMLResponse)
    def add_video(request: Request, url: str = Form(...)) -> Response:
        try:
            video_service.add_video(url)
        except Exception as error:
            return page(request, "videos.html", videos=_video_views(), error=str(error), status_code=400)
        return RedirectResponse("/videos", 303)

    @app.get("/videos/{video_id}/transcript", response_class=HTMLResponse)
    def transcript(
        request: Request,
        video_id: str,
        until: float | None = None,
        search: str | None = None,
    ) -> HTMLResponse:
        return page(
            request,
            "transcript.html",
            video=video_service.get_video(video_id),
            segments=transcripts.list_segments(video_id, until=until, search=search),
            search=search or "",
        )

    @app.get("/jobs", response_class=HTMLResponse)
    def job_list(request: Request, warning: str | None = None) -> HTMLResponse:
        return page(request, "jobs.html", jobs=_job_views(), videos=_video_views(), warning=warning)

    @app.post("/jobs", response_class=HTMLResponse)
    def create_job(
        request: Request,
        video_id: str = Form(...),
        start: str = Form("0s"),
        until: str = Form(...),
    ) -> Response:
        try:
            created = job_service.create_job(video_id, until, start)
        except Exception as error:
            return page(
                request,
                "jobs.html",
                jobs=_job_views(),
                videos=_video_views(),
                error=str(error),
                form_values={"video_id": video_id, "start": start, "until": until},
                status_code=400,
            )
        warnings = created.get("warnings", [])
        location = "/jobs"
        if warnings:
            location += "?warning=" + quote(str(warnings[0]))
        return RedirectResponse(location, 303)

    @app.post("/jobs/{job_id}/validate")
    def validate_job(job_id: str) -> RedirectResponse:
        job_service.validate_job(job_id)
        return RedirectResponse("/jobs", 303)

    @app.post("/jobs/{job_id}/commit")
    def commit_job(job_id: str) -> RedirectResponse:
        job_service.commit_job(job_id)
        return RedirectResponse("/jobs", 303)

    @app.get("/tests/new", response_class=HTMLResponse)
    def new_test(request: Request, mode: str = "random") -> HTMLResponse:
        return page(request, "new_test.html", **_new_test_context(mode))

    @app.post("/tests", response_class=HTMLResponse)
    def start_test(
        request: Request,
        mode: str = Form("random"),
        count: int = Form(10),
        video_ids: list[str] = Form(default=[]),
        start: str | None = Form(None),
        until: str | None = Form(None),
        repeat_answered: bool = Form(False),
    ) -> Response:
        chosen_videos = list(video_ids or [])
        new_questions_exhausted = False
        try:
            questions = select_questions(
                mode,
                count,
                chosen_videos or None,
                start=start or None,
                until=until or None,
                repeat_answered=repeat_answered,
            )
            if not questions:
                if mode == "new" and not repeat_answered:
                    answered_questions = select_questions(
                        mode,
                        1,
                        chosen_videos or None,
                        start=start or None,
                        until=until or None,
                        repeat_answered=True,
                    )
                    if answered_questions:
                        new_questions_exhausted = True
                        raise ValueError(
                            "Has agotado las preguntas nuevas para estos filtros. "
                            "Puedes repetir las que ya has respondido."
                        )
                raise ValueError("No hay preguntas disponibles para estos filtros")
        except Exception as error:
            context = _new_test_context(
                mode,
                str(error),
                selected_video_ids=chosen_videos,
                new_questions_exhausted=new_questions_exhausted,
            )
            context.update({"selected_count": count, "selected_start": start or "", "selected_until": until or ""})
            return page(request, "new_test.html", status_code=400, **context)

        attempt_id = f"attempt-{uuid.uuid4().hex[:12]}"
        create_attempt(attempt_id, chosen_videos, mode, len(questions), None)
        app.state.tests = getattr(app.state, "tests", {})
        app.state.test_modes = getattr(app.state, "test_modes", {})
        app.state.tests[attempt_id] = [shuffle_options(question) for question in questions]
        app.state.test_modes[attempt_id] = mode
        return RedirectResponse(f"/tests/{attempt_id}/1", 303)

    @app.get("/tests/{attempt_id}/{position}", response_class=HTMLResponse)
    def test_question(request: Request, attempt_id: str, position: int) -> Response:
        questions = getattr(app.state, "tests", {}).get(attempt_id)
        if not questions:
            raise HTTPException(404, "Test no encontrado. Crea un test nuevo.")
        if position < 1:
            raise HTTPException(404, "Pregunta no válida")
        if position > len(questions):
            return RedirectResponse(f"/results/{attempt_id}", 303)
        mode = getattr(app.state, "test_modes", {}).get(attempt_id, "random")
        return page(
            request,
            "test.html",
            attempt_id=attempt_id,
            position=position,
            total=len(questions),
            question=questions[position - 1],
            mode=mode,
            mode_label=MODE_LABELS.get(mode, mode),
        )

    @app.post("/tests/{attempt_id}/{position}", response_class=HTMLResponse)
    def answer(
        request: Request,
        attempt_id: str,
        position: int,
        option: str = Form(...),
    ) -> HTMLResponse:
        questions = getattr(app.state, "tests", {}).get(attempt_id)
        if not questions or position < 1 or position > len(questions):
            raise HTTPException(404, "Test no encontrado")
        question = questions[position - 1]
        valid_options = {str(item["id"]) for item in question["options"]}
        if option not in valid_options:
            raise HTTPException(400, "Selecciona una opción válida")
        correct = record_answer(
            attempt_id,
            str(question["id"]),
            option,
            str(question["correct_option"]),
            None,
            position,
        )
        mode = getattr(app.state, "test_modes", {}).get(attempt_id, "random")
        return page(
            request,
            "answer.html",
            attempt_id=attempt_id,
            position=position,
            total=len(questions),
            question=question,
            correct=correct,
            selected=option,
            is_exam=mode == "exam",
            show_explanation=mode != "exam",
            mode_label=MODE_LABELS.get(mode, mode),
        )

    @app.get("/results/{attempt_id}", response_class=HTMLResponse)
    def results(request: Request, attempt_id: str) -> HTMLResponse:
        attempt = _attempt_view(get_attempt(attempt_id))
        attempt["answers"] = list(attempt.get("answers", []))
        return page(request, "results.html", attempt=attempt)

    @app.get("/statistics", response_class=HTMLResponse)
    def statistics(request: Request) -> HTMLResponse:
        return page(request, "statistics.html", stats=_dashboard_view(len(_video_views())))

    @app.get("/admin/data", response_class=HTMLResponse)
    def data_admin(request: Request) -> HTMLResponse:
        return page(request, "data.html", counts=data_management.current_counts())

    @app.post("/admin/data/preview", response_class=HTMLResponse)
    def data_preview(
        request: Request,
        resource: str = Form(...),
        identifier: str = Form(...),
        cascade: bool = Form(False),
    ) -> HTMLResponse:
        try:
            plan = data_management.build_deletion_plan(resource, identifier, cascade)
            error = None
        except Exception as caught:
            plan = None
            error = str(caught)
        return page(
            request,
            "data.html",
            counts=data_management.current_counts(),
            plan=plan,
            error=error,
        )

    @app.post("/admin/data/delete", response_class=HTMLResponse)
    def data_delete(
        request: Request,
        resource: str = Form(...),
        identifier: str = Form(...),
        cascade: bool = Form(False),
        confirm: str = Form(""),
    ) -> HTMLResponse:
        plan = None
        try:
            plan = data_management.build_deletion_plan(resource, identifier, cascade)
            if plan.blocked:
                raise data_management.DeletionBlocked(plan.warnings[-1])
            if confirm != "DELETE":
                return page(
                    request,
                    "data.html",
                    counts=data_management.current_counts(),
                    plan=plan,
                    error="Escribe DELETE para confirmar el borrado selectivo.",
                    status_code=400,
                )
            result = data_management.execute_plan(plan)
            error = None if result["cleanup_complete"] else "Limpieza de archivos incompleta."
        except Exception as caught:
            result = None
            error = str(caught)
        return page(
            request,
            "data.html",
            counts=data_management.current_counts(),
            plan=plan,
            result=result,
            error=error,
        )

    @app.post("/admin/data/preview-reset", response_class=HTMLResponse)
    def data_preview_reset(request: Request) -> HTMLResponse:
        try:
            plan = data_management.build_reset_plan()
            error = None
        except Exception as caught:
            plan = None
            error = str(caught)
        return page(
            request,
            "data.html",
            counts=data_management.current_counts(),
            reset_plan=plan,
            error=error,
        )

    @app.post("/admin/data/reset", response_class=HTMLResponse)
    def data_reset(request: Request, confirm: str = Form("")) -> HTMLResponse:
        plan = None
        try:
            plan = data_management.build_reset_plan()
            if not data_management.reset_confirmation_is_valid(confirm):
                return page(
                    request,
                    "data.html",
                    counts=data_management.current_counts(),
                    reset_plan=plan,
                    error="El reseteo exige escribir exactamente RESET CARNETQUIZ.",
                    status_code=400,
                )
            result = data_management.execute_plan(plan)
            error = None if result["cleanup_complete"] else "Limpieza de archivos incompleta."
        except Exception as caught:
            result = None
            error = str(caught)
        return page(
            request,
            "data.html",
            counts=data_management.current_counts(),
            reset_plan=plan,
            result=result,
            error=error,
        )

    return app
