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


def test_mark_seen_behavior(tmp_path, monkeypatch):
    """Ensure _mark_seen guards against re-parsing the same file."""
    from sshcli import config as config_module

    visited = []

    def fake_read_lines_with_comments(path):
        visited.append(path)
        # No meaningful content; just drive _mark_seen + _parse_include path.
        return []

    monkeypatch.setattr(config_module, "_read_lines_with_comments", fake_read_lines_with_comments)

    temp = tmp_path / "config"
    temp.write_text("Host foo\n    HostName foo\n")

    # _mark_seen is exercised via parse_config_files; we ensure repeated entrypoints
    # do not re-run the parser after the first visit.
    config_module.parse_config_files([temp, temp])

    assert visited.count(temp) == 1


def test_pattern_scoring_helpers(monkeypatch):
    import importlib.util
    import sys

    module_path = Path(__file__).resolve().parents[1] / "sshcli" / "commands" / "common.py"
    spec = importlib.util.spec_from_file_location("sshcli.commands.common_under_test", module_path)
    common_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = common_module
    assert spec.loader is not None
    spec.loader.exec_module(common_module)

    from sshcli.models import HostBlock

    patterns = ["foo", "foo*", "bar?"]
    block = HostBlock(patterns=patterns, source_file=Path("config"), lineno=1)

    score = common_module._best_score_for_block("foo", block, 0)
    assert score is not None
    literal, wildcard_penalty, length, index = score
    assert literal == 1
    assert wildcard_penalty <= 0
    assert length == len("foo")
    assert index == 0

    # Ensure wildcard-only match is still scored, but lower than literal.
    wildcard_score = common_module._score_pattern("foo", "foo*", 0)
    assert wildcard_score is not None
    assert wildcard_score[0] == 0
    assert wildcard_score[1] < 0

    # Non-matching pattern yields None.
    assert common_module._score_pattern("foo", "baz*", 0) is None
