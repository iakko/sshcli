from __future__ import annotations

from pathlib import Path

from sshcli.config import append_host_block, parse_config_files
from sshcli.commands.common import matching_blocks


def test_parse_config_files_with_include(sample_config):
    config_path: Path = sample_config["config"]

    blocks = parse_config_files([config_path])

    assert len(blocks) == 2
    block_names = {tuple(block.patterns) for block in blocks}
    assert ("foo",) in block_names
    assert ("*.example.com",) in block_names

    foo_block = next(block for block in blocks if block.patterns == ["foo"])
    assert foo_block.options["HostName"] == "foo.example.com"
    assert foo_block.options["User"] == "alice"


def test_matching_blocks_prefers_literal_matches(sample_config):
    config_path: Path = sample_config["config"]
    blocks = parse_config_files([config_path])

    primary, matched = matching_blocks("foo", blocks)

    assert matched, "Expected at least one matching block"
    assert primary, "Expected a primary match"
    assert primary[0].patterns == ["foo"]


def test_append_host_block_creates_backups(tmp_path):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"

    # Prepopulate the config file so the first append produces a backup.
    target.write_text("Host existing\n    HostName existing.example.com\n")

    backup_path = append_host_block(
        target,
        patterns=["new-host"],
        options=[("HostName", "new.example.com"), ("User", "bob")],
    )

    assert backup_path is not None
    assert backup_path.parent == ssh_dir / "backups"
    assert backup_path.exists()

    backup_content = backup_path.read_text()
    assert "Host existing" in backup_content
    assert "HostName existing.example.com" in backup_content

    updated_content = target.read_text()
    assert "Host existing" in updated_content
    assert "Host new-host" in updated_content
    assert "HostName new.example.com" in updated_content
    assert updated_content.endswith("\n")
