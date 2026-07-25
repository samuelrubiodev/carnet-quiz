from typer.testing import CliRunner

from carnetquiz.cli import app


def test_cli_help_and_init():
    runner = CliRunner()
    assert runner.invoke(app, ["--help"]).exit_code == 0
    assert runner.invoke(app, ["init"]).exit_code == 0
