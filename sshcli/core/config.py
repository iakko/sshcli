from __future__ import annotations

import glob
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from ..models import HostBlock

DEFAULT_HOME_SSH = "~/.ssh"
DEFAULT_HOME_SSH_CONFIG = f"{DEFAULT_HOME_SSH}/config"
DEFAULT_KEYS_DIR = f"{DEFAULT_HOME_SSH}/keys"

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


def _read_lines_with_comments(path: Path) -> Iterable[Tuple[int, str, bool]]:
    """
    Yield (line_number, text, is_comment) tuples.
    
    Args:
        path: Path to the config file
    
    Returns:
        Tuples of (lineno, line_text, is_comment_flag)
    """
    try:
        with path.open("r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                text = line.rstrip("\n")
                is_comment = text.strip().startswith("#")
                yield number, text, is_comment
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


def _start_new_block_with_metadata(
    current: Optional[HostBlock],
    patterns: List[str],
    file_path: Path,
    lineno: int,
    blocks: List[HostBlock],
    pending_comments: List[Tuple[int, str]],
) -> HostBlock:
    """Create a new HostBlock and parse metadata from pending comments."""
    if current is not None:
        blocks.append(current)
    
    # Determine metadata start line
    metadata_lineno = pending_comments[0][0] if pending_comments else lineno
    
    block = HostBlock(patterns=patterns, source_file=file_path, lineno=lineno)
    block.metadata_lineno = metadata_lineno
    
    # Parse metadata from comments
    from .metadata import parse_metadata_comment, parse_tags
    
    for _, comment_line in pending_comments:
        key, value = parse_metadata_comment(comment_line)
        if key == "tags":
            block.tags = parse_tags(value)
        elif key == "color":
            block.color = value
    
    return block


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
    """Parse host blocks with metadata support."""
    seen: set[Path] = set()
    blocks: List[HostBlock] = []

    def parse_one(file_path: Path):
        if not _mark_seen(file_path, seen):
            return

        current: Optional[HostBlock] = None
        pending_comments: List[Tuple[int, str]] = []
        
        for lineno, line, is_comment in _read_lines_with_comments(file_path):
            # Track comments that might be metadata
            if is_comment:
                pending_comments.append((lineno, line))
                continue
            
            # Parse non-comment line
            stripped = line.split("#", 1)[0].strip()
            if not stripped:
                pending_comments.clear()
                continue
            
            parts = stripped.split()
            key = parts[0].lower()

            if _is_include(key, parts):
                _parse_include(parts, file_path, parse_one)
                pending_comments.clear()
                continue

            if key == "match":
                pending_comments.clear()
                continue

            if _is_host_definition(key, parts):
                patterns = parts[1:]
                current = _start_new_block_with_metadata(
                    current, patterns, file_path, lineno, blocks, pending_comments
                )
                pending_comments.clear()
                continue

            current = _append_option(current, parts)

        _finalize_block(current, blocks)

    for entrypoint in entrypoints:
        parse_one(entrypoint)

    return blocks


def _mark_seen(file_path: Path, seen: set[Path]) -> bool:
    if file_path in seen:
        return False
    seen.add(file_path)
    return True


def _is_include(key: str, parts: List[str]) -> bool:
    return key == "include" and len(parts) >= 2


def _parse_include(parts: List[str], file_path: Path, parser) -> None:
    include_pattern = " ".join(parts[1:])
    for included in _expand_path(include_pattern, current_file=file_path):
        parser(included)


def _is_host_definition(key: str, parts: List[str]) -> bool:
    return key == "host" and len(parts) >= 2


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


def format_host_block_with_metadata(
    patterns: List[str],
    options: List[Tuple[str, str]],
    tags: Optional[List[str]] = None,
    color: Optional[str] = None,
) -> str:
    """
    Format a host block with metadata comments for writing to disk.
    
    Args:
        patterns: List of host patterns
        options: List of (key, value) tuples for SSH options
        tags: Optional list of tags to add as metadata
        color: Optional color value to add as metadata
    
    Returns:
        Formatted string with metadata comments, Host declaration, and options
    """
    from .metadata import format_metadata_comments
    
    lines = []
    
    # Add metadata comments
    metadata_lines = format_metadata_comments(tags or [], color)
    lines.extend(metadata_lines)
    
    # Add Host declaration
    lines.append(f"Host {' '.join(patterns)}")
    
    # Add options
    for key, value in options:
        lines.append(f"    {key} {value}")
    
    return "\n".join(lines) + "\n"


def append_host_block(
    target: Path,
    patterns: List[str],
    options: List[Tuple[str, str]],
    tags: Optional[List[str]] = None,
    color: Optional[str] = None,
) -> Optional[Path]:
    """
    Append a host block to the target SSH config, creating the file if needed.
    
    Args:
        target: Path to the SSH config file
        patterns: List of host patterns
        options: List of (key, value) tuples for SSH options
        tags: Optional list of tags to add as metadata
        color: Optional color value to add as metadata
    
    Returns:
        Path to the backup file, or None if no backup was created
    """
    target = target.expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    backup: Optional[Path] = None
    if target.exists():
        backup = _backup_file(target)

    # Use format_host_block_with_metadata() instead of format_host_block()
    block_text = format_host_block_with_metadata(patterns, options, tags, color)
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


def replace_host_block_with_metadata(
    target: Path,
    block: HostBlock,
    patterns: List[str],
    options: List[Tuple[str, str]],
) -> Optional[Path]:
    """
    Replace an existing host block with new content, preserving or updating metadata.
    
    Args:
        target: Path to the SSH config file
        block: The HostBlock to replace (contains metadata_lineno)
        patterns: List of host patterns
        options: List of (key, value) tuples for SSH options
    
    Returns:
        Path to the backup file, or None if no backup was created
    """
    target = target.expanduser()
    if not target.exists():
        raise FileNotFoundError(f"Config file {target} does not exist.")

    # Read existing config file lines
    with target.open("r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    # Create backup using existing _backup_file()
    backup = _backup_file(target)

    # Calculate start_idx from block.metadata_lineno
    start_idx = max(block.metadata_lineno - 1, 0)
    
    # Find end_idx of block (next Host/Match or EOF)
    end_idx = block.lineno  # Start from Host line
    while end_idx < len(lines):
        stripped = lines[end_idx].strip()
        if stripped and not stripped.startswith("#"):
            keyword = stripped.split(None, 1)[0].lower()
            if keyword in {"host", "match"}:
                break
        end_idx += 1

    # Replace lines with new formatted block including metadata
    new_block_lines = format_host_block_with_metadata(
        patterns, options, block.tags, block.color
    ).rstrip("\n").split("\n")
    
    lines[start_idx:end_idx] = new_block_lines

    # Write updated content back to file
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
    "DEFAULT_KEYS_DIR",
    "DEFAULT_HOME_SSH_CONFIG",
    "DEFAULT_INCLUDE_FALLBACKS",
    "append_host_block",
    "discover_config_files",
    "format_host_block",
    "format_host_block_with_metadata",
    "load_host_blocks",
    "parse_config_files",
    "remove_host_block",
    "replace_host_block",
    "replace_host_block_with_metadata",
]
