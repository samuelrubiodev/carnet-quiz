from typer.testing import CliRunner

from carnetquiz.cli import app
from carnetquiz.schemas import SegmentInput
from carnetquiz.services.transcripts import import_segments
from carnetquiz.services.videos import add_demo_video


def test_cli_help_and_init():
    runner = CliRunner()
    assert runner.invoke(app, ["--help"]).exit_code == 0
    assert runner.invoke(app, ["init"]).exit_code == 0


def test_cli_creates_explicit_interval_and_exposes_from_option():
    add_demo_video("cli-video-01", "CLI", 3600)
    import_segments(
        "cli-video-01",
        [SegmentInput(start_seconds=1800, end_seconds=1810, text="Segmento disponible desde treinta minutos.")],
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["job", "create", "cli-video-01", "--from", "30m", "--until", "60m"],
    )
    assert result.exit_code == 0
    assert "start_seconds: 1800.0" in result.stdout
    assert "end_seconds: 3600.0" in result.stdout
    help_result = runner.invoke(app, ["job", "create", "--help"])
    assert "--from" in help_result.stdout
