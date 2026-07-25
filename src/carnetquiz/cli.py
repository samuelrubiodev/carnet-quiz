from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Annotated

import typer

from .config import get_settings
from .database import backup, initialize, integrity_check
from .repositories.questions import list_questions, question_statistics
from .services import data_management, jobs, transcripts, videos
from .services.demo import create_demo

app = typer.Typer(help="CarnetQuiz: tests locales basados en transcripciones.", no_args_is_help=True)
video_app = typer.Typer(help="Gestionar vídeos.", no_args_is_help=True)
transcript_app = typer.Typer(help="Gestionar transcripciones.", no_args_is_help=True)
job_app = typer.Typer(help="Gestionar trabajos de generación.", no_args_is_help=True)
db_app = typer.Typer(help="Gestionar base de datos.", no_args_is_help=True)
questions_app = typer.Typer(help="Consultar preguntas.", no_args_is_help=True)
data_app = typer.Typer(help="Administrar y borrar datos de estudio.", no_args_is_help=True)
app.add_typer(video_app, name="video"); app.add_typer(transcript_app, name="transcript"); app.add_typer(job_app, name="job"); app.add_typer(db_app, name="db"); app.add_typer(questions_app, name="questions"); app.add_typer(data_app, name="data")


def output(value: object, as_json: bool = False) -> None:
    if as_json: typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str)); return
    if isinstance(value, list):
        for item in value: typer.echo(json.dumps(item, ensure_ascii=False, default=str))
    elif isinstance(value, dict):
        for key, item in value.items(): typer.echo(f"{key}: {item}")
    else: typer.echo(str(value))


def _data_error(error: Exception, as_json: bool, operation: str) -> None:
    if as_json:
        output({"operation": operation, "error": str(error)}, True)
    else:
        typer.echo(f"Error: {error}", err=True)
    raise typer.Exit(code=1)


def _show_deletion_plan(plan: data_management.DeletionPlan) -> None:
    labels = {
        "videos": "vídeos",
        "transcript_segments": "segmentos de transcripción",
        "jobs": "trabajos",
        "concepts": "conceptos",
        "questions": "preguntas",
        "attempts": "intentos",
        "answers": "respuestas",
    }
    typer.echo("Se eliminarán:")
    for key, label in labels.items():
        typer.echo(f"- {plan.counts[key]} {label}")
    typer.echo(f"- {plan.counts['files']} archivos o directorios")
    typer.echo(f"Base de datos: {plan.database_path}")
    typer.echo(f"Directorio de datos: {plan.data_dir}")
    if plan.resource == "video":
        typer.echo("La eliminación del vídeo es en cascada.")
    if plan.resource == "transcript" and plan.affected_counts["jobs"]:
        typer.echo(
            "Dependencias detectadas: "
            f"{plan.affected_counts['jobs']} trabajos, "
            f"{plan.affected_counts['concepts']} conceptos, "
            f"{plan.affected_counts['questions']} preguntas"
        )
    for warning in plan.warnings:
        typer.echo(f"Advertencia: {warning}")


def _show_data_result(result: dict[str, object]) -> None:
    if result["dry_run"]:
        typer.echo("Vista previa: no se modificó SQLite ni el sistema de archivos.")
    elif result["cleanup_complete"]:
        typer.echo("Operación completada. SQLite: integridad correcta.")
    else:
        typer.echo("SQLite actualizado, pero la limpieza de archivos quedó incompleta.")
    if result.get("backup_path"):
        typer.echo(f"Copia de seguridad: {result['backup_path']}")
    for warning in result.get("warnings", []):
        typer.echo(f"Advertencia: {warning}")


def _run_data_plan(
    plan: data_management.DeletionPlan,
    *,
    dry_run: bool,
    yes: bool,
    as_json: bool,
    no_backup: bool,
    reset: bool = False,
    confirm: str | None = None,
) -> None:
    if plan.blocked:
        if as_json:
            output({"operation": "delete", "plan": plan.to_dict(), "error": plan.warnings[-1]}, True)
        else:
            _show_deletion_plan(plan)
            typer.echo("Operación rechazada: faltan dependencias --cascade.", err=True)
        raise typer.Exit(code=1)
    if as_json and not dry_run and not yes:
        _data_error(ValueError("--json exige --yes para operaciones destructivas"), True, plan.operation)
    if not as_json:
        _show_deletion_plan(plan)
    if not dry_run:
        if reset:
            phrase = data_management.confirmation_phrase()
            if yes:
                if confirm != phrase:
                    _data_error(
                        ValueError(f"--yes exige --confirm {phrase!r}"), as_json, "reset"
                    )
            elif data_management.reset_confirmation_is_valid(
                typer.prompt(f"Escribí exactamente {phrase!r}", default="")
            ) is False:
                raise typer.Exit(code=1)
        elif not yes and not typer.confirm("¿Continuar?", default=False):
            raise typer.Exit(code=1)
    try:
        result = data_management.execute_plan(plan, dry_run=dry_run, no_backup=no_backup)
    except Exception as error:
        _data_error(error, as_json, plan.operation)
    if as_json:
        output(result, True)
    else:
        _show_data_result(result)
    if not result["cleanup_complete"]:
        raise typer.Exit(code=1)


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


@data_app.command("reset")
def data_reset(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Mostrar plan sin modificar nada.")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirmación no interactiva.")] = False,
    as_json: Annotated[bool, typer.Option("--json")] = False,
    no_backup: Annotated[bool, typer.Option("--no-backup", help="Omitir copia; operación irreversible.")] = False,
    cascade: Annotated[bool, typer.Option("--cascade", help="No aplicable al reseteo.")] = False,
    confirm: Annotated[str | None, typer.Option("--confirm", help="Frase exacta para --yes.")] = None,
) -> None:
    if cascade:
        _data_error(ValueError("--cascade no es válido para data reset"), as_json, "reset")
    try:
        plan = data_management.build_reset_plan()
    except Exception as error:
        _data_error(error, as_json, "reset")
    _run_data_plan(
        plan,
        dry_run=dry_run,
        yes=yes,
        as_json=as_json,
        no_backup=no_backup,
        reset=True,
        confirm=confirm,
    )


@data_app.command("delete")
def data_delete(
    resource: str,
    identifier: str,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Mostrar plan sin modificar nada.")] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirmación no interactiva.")] = False,
    as_json: Annotated[bool, typer.Option("--json")] = False,
    no_backup: Annotated[bool, typer.Option("--no-backup", help="Omitir copia; operación irreversible.")] = False,
    cascade: Annotated[bool, typer.Option("--cascade", help="Borrar dependencias de una transcripción.")] = False,
) -> None:
    try:
        plan = data_management.build_deletion_plan(resource, identifier, cascade)
    except Exception as error:
        _data_error(error, as_json, "delete")
    _run_data_plan(
        plan,
        dry_run=dry_run,
        yes=yes,
        as_json=as_json,
        no_backup=no_backup,
    )


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
