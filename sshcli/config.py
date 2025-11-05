from __future__ import annotations

import glob
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .models import HostBlock

DEFAULT_HOME_SSH_CONFIG = "~/.ssh/config"

DEFAULT_CONFIG_PATHS = [
    "/etc/ssh/ssh_config",
    DEFAULT_HOME_SSH_CONFIG,
]

DEFAULT_INCLUDE_FALLBACKS = [
    "~/.ssh/config.d/*.conf",
]


def _backup_file(path: Path) -> Path:
    """Create a timestamped backup of the given file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{path.name}.backup.{timestamp}"
    shutil.copy2(path, backup_path)
    return backup_path


def _expand_path(pattern: str, current_file: Optional[Path] = None) -> List[Path]:
    """Expand an include pattern, resolving relative paths against the current file."""
    if current_file and not pattern.startswith(("~", "/")):
        base = current_file.parent
        glob_pattern = str((base / pattern).expanduser())
    else:
        glob_pattern = str(Path(pattern).expanduser())
    matches = [Path(x) for x in glob.glob(glob_pattern)]
    return [m for m in matches if m.is_file()]


def _read_lines(path: Path) -> Iterable[Tuple[int, str]]:
    """Yield (line_number, text) tuples while gracefully handling missing files."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                yield number, line.rstrip("\n")
    except (FileNotFoundError, PermissionError):
        return


def _iter_config_parts(file_path: Path) -> Iterable[Tuple[int, List[str]]]:
    for lineno, raw_line in _read_lines(file_path):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        yield lineno, line.split()


def _start_new_block(
    current: Optional[HostBlock],
    patterns: List[str],
    file_path: Path,
    lineno: int,
    blocks: List[HostBlock],
) -> HostBlock:
    if current is not None:
        blocks.append(current)
    return HostBlock(patterns=patterns, source_file=file_path, lineno=lineno)


def _append_option(current: Optional[HostBlock], parts: List[str]) -> Optional[HostBlock]:
    if current is None or len(parts) < 2:
        return current
    option_key = parts[0]
    option_value = " ".join(parts[1:])
    current.options[option_key] = option_value
    return current


def _finalize_block(current: Optional[HostBlock], blocks: List[HostBlock]) -> None:
    if current is not None:
        blocks.append(current)


def parse_config_files(entrypoints: List[Path]) -> List[HostBlock]:
    """Parse host blocks recursively while following Include directives."""
    seen: set[Path] = set()
    blocks: List[HostBlock] = []

    def parse_one(file_path: Path):
        if file_path in seen:
            return
        seen.add(file_path)

        current: Optional[HostBlock] = None
        for lineno, parts in _iter_config_parts(file_path):
            key = parts[0].lower()

            if key == "include" and len(parts) >= 2:
                include_pattern = " ".join(parts[1:])
                for included in _expand_path(include_pattern, current_file=file_path):
                    parse_one(included)
                continue

            if key == "match":
                # Skipped in this minimal viewer.
                continue

            if key == "host" and len(parts) >= 2:
                patterns = parts[1:]
                current = _start_new_block(current, patterns, file_path, lineno, blocks)
                continue

            current = _append_option(current, parts)

        _finalize_block(current, blocks)

    for entrypoint in entrypoints:
        parse_one(entrypoint)

    return blocks


def discover_config_files() -> List[Path]:
    """Return the list of entrypoint configuration files to parse."""
    files: List[Path] = []
    for path in DEFAULT_CONFIG_PATHS:
        expanded = Path(path).expanduser()
        if expanded.is_file():
            files.append(expanded)
    if not files:
        for pattern in DEFAULT_INCLUDE_FALLBACKS:
            files.extend(_expand_path(pattern))
    return files


def load_host_blocks() -> List[HostBlock]:
    """Load host blocks from the discovered SSH configuration files."""
    files = discover_config_files()
    return parse_config_files(files)


def format_host_block(patterns: List[str], options: List[Tuple[str, str]]) -> str:
    """Format a host block for writing to disk."""
    lines = [f"Host {' '.join(patterns)}"]
    for key, value in options:
        lines.append(f"    {key} {value}")
    return "\n".join(lines) + "\n"


def append_host_block(target: Path, patterns: List[str], options: List[Tuple[str, str]]) -> Optional[Path]:
    """Append a host block to the target SSH config, creating the file if needed."""
    target = target.expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    backup: Optional[Path] = None
    if target.exists():
        backup = _backup_file(target)

    block_text = format_host_block(patterns, options)
    separator = ""
    if target.exists():
        size = target.stat().st_size
        if size > 0:
            with target.open("rb") as handle:
                handle.seek(-1, os.SEEK_END)
                last = handle.read(1)
            separator = "\n" if last == b"\n" else "\n\n"
    with target.open("a", encoding="utf-8") as handle:
        handle.write(separator + block_text)
    return backup


def replace_host_block(
    target: Path,
    block: HostBlock,
    patterns: List[str],
    options: List[Tuple[str, str]],
) -> Optional[Path]:
    """Replace an existing host block in the given file with new content."""
    target = target.expanduser()
    if not target.exists():
        raise FileNotFoundError(f"Config file {target} does not exist.")

    with target.open("r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    backup = _backup_file(target)

    start_idx = max(block.lineno - 1, 0)
    end_idx = start_idx + 1

    while end_idx < len(lines):
        stripped = lines[end_idx].strip()
        if stripped and not stripped.startswith("#"):
            keyword = stripped.split(None, 1)[0].lower()
            if keyword in {"host", "match"}:
                break
        end_idx += 1

    new_block_lines = format_host_block(patterns, options).rstrip("\n").split("\n")
    lines[start_idx:end_idx] = new_block_lines

    new_content = "\n".join(lines)
    if not new_content.endswith("\n"):
        new_content += "\n"

    with target.open("w", encoding="utf-8") as handle:
        handle.write(new_content)
    return backup


def remove_host_block(target: Path, block: HostBlock) -> Optional[Path]:
    """Remove a host block from the given file."""
    target = target.expanduser()
    if not target.exists():
        raise FileNotFoundError(f"Config file {target} does not exist.")

    backup = _backup_file(target)

    with target.open("r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    start_idx = max(block.lineno - 1, 0)
    end_idx = start_idx + 1

    while end_idx < len(lines):
        stripped = lines[end_idx].strip()
        if stripped and not stripped.startswith("#"):
            keyword = stripped.split(None, 1)[0].lower()
            if keyword in {"host", "match"}:
                break
        end_idx += 1

    del lines[start_idx:end_idx]

    while start_idx < len(lines) and lines[start_idx].strip() == "":
        del lines[start_idx]

    new_content = "\n".join(lines)
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"

    with target.open("w", encoding="utf-8") as handle:
        handle.write(new_content)
    return backup


__all__ = [
    "DEFAULT_CONFIG_PATHS",
    "DEFAULT_INCLUDE_FALLBACKS",
    "append_host_block",
    "discover_config_files",
    "format_host_block",
    "load_host_blocks",
    "parse_config_files",
    "remove_host_block",
    "replace_host_block",
]
