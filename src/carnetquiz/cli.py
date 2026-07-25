from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Annotated

import typer

from .config import get_settings
from .database import backup, initialize, integrity_check
from .repositories.questions import list_questions, question_statistics
from .services import jobs, transcripts, videos
from .services.demo import create_demo

app = typer.Typer(help="CarnetQuiz: tests locales basados en transcripciones.", no_args_is_help=True)
video_app = typer.Typer(help="Gestionar vídeos.", no_args_is_help=True)
transcript_app = typer.Typer(help="Gestionar transcripciones.", no_args_is_help=True)
job_app = typer.Typer(help="Gestionar trabajos de generación.", no_args_is_help=True)
db_app = typer.Typer(help="Gestionar base de datos.", no_args_is_help=True)
questions_app = typer.Typer(help="Consultar preguntas.", no_args_is_help=True)
app.add_typer(video_app, name="video"); app.add_typer(transcript_app, name="transcript"); app.add_typer(job_app, name="job"); app.add_typer(db_app, name="db"); app.add_typer(questions_app, name="questions")


def output(value: object, as_json: bool = False) -> None:
    if as_json: typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str)); return
    if isinstance(value, list):
        for item in value: typer.echo(json.dumps(item, ensure_ascii=False, default=str))
    elif isinstance(value, dict):
        for key, item in value.items(): typer.echo(f"{key}: {item}")
    else: typer.echo(str(value))


@app.command()
def init() -> None:
    """Inicializar directorios y SQLite."""
    typer.echo(f"Base de datos inicializada: {initialize()}")


@app.command()
def doctor(as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    """Comprobar dependencias locales."""
    result = {"database": str(initialize()), "yt_dlp": bool(shutil.which("yt-dlp")), "python": __import__("sys").version.split()[0]}
    output(result, as_json)


@video_app.command("add")
def video_add(url: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    output(videos.add_video(url), as_json)


@video_app.command("list")
def video_list(as_json: Annotated[bool, typer.Option("--json")] = False) -> None: output(videos.list_videos(), as_json)


@video_app.command("show")
def video_show(video_id: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None: output(videos.get_video(video_id), as_json)


@transcript_app.command("list")
def transcript_list(video_id: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None: output(transcripts.list_segments(video_id), as_json)


@transcript_app.command("fetch")
def transcript_fetch(video_id: str, language: Annotated[str | None, typer.Option()] = None) -> None: typer.echo(f"Segmentos importados: {transcripts.fetch(video_id, language)}")


@transcript_app.command("import")
def transcript_import(video_id: str, file: Path, language: Annotated[str, typer.Option()] = "es") -> None: typer.echo(f"Segmentos importados: {transcripts.import_file(video_id, file, language)}")


@transcript_app.command("show")
def transcript_show(video_id: str, until: Annotated[str | None, typer.Option()] = None, search: Annotated[str | None, typer.Option()] = None, as_json: Annotated[bool, typer.Option("--json")] = False) -> None:
    output(transcripts.list_segments(video_id, jobs.parse_duration(until) if until else None, search), as_json)


@job_app.command("create")
def job_create(video_id: str, until: Annotated[str, typer.Option()]) -> None: output(jobs.create_job(video_id, until))


@job_app.command("list")
def job_list(as_json: Annotated[bool, typer.Option("--json")] = False) -> None: output(jobs.list_jobs(), as_json)


@job_app.command("show")
def job_show(job_id: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None: output(jobs.get_job(job_id), as_json)


@job_app.command("validate")
def job_validate(job_id: str, as_json: Annotated[bool, typer.Option("--json")] = False) -> None: output(jobs.validate_job(job_id), as_json)


@job_app.command("commit")
def job_commit(job_id: str, yes: Annotated[bool, typer.Option("--yes", help="Confirmar importación.")] = False) -> None:
    if not yes and not typer.confirm("¿Importar preguntas válidas en SQLite?"): raise typer.Abort()
    output(jobs.commit_job(job_id))


@job_app.command("reject")
def job_reject(job_id: str, yes: Annotated[bool, typer.Option("--yes")] = False) -> None:
    if not yes and not typer.confirm("¿Rechazar trabajo?"): raise typer.Abort()
    jobs.reject_job(job_id); typer.echo("Trabajo rechazado")


@questions_app.command("list")
def questions_list(as_json: Annotated[bool, typer.Option("--json")] = False) -> None: output(list_questions(), as_json)


@questions_app.command("stats")
def questions_stats(as_json: Annotated[bool, typer.Option("--json")] = False) -> None: output(question_statistics(), as_json)


@db_app.command("check")
def db_check() -> None:
    result = integrity_check()
    if result != ["ok"]: raise typer.Exit(code=1)
    typer.echo("SQLite integrity_check: ok")


@db_app.command("backup")
def db_backup() -> None: typer.echo(f"Copia creada: {backup()}")


@app.command()
def demo() -> None: output(create_demo())


@app.command()
def serve(host: Annotated[str | None, typer.Option()] = None, port: Annotated[int | None, typer.Option()] = None) -> None:
    import uvicorn
    settings = get_settings(); uvicorn.run("carnetquiz.web.app:create_app", host=host or settings.web_host, port=port or settings.web_port, factory=True)


@app.command()
def mcp() -> None:
    from .mcp_server.server import run
    run()


if __name__ == "__main__": app()
