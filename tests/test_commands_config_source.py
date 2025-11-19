from pathlib import Path

from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import config_source as config_source_module


runner = CliRunner()


def test_config_source_add_invokes_settings(monkeypatch, tmp_path):
    calls = {}

    def fake_add_or_update_source(path, enabled, make_default):
        calls["path"] = Path(path)
        calls["enabled"] = enabled
        calls["default"] = make_default
        return config_source_module.settings_module.AppSettings(config_sources=[])

    monkeypatch.setattr(
        config_source_module.settings_module,
        "add_or_update_source",
        fake_add_or_update_source,
    )

    target = tmp_path / "custom.conf"
    result = runner.invoke(
        app,
        ["config-source", "add", str(target), "--default", "--disable"],
    )
    assert result.exit_code == 0
    assert calls["path"] == target
    assert calls["enabled"] is False
    assert calls["default"] is True


def test_config_source_disable_reports_errors(monkeypatch):
    def fake_set_source_enabled(path, enabled):
        raise ValueError("No config source registered")

    monkeypatch.setattr(
        config_source_module.settings_module,
        "set_source_enabled",
        fake_set_source_enabled,
    )

    result = runner.invoke(app, ["config-source", "disable", "/tmp/missing"])
    assert result.exit_code == 1
    assert "No config source registered" in result.stdout


def test_config_source_default_sets_target(monkeypatch, tmp_path):
    seen = {}

    def fake_set_default(path):
        seen["path"] = Path(path)

    monkeypatch.setattr(
        config_source_module.settings_module,
        "set_default_source",
        fake_set_default,
    )

    target = tmp_path / "config"
    result = runner.invoke(app, ["config-source", "default", str(target)])
    assert result.exit_code == 0
    assert seen["path"] == target
