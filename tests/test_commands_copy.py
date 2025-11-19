from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import copy as copy_module


runner = CliRunner()


def test_copy_host_appends_new_block(monkeypatch, tmp_path, host_block_factory):
    target = tmp_path / "config"
    target.write_text("Host web\n")
    source_block = host_block_factory(["web"], source=str(target), options={"HostName": "web.example"})

    monkeypatch.setattr(copy_module.config_module, "default_config_path", lambda: target)
    monkeypatch.setattr(copy_module.config_module, "parse_config_files", lambda paths: [source_block])

    captured = {}

    def fake_append(path, patterns, options):
        captured["path"] = path
        captured["patterns"] = patterns
        captured["options"] = options
        return path.parent / "backups" / "config.backup.20240101000000"

    monkeypatch.setattr(copy_module.config_module, "append_host_block", fake_append)

    result = runner.invoke(app, ["copy", "web", "--name", "web-copy"])

    assert result.exit_code == 0
    assert captured["path"] == target
    assert captured["patterns"] == ["web-copy"]
    assert ("HostName", "web.example") in captured["options"]


def test_copy_host_detects_duplicates(monkeypatch, tmp_path, host_block_factory):
    target = tmp_path / "config"
    target.write_text("Host web\n")
    source_block = host_block_factory(["web"], source=str(target))
    duplicate = host_block_factory(["web-copy"], source=str(target))

    monkeypatch.setattr(copy_module.config_module, "default_config_path", lambda: target)
    monkeypatch.setattr(
        copy_module.config_module,
        "parse_config_files",
        lambda paths: [source_block, duplicate],
    )

    result = runner.invoke(app, ["copy", "web", "--name", "web-copy"])
    assert result.exit_code == 1
    assert "already exists" in result.stdout
