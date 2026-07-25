from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from carnetquiz.cli import app
from carnetquiz.database import connect
from carnetquiz.repositories.questions import create_attempt, record_answer
from carnetquiz.services import data_management
from carnetquiz.services.data_management import (
    DeletionBlocked,
    PathSafetyError,
    build_deletion_plan,
    build_reset_plan,
    current_counts,
    execute_plan,
)
from carnetquiz.services.demo import create_demo


def test_reset_empty_preserves_schema_and_is_repeatable():
    first = execute_plan(build_reset_plan())
    assert first["cleanup_complete"]
    with connect() as db:
        assert db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()[0] == "1"
    assert current_counts() == {
        "videos": 0,
        "transcript_segments": 0,
        "jobs": 0,
        "concepts": 0,
        "questions": 0,
        "attempts": 0,
        "answers": 0,
    }
    second = execute_plan(build_reset_plan(), no_backup=True)
    assert second["cleanup_complete"]


def test_reset_backs_up_and_removes_jobs_and_transcripts(tmp_path):
    create_demo()
    settings_data = tmp_path / "data"
    job_directory = next(settings_data.joinpath("jobs").iterdir())
    transcript = settings_data / "transcripts" / "demo-signals-001.json"
    result = execute_plan(build_reset_plan())
    assert result["backup_path"]
    assert not job_directory.exists()
    assert not transcript.exists()
    backup_root = result["backup_path"]
    manifest = json.loads((Path(backup_root) / "manifest.json").read_text())
    assert manifest["paths"]
    assert (settings_data / "carnetquiz.db").exists()
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 0
        assert db.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()[0] == "1"


def test_reset_dry_run_and_confirmation_do_not_modify():
    create_demo()
    runner = CliRunner()
    before = current_counts()
    dry = runner.invoke(app, ["data", "reset", "--dry-run"])
    assert dry.exit_code == 0
    assert "no se modificó" in dry.stdout.lower()
    assert current_counts() == before
    rejected = runner.invoke(app, ["data", "reset", "--yes", "--confirm", "NO"])
    assert rejected.exit_code != 0
    assert current_counts() == before


def test_video_delete_removes_cross_video_attempt_and_keeps_other_video():
    create_demo()
    from carnetquiz.services.videos import add_demo_video

    add_demo_video("other-video-01", "Otro vídeo")
    create_attempt("mixed", ["demo-signals-001", "other-video-01"], "random", 2, None)
    record_answer("mixed", "red-light-001-q01", "c", "c", None, 1)
    result = execute_plan(build_deletion_plan("video", "demo-signals-001"), no_backup=True)
    assert result["deleted"]["attempts"] == 1
    counts = current_counts()
    assert counts["videos"] == 1
    assert counts["attempts"] == 0


def test_transcript_requires_cascade_and_preserves_video_with_cascade():
    create_demo()
    blocked = build_deletion_plan("transcript", "demo-signals-001")
    assert blocked.blocked
    with pytest.raises(DeletionBlocked):
        execute_plan(blocked, no_backup=True)
    result = execute_plan(
        build_deletion_plan("transcript", "demo-signals-001", cascade=True), no_backup=True
    )
    assert result["deleted"]["jobs"] == 1
    assert current_counts()["videos"] == 1
    with connect() as db:
        video = db.execute(
            "SELECT status, transcript_path, last_processed_seconds FROM videos WHERE id=?",
            ("demo-signals-001",),
        ).fetchone()
    assert tuple(video) == ("added", None, 0.0)


def test_question_delete_removes_attempt_and_preserves_parent_data():
    create_demo()
    create_attempt("attempt-q", ["demo-signals-001"], "random", 1, None)
    record_answer("attempt-q", "priority-signals-001-q01", "b", "b", None, 1)
    result = execute_plan(
        build_deletion_plan("question", "priority-signals-001-q01"), no_backup=True
    )
    assert result["deleted"]["questions"] == 1
    assert current_counts() == {
        "videos": 1,
        "transcript_segments": 3,
        "jobs": 1,
        "concepts": 2,
        "questions": 1,
        "attempts": 0,
        "answers": 0,
    }


def test_attempt_delete_recalculates_question_statistics():
    create_demo()
    create_attempt("attempt-stat", ["demo-signals-001"], "random", 1, None)
    record_answer("attempt-stat", "red-light-001-q01", "c", "c", None, 1)
    with connect() as db:
        before = db.execute(
            "SELECT shown_count, correct_count, wrong_count FROM questions WHERE id=?",
            ("red-light-001-q01",),
        ).fetchone()
    assert tuple(before) == (1, 1, 0)
    execute_plan(build_deletion_plan("attempt", "attempt-stat"), no_backup=True)
    with connect() as db:
        after = db.execute(
            "SELECT shown_count, correct_count, wrong_count, last_shown_at FROM questions WHERE id=?",
            ("red-light-001-q01",),
        ).fetchone()
    assert tuple(after) == (0, 0, 0, None)


def test_invalid_resource_identifier_and_unsafe_registered_path(monkeypatch):
    create_demo()
    runner = CliRunner()
    invalid = runner.invoke(app, ["data", "delete", "unknown", "x"])
    assert invalid.exit_code != 0
    missing = runner.invoke(app, ["data", "delete", "question", "missing-q", "--yes"])
    assert missing.exit_code != 0
    with connect() as db:
        job_id = db.execute("SELECT id FROM jobs LIMIT 1").fetchone()[0]
        db.execute("UPDATE jobs SET directory=?", ("/tmp/../outside-job",))
    with pytest.raises(PathSafetyError):
        build_deletion_plan("job", str(job_id))


def test_transaction_failure_rolls_back(monkeypatch):
    create_demo()
    before = current_counts()

    def fail(_connection):
        raise RuntimeError("integrity test failure")

    monkeypatch.setattr(data_management, "_check_integrity", fail)
    with pytest.raises(RuntimeError, match="integrity test failure"):
        execute_plan(build_deletion_plan("question", "red-light-001-q01"), no_backup=True)
    assert current_counts() == before


def test_file_cleanup_failure_is_reported(monkeypatch):
    create_demo()
    plan = build_deletion_plan("video", "demo-signals-001")

    def fail_unlink(_path):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    result = execute_plan(plan, no_backup=True)
    assert not result["cleanup_complete"]
    assert any("permission denied" in warning for warning in result["warnings"])
    assert current_counts()["videos"] == 0


def test_symlink_outside_is_rejected():
    create_demo()
    with connect() as db:
        job_id = db.execute("SELECT id FROM jobs LIMIT 1").fetchone()[0]
        jobs_dir = Path(os.environ["CARNETQUIZ_DATA_DIR"]) / "jobs"
        outside = Path(os.environ["CARNETQUIZ_DATA_DIR"]).parent / "outside"
        outside.mkdir()
        link = jobs_dir / "unsafe-link"
        link.symlink_to(outside, target_is_directory=True)
        db.execute("UPDATE jobs SET directory=? WHERE id=?", (str(link), job_id))
    with pytest.raises(PathSafetyError, match="Enlace simbólico"):
        build_deletion_plan("job", str(job_id))


def test_json_output_is_structured_and_no_backup_warns():
    create_demo()
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["data", "delete", "question", "red-light-001-q01", "--yes", "--json", "--no-backup"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["integrity_check"] == "ok"
    assert any("no-backup" in warning for warning in payload["warnings"])
