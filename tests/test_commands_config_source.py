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


def test_config_source_list_displays_table(monkeypatch, tmp_path):
    file1 = tmp_path / "config"
    file1.write_text("Host app\n")
    file2 = tmp_path / "missing"

    sources = [
        config_source_module.settings_module.ConfigSource(path=str(file1), enabled=True, is_default=True),
        config_source_module.settings_module.ConfigSource(path=str(file2), enabled=False, is_default=False),
    ]
    settings = config_source_module.settings_module.AppSettings(config_sources=sources)
    monkeypatch.setattr(
        config_source_module.settings_module,
        "load_settings",
        lambda: settings,
    )

    result = runner.invoke(app, ["config-source", "list"])
    assert result.exit_code == 0
    assert "Path" in result.stdout
    assert "Enabled" in result.stdout


def test_config_source_enable_success(monkeypatch, tmp_path):
    called = {}

    def fake_enable(path, enabled):
        called["path"] = Path(path)
        called["enabled"] = enabled

    monkeypatch.setattr(
        config_source_module.settings_module,
        "set_source_enabled",
        fake_enable,
    )

    target = tmp_path / "config"
    result = runner.invoke(app, ["config-source", "enable", str(target)])
    assert result.exit_code == 0
    assert called["path"] == target
    assert called["enabled"] is True


def test_config_source_remove_success(monkeypatch, tmp_path):
    removed = {}

    def fake_remove(path):
        removed["path"] = Path(path)

    monkeypatch.setattr(
        config_source_module.settings_module,
        "remove_source",
        fake_remove,
    )

    target = tmp_path / "config"
    result = runner.invoke(app, ["config-source", "remove", str(target)])
    assert result.exit_code == 0
    assert removed["path"] == target


def test_config_source_reset(monkeypatch):
    called = {}

    def fake_reset():
        called["done"] = True

    monkeypatch.setattr(
        config_source_module.settings_module,
        "reset_sources",
        fake_reset,
    )

    result = runner.invoke(app, ["config-source", "reset"])
    assert result.exit_code == 0
    assert called["done"] is True
