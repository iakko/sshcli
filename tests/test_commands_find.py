from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import find as find_module


runner = CliRunner()


def test_find_hosts_filters_by_tag(monkeypatch, host_block_factory):
    prod = host_block_factory(["app-prod"], options={"HostName": "prod.example"}, tags=["prod"])
    staging = host_block_factory(["app-staging"], options={"HostName": "staging.example"}, tags=["staging"])

    monkeypatch.setattr(find_module.config_module, "load_host_blocks", lambda: [prod, staging])

    result = runner.invoke(app, ["find", "app*", "--tag", "prod"])
    assert result.exit_code == 0
    assert "prod.example" in result.stdout
    assert "staging.example" not in result.stdout


def test_find_hosts_reports_missing(monkeypatch, host_block_factory):
    block = host_block_factory(["db"], options={"HostName": "db.example"})
    monkeypatch.setattr(find_module.config_module, "load_host_blocks", lambda: [block])

    result = runner.invoke(app, ["find", "web*"])
    assert result.exit_code == 0
    assert "No results" in result.stdout
