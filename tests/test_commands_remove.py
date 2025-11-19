from pathlib import Path

import typer
from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import remove as remove_module


runner = CliRunner()


def test_remove_host_single_match(monkeypatch, tmp_path, host_block_factory):
    target = tmp_path / "config"
    target.write_text("Host app\n")
    block = host_block_factory(["app"], source=str(target))

    monkeypatch.setattr(remove_module, "_load_blocks_for_target", lambda resolved: [block])

    removed = {}

    def fake_remove(path, selected_block):
        removed["path"] = path
        removed["block"] = selected_block
        return path.parent / "backups" / "backup"

    monkeypatch.setattr(remove_module.config_module, "remove_host_block", fake_remove)

    result = runner.invoke(app, ["remove", "app", "--target", str(target)])
    assert result.exit_code == 0
    assert removed["path"] == Path(str(target)).expanduser()
    assert removed["block"].patterns == ["app"]


def test_remove_host_multiple_selection(monkeypatch, tmp_path, host_block_factory):
    target = tmp_path / "config"
    target.write_text("Host app\n")
    block_one = host_block_factory(["app"], source=str(target))
    block_two = host_block_factory(["app*"], source=str(target))

    monkeypatch.setattr(remove_module, "_load_blocks_for_target", lambda resolved: [block_one, block_two])

    selections = []

    def fake_remove(path, block):
        selections.append(block.patterns[0])

    monkeypatch.setattr(remove_module.config_module, "remove_host_block", fake_remove)
    monkeypatch.setattr(remove_module.typer, "prompt", lambda message: "a")

    result = runner.invoke(app, ["remove", "app", "--target", str(target)])
    assert result.exit_code == 0
    assert set(selections) == {"app", "app*"}


def test_remove_host_invalid_selection(monkeypatch, tmp_path, host_block_factory):
    target = tmp_path / "config"
    target.write_text("Host app\n")
    blocks = [
        host_block_factory(["app"], source=str(target)),
        host_block_factory(["app*"], source=str(target)),
    ]

    monkeypatch.setattr(remove_module, "_load_blocks_for_target", lambda resolved: blocks)
    monkeypatch.setattr(remove_module.typer, "prompt", lambda message: "99")

    result = runner.invoke(app, ["remove", "app", "--target", str(target)])
    assert result.exit_code == 1
    assert "Selection out of range" in result.stdout
