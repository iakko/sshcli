from rich.console import Console
from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import list as list_module


runner = CliRunner()


def test_list_hosts_displays_patterns_and_files(monkeypatch, host_block_factory):
    record_console = Console(record=True, force_terminal=False, width=120)
    monkeypatch.setattr(list_module, "console", record_console)

    blocks = [
        host_block_factory(
            ["prod-db-1"],
            source="/tmp/config",
            lineno=8,
            options={"HostName": "db1.example.com", "User": "postgres"},
            tags=["prod", "db"],
        ),
        host_block_factory(
            ["staging-*"],
            source="/tmp/config",
            lineno=20,
            options={"HostName": "staging.example.com"},
        ),
    ]
    monkeypatch.setattr(list_module.config_module, "load_host_blocks", lambda: blocks)

    result = runner.invoke(app, ["list", "--patterns", "--files"])
    assert result.exit_code == 0
    output = record_console.export_text()
    assert "prod-db-1" in output
    assert "db1.example.com" in output
    assert "/tmp/config :8" in output
    assert "staging-*" in output


def test_list_hosts_filters_by_tag(monkeypatch, host_block_factory):
    record_console = Console(record=True, force_terminal=False, width=120)
    monkeypatch.setattr(list_module, "console", record_console)

    prod = host_block_factory(
        ["prod-db-1"],
        options={"HostName": "db1"},
        tags=["prod"],
    )
    staging = host_block_factory(
        ["staging-1"],
        options={"HostName": "staging"},
        tags=["staging"],
    )
    monkeypatch.setattr(list_module.config_module, "load_host_blocks", lambda: [prod, staging])

    result = runner.invoke(app, ["list", "--tag", "prod"])
    assert result.exit_code == 0
    output = record_console.export_text()
    assert "db1" in output
    assert "staging" not in output


def test_list_hosts_handles_empty(monkeypatch):
    record_console = Console(record=True, force_terminal=False, width=120)
    monkeypatch.setattr(list_module, "console", record_console)
    monkeypatch.setattr(list_module.config_module, "load_host_blocks", lambda: [])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "No SSH host blocks found" in record_console.export_text()
