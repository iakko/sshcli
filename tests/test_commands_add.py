import pytest
import typer
from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import add as add_module


runner = CliRunner()


def test_build_options_accepts_core_fields():
    options = add_module._build_options(
        hostname="example.com",
        user="ubuntu",
        port=2200,
        option_entries=["IdentityFile=~/.ssh/id_rsa"],
    )
    assert ("HostName", "example.com") in options
    assert ("User", "ubuntu") in options
    assert ("Port", "2200") in options
    assert ("IdentityFile", "~/.ssh/id_rsa") in options


def test_build_options_validates_custom_entries():
    with pytest.raises(typer.Exit):
        add_module._build_options(
            hostname="example.com",
            user="",
            port=0,
            option_entries=["invalid-entry"],
        )


def test_guard_duplicates_detects_existing_blocks(host_block_factory):
    existing = host_block_factory(["app"], lineno=5)
    with pytest.raises(typer.Exit):
        add_module._guard_duplicates(["app"], [existing], force=False)

    # Should pass when force flag is used
    add_module._guard_duplicates(["app"], [existing], force=True)


def test_load_existing_blocks_handles_missing_file(tmp_path):
    target = tmp_path / "config"
    blocks = add_module._load_existing_blocks(target)
    assert blocks == []


def test_add_command_appends_new_block(monkeypatch, tmp_path):
    target = tmp_path / "config"
    target.write_text("Host existing\n")

    monkeypatch.setattr(add_module.config_module, "default_config_path", lambda: target)
    monkeypatch.setattr(add_module, "_load_existing_blocks", lambda resolved: [])

    recorded = {}

    def fake_append(path, patterns, options):
        recorded["path"] = path
        recorded["patterns"] = patterns
        recorded["options"] = options
        return path.parent / "backups" / "config.backup"

    monkeypatch.setattr(add_module.config_module, "append_host_block", fake_append)

    result = runner.invoke(app, ["add", "web", "--hostname", "web.example"])
    assert result.exit_code == 0
    assert recorded["path"] == target.expanduser()
    assert recorded["patterns"] == ["web"]
    assert ("HostName", "web.example") in recorded["options"]
