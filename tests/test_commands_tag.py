from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import tag as tag_module


runner = CliRunner()


def test_tag_add_requires_defined_tags(monkeypatch, host_block_factory):
    block = host_block_factory(["app"])
    monkeypatch.setattr(tag_module.config_module, "load_host_blocks", lambda: [block])
    monkeypatch.setattr(tag_module.settings_module, "get_tag_definitions", lambda: {})

    result = runner.invoke(app, ["tag", "add", "app", "prod"])
    assert result.exit_code == 1
    assert "not defined" in result.stdout


def test_tag_add_updates_block_and_persists(monkeypatch, host_block_factory):
    block = host_block_factory(["app"], tags=["existing"])
    saved = {}

    def fake_replace(target, updated_block, patterns, options):
        saved["target"] = target
        saved["block"] = updated_block

    monkeypatch.setattr(tag_module.config_module, "load_host_blocks", lambda: [block])
    monkeypatch.setattr(tag_module.config_module, "replace_host_block_with_metadata", fake_replace)
    monkeypatch.setattr(
        tag_module.settings_module,
        "get_tag_definitions",
        lambda: {"prod": "red", "existing": "blue"},
    )

    result = runner.invoke(app, ["tag", "add", "app", "prod"])
    assert result.exit_code == 0
    assert "Added tags" in result.stdout
    assert saved["target"] == block.source_file
    assert "prod" in saved["block"].tags
    assert "existing" in saved["block"].tags


def test_tag_remove_updates_metadata(monkeypatch, host_block_factory):
    block = host_block_factory(["app"], tags=["Prod", "Blue"])
    saved = {}

    def fake_replace(target, updated_block, patterns, options):
        saved["tags"] = list(updated_block.tags)

    monkeypatch.setattr(tag_module.config_module, "load_host_blocks", lambda: [block])
    monkeypatch.setattr(tag_module.config_module, "replace_host_block_with_metadata", fake_replace)

    result = runner.invoke(app, ["tag", "remove", "app", "prod"])
    assert result.exit_code == 0
    assert saved["tags"] == ["Blue"]


def test_tag_color_updates_definitions(monkeypatch):
    definitions = {"prod": "red"}
    monkeypatch.setattr(tag_module.settings_module, "get_tag_definitions", lambda: dict(definitions))
    recorded = {}

    def fake_update(updated):
        recorded["payload"] = updated

    monkeypatch.setattr(tag_module.settings_module, "update_tag_definitions", fake_update)

    result = runner.invoke(app, ["tag", "color", "staging", "#00ff00"])
    assert result.exit_code == 0
    assert recorded["payload"]["prod"] == "red"
    assert recorded["payload"]["staging"] == "#00ff00"
