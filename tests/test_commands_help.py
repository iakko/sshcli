from typer.testing import CliRunner

from sshcli.cli import app


runner = CliRunner()


def test_help_command_lists_registered_commands():
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0
    assert "add" in result.stdout
    assert "copy" in result.stdout
    assert "remove" in result.stdout
