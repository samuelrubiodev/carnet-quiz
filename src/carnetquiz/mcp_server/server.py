from __future__ import annotations

from ..repositories.questions import question_statistics
from ..services import jobs, transcripts, videos


def build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:
        raise RuntimeError("SDK MCP no instalado. Instalá dependencias del proyecto.") from error
    mcp = FastMCP("CarnetQuiz")

    @mcp.tool()
    def list_videos() -> list[dict[str, object]]: return videos.list_videos()

    @mcp.tool()
    def get_video(video_id: str) -> dict[str, object]: return videos.get_video(video_id)

    @mcp.tool()
    def add_video(url: str) -> dict[str, object]: return videos.add_video(url)

    @mcp.tool()
    def fetch_transcript(video_id: str, language: str | None = None) -> dict[str, int]: return {"segments": transcripts.fetch(video_id, language)}

    @mcp.tool()
    def get_transcript_range(video_id: str, until_seconds: float) -> list[dict[str, object]]: return transcripts.list_segments(video_id, until_seconds)

    @mcp.tool()
    def create_generation_job(video_id: str, until: str) -> dict[str, object]: return jobs.create_job(video_id, until)

    @mcp.tool()
    def list_jobs() -> list[dict[str, object]]: return jobs.list_jobs()

    @mcp.tool()
    def get_job_context(job_id: str) -> str:
        from pathlib import Path
        return (Path(str(jobs.get_job(job_id)["directory"])) / "context.md").read_text(encoding="utf-8")

    @mcp.tool()
    def submit_concepts(job_id: str, concepts: list[dict[str, object]]) -> dict[str, str]: jobs.write_submission(job_id, "concepts.json", concepts); return {"status": "saved"}

    @mcp.tool()
    def submit_questions(job_id: str, questions: list[dict[str, object]]) -> dict[str, str]: jobs.write_submission(job_id, "questions.json", questions); return {"status": "saved"}

    @mcp.tool()
    def submit_review(job_id: str, review: dict[str, object]) -> dict[str, str]: jobs.write_submission(job_id, "review.json", review); return {"status": "saved"}

    @mcp.tool()
    def validate_job(job_id: str) -> dict[str, object]: return jobs.validate_job(job_id)

    @mcp.tool()
    def commit_job(job_id: str) -> dict[str, int]: return jobs.commit_job(job_id)

    @mcp.tool()
    def get_validation_report(job_id: str) -> dict[str, object]:
        import json
        from pathlib import Path
        return json.loads((Path(str(jobs.get_job(job_id)["directory"])) / "validation-report.json").read_text(encoding="utf-8"))

    @mcp.tool()
    def list_questions() -> list[dict[str, object]]: return list_questions()

    @mcp.tool()
    def get_question_statistics() -> dict[str, int]: return question_statistics()
    return mcp


def run() -> None: build_server().run(transport="stdio")
