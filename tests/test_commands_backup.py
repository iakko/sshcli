from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import backup as backup_module
from sshcore import backups as backups_core


runner = CliRunner()


def _make_entry(base_dir: Path, stamp: str, *, seconds_ago: int, size: int = 1024) -> backups_core.BackupEntry:
    backup_path = base_dir / f"config.backup.{stamp}"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text("data")
    timestamp = datetime.now(tz=timezone.utc) - timedelta(seconds=seconds_ago)
    return backups_core.BackupEntry(path=backup_path, stamp=stamp, timestamp=timestamp, size=size)


def test_backup_list_displays_entries(monkeypatch, tmp_path):
    target = tmp_path / "config"
    target.write_text("")
    entries = [
        _make_entry(tmp_path, "20240101010101", seconds_ago=60, size=2048),
        _make_entry(tmp_path, "20231224083000", seconds_ago=3600, size=512),
    ]

    monkeypatch.setattr(backup_module, "_resolve_target", lambda t=None: target)
    monkeypatch.setattr(backup_module.backups_core, "discover_backups", lambda resolved: entries)

    result = runner.invoke(app, ["backup", "list"])
    assert result.exit_code == 0
    for entry in entries:
        assert entry.stamp in result.stdout


def test_backup_prune_dry_run_lists_candidates(monkeypatch, tmp_path):
    target = tmp_path / "config"
    target.write_text("")
    entries = [
        _make_entry(tmp_path, "20240101010101", seconds_ago=60),
        _make_entry(tmp_path, "20231224083000", seconds_ago=3600),
    ]

    monkeypatch.setattr(backup_module, "_resolve_target", lambda t=None: target)
    monkeypatch.setattr(backup_module.backups_core, "discover_backups", lambda resolved: entries)

    result = runner.invoke(app, ["backup", "prune", "--keep", "0", "--dry-run"])
    assert result.exit_code == 0
    assert "Backups that would be removed" in result.stdout
    normalized = result.stdout.replace("\n", "")
    assert "20240101010101" in normalized


def test_validate_prune_arguments_require_selector():
    with pytest.raises(typer.Exit):
        backup_module._validate_prune_arguments(None, None)


def test_validate_prune_arguments_parses_timestamp():
    cutoff = backup_module._validate_prune_arguments(keep=1, before="20240101010101")
    assert cutoff is not None
    assert cutoff.year == 2024


def test_select_backups_to_remove_honors_filters(tmp_path):
    now = datetime.now(tz=timezone.utc)
    entries = [
        backups_core.BackupEntry(tmp_path / "new", "new", now, 100),
        backups_core.BackupEntry(tmp_path / "old", "old", now - timedelta(days=10), 100),
        backups_core.BackupEntry(tmp_path / "older", "older", now - timedelta(days=40), 100),
    ]

    cutoff = now - timedelta(days=7)
    to_remove = backup_module._select_backups_to_remove(entries, keep=1, cutoff=cutoff)
    assert tmp_path / "old" in to_remove


def test_delete_backups_removes_files(tmp_path):
    target = tmp_path / "config.backup"
    target.write_text("data")

    removed = backup_module._delete_backups([target])
    assert removed == [target]
    assert not target.exists()
