from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Sequence

from . import config as config_module


@dataclass
class BackupEntry:
    path: Path
    stamp: str
    timestamp: Optional[datetime]
    size: int

    @property
    def sort_key(self) -> float:
        if self.timestamp is not None:
            return self.timestamp.timestamp()
        return self.path.stat().st_mtime


def discover_backups(target: Path) -> List[BackupEntry]:
    resolved = target.expanduser()
    backup_dir = resolved.parent / "backups"

    if not backup_dir.exists():
        return []

    prefix = f"{resolved.name}.backup."
    entries: List[BackupEntry] = []
    seen_paths: set[Path] = set()

    for candidate in backup_dir.glob(f"{resolved.name}.backup.*"):
        if not candidate.is_file() or candidate in seen_paths:
            continue
        seen_paths.add(candidate)
        stamp = candidate.name[len(prefix):]
        timestamp = parse_backup_timestamp(stamp)
        entries.append(
            BackupEntry(
                path=candidate,
                stamp=stamp,
                timestamp=timestamp,
                size=candidate.stat().st_size,
            )
        )

    return sorted(entries, key=lambda entry: entry.sort_key, reverse=True)


def select_backup(identifier: str, backups: Sequence[BackupEntry]) -> Optional[BackupEntry]:
    for entry in backups:
        if (
            entry.stamp == identifier
            or entry.path.name == identifier
            or str(entry.path) == identifier
        ):
            return entry
    return None


def create_backup(target: Path) -> Optional[Path]:
    target = target.expanduser()
    if not target.exists():
        return None
    return config_module._backup_file(target)


def parse_backup_timestamp(value: str) -> Optional[datetime]:
    try:
        naive = datetime.strptime(value, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    dt_utc = naive.replace(tzinfo=timezone.utc)
    now_utc = datetime.now(tz=timezone.utc)
    if dt_utc - now_utc > timedelta(minutes=5):
        local_tz = datetime.now().astimezone().tzinfo
        if local_tz is not None:
            dt_local = naive.replace(tzinfo=local_tz)
            dt_utc = dt_local.astimezone(timezone.utc)
    return dt_utc


__all__ = [
    "BackupEntry",
    "discover_backups",
    "select_backup",
    "create_backup",
    "parse_backup_timestamp",
]
