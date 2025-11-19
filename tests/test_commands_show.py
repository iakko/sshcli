from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import show as show_module


runner = CliRunner()


def test_show_host_displays_primary_block(monkeypatch, host_block_factory):
    block = host_block_factory(["app"], options={"HostName": "app.example"})
    monkeypatch.setattr(show_module.config_module, "load_host_blocks", lambda: [block])

    result = runner.invoke(app, ["show", "app"])
    assert result.exit_code == 0
    assert "app.example" in result.stdout
    assert "Host app" in result.stdout


def test_show_host_details_lists_all_matches(monkeypatch, host_block_factory):
    primary = host_block_factory(["api"], options={"HostName": "api.example"})
    wildcard = host_block_factory(["api*"], options={"HostName": "fallback"})
    monkeypatch.setattr(show_module.config_module, "load_host_blocks", lambda: [primary, wildcard])

    result = runner.invoke(app, ["show", "api", "--details"])
    assert result.exit_code == 0
    assert "fallback" in result.stdout
    assert result.stdout.count("Host api") >= 1


def test_show_host_reports_missing(monkeypatch):
    monkeypatch.setattr(show_module.config_module, "load_host_blocks", lambda: [])

    result = runner.invoke(app, ["show", "missing"])
    assert result.exit_code == 1
    assert "No host block matches" in result.stdout
