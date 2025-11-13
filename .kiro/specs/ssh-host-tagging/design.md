# Design Document

## Overview

This design implements a tagging system for SSH hosts that stores metadata as specially-formatted comments in SSH config files. The system extends the existing parser and writer components to handle metadata comments while maintaining backward compatibility and preserving the config file as the single source of truth.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Application Layer                    │
│  (CLI Commands, UI Components)                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│                    Business Logic                        │
│  - Tag filtering                                        │
│  - Tag autocomplete                                     │
│  - Tag validation                                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                            │
│  - HostBlock (extended with tags/color)                │
│  - Metadata parser                                      │
│  - Metadata writer                                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│                  SSH Config Files                        │
│  (Single source of truth)                               │
└─────────────────────────────────────────────────────────┘
```

### Component Interaction

```
User Action (Add Tag)
    │
    ▼
UI Dialog / CLI Command
    │
    ▼
Update HostBlock.tags
    │
    ▼
Config Writer (format_host_block_with_metadata)
    │
    ▼
Write to SSH Config File
    │
    ▼
Reload (parse_config_files)
    │
    ▼
Display Updated Tags
```

## Components and Interfaces

### 0. CLI Command Structure

**File:** `sshcli/commands/tag.py` (new file)

New CLI command group for tag management:

```python
import typer
from typing import List, Optional
from pathlib import Path

from ..core.config import load_host_blocks, replace_host_block_with_metadata
from ..models import HostBlock
from .common import console

app = typer.Typer(help="Manage host tags")


@app.command("add")
def add_tags(
    host_pattern: str = typer.Argument(..., help="Host pattern to add tags to"),
    tags: List[str] = typer.Argument(..., help="Tags to add"),
) -> None:
    """Add one or more tags to a host."""
    blocks = load_host_blocks()
    matching = [b for b in blocks if host_pattern in b.patterns]
    
    if not matching:
        console.print(f"[red]No host found matching '{host_pattern}'[/red]")
        raise typer.Exit(1)
    
    if len(matching) > 1:
        console.print(f"[yellow]Multiple hosts match '{host_pattern}':[/yellow]")
        for block in matching:
            console.print(f"  - {', '.join(block.patterns)}")
        raise typer.Exit(1)
    
    block = matching[0]
    for tag in tags:
        block.add_tag(tag)
    
    replace_host_block_with_metadata(
        Path(block.source_file),
        block,
        block.patterns,
        list(block.options.items())
    )
    
    console.print(f"[green]Added tags {', '.join(repr(t) for t in tags)} to {host_pattern}[/green]")


@app.command("remove")
def remove_tags(
    host_pattern: str = typer.Argument(..., help="Host pattern to remove tags from"),
    tags: List[str] = typer.Argument(..., help="Tags to remove"),
) -> None:
    """Remove one or more tags from a host."""
    blocks = load_host_blocks()
    matching = [b for b in blocks if host_pattern in b.patterns]
    
    if not matching:
        console.print(f"[red]No host found matching '{host_pattern}'[/red]")
        raise typer.Exit(1)
    
    block = matching[0]
    for tag in tags:
        block.remove_tag(tag)
    
    replace_host_block_with_metadata(
        Path(block.source_file),
        block,
        block.patterns,
        list(block.options.items())
    )
    
    console.print(f"[green]Removed tags {', '.join(repr(t) for t in tags)} from {host_pattern}[/green]")


@app.command("list")
def list_tags() -> None:
    """List all tags and their usage counts."""
    blocks = load_host_blocks()
    tag_counts: dict[str, int] = {}
    
    for block in blocks:
        for tag in block.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    if not tag_counts:
        console.print("[yellow]No tags found[/yellow]")
        return
    
    for tag in sorted(tag_counts.keys()):
        count = tag_counts[tag]
        console.print(f"{tag} ({count} host{'s' if count != 1 else ''})")


@app.command("show")
def show_tag(
    tag: str = typer.Argument(..., help="Tag to filter by"),
) -> None:
    """Show all hosts with a specific tag."""
    blocks = load_host_blocks()
    matching = [b for b in blocks if b.has_tag(tag)]
    
    if not matching:
        console.print(f"[yellow]No hosts found with tag '{tag}'[/yellow]")
        return
    
    for block in matching:
        hostname = block.options.get("HostName", "")
        tags_str = ", ".join(block.tags)
        console.print(f"{', '.join(block.patterns):20} {hostname:20} [{tags_str}]")


@app.command("color")
def set_color(
    host_pattern: str = typer.Argument(..., help="Host pattern to set color for"),
    color: str = typer.Argument(..., help="Color name or hex code"),
) -> None:
    """Set the color for a host."""
    blocks = load_host_blocks()
    matching = [b for b in blocks if host_pattern in b.patterns]
    
    if not matching:
        console.print(f"[red]No host found matching '{host_pattern}'[/red]")
        raise typer.Exit(1)
    
    block = matching[0]
    block.color = color
    
    replace_host_block_with_metadata(
        Path(block.source_file),
        block,
        block.patterns,
        list(block.options.items())
    )
    
    console.print(f"[green]Set color '{color}' for {host_pattern}[/green]")
```

**File:** `sshcli/commands/__init__.py` (modification)

Register the new tag command group:

```python
def register_commands(app: typer.Typer) -> None:
    # ... existing commands ...
    from . import tag
    app.add_typer(tag.app, name="tag")
```

### 1. Extended HostBlock Model

**File:** `sshcli/models.py`

```python
class HostBlock:
    """Represents a single Host block with metadata support."""
    
    def __init__(self, patterns: List[str], source_file: Path, lineno: int):
        self.patterns = patterns
        self.options: Dict[str, str] = {}
        self.source_file = source_file
        self.lineno = lineno
        
        # New metadata fields
        self.tags: List[str] = []
        self.color: Optional[str] = None
        self.metadata_lineno: int = lineno  # Line where metadata starts
    
    @property
    def names_for_listing(self) -> List[str]:
        """Return non-wildcard host names for concise listing output."""
        return [p for p in self.patterns if not any(ch in p for ch in "*?[]")]
    
    def has_tag(self, tag: str) -> bool:
        """Check if this host has a specific tag (case-insensitive)."""
        return tag.lower() in [t.lower() for t in self.tags]
    
    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if not self.has_tag(tag):
            self.tags.append(tag.strip())
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag (case-insensitive)."""
        self.tags = [t for t in self.tags if t.lower() != tag.lower()]
```

### 2. Metadata Parser

**File:** `sshcli/core/metadata.py` (new file)

```python
from typing import List, Tuple, Optional

def parse_metadata_comment(line: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a metadata comment line.
    
    Returns:
        (key, value) tuple or (None, None) if not a metadata comment
    
    Examples:
        "# @tags: prod, web" -> ("tags", "prod, web")
        "# @color: red" -> ("color", "red")
        "# regular comment" -> (None, None)
    """
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None, None
    
    content = stripped[1:].strip()
    if not content.startswith("@"):
        return None, None
    
    if ":" not in content:
        return None, None
    
    key, value = content[1:].split(":", 1)
    return key.strip().lower(), value.strip()


def parse_tags(value: str) -> List[str]:
    """
    Parse comma-separated tags from a value string.
    
    Example:
        "prod, web, critical" -> ["prod", "web", "critical"]
    """
    if not value:
        return []
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def format_metadata_comments(tags: List[str], color: Optional[str]) -> List[str]:
    """
    Format metadata as comment lines.
    
    Returns:
        List of comment lines to write before Host declaration
    """
    lines = []
    if tags:
        tags_str = ", ".join(tags)
        lines.append(f"# @tags: {tags_str}")
    if color:
        lines.append(f"# @color: {color}")
    return lines
```

### 3. Enhanced Config Parser

**File:** `sshcli/core/config.py` (modifications)

The parser needs to track pending comments before each Host block:

```python
def _read_lines_with_comments(path: Path) -> Iterable[Tuple[int, str, bool]]:
    """
    Yield (line_number, text, is_comment) tuples.
    
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
```

### 4. Enhanced Config Writer

**File:** `sshcli/core/config.py` (modifications)

```python
def format_host_block_with_metadata(
    patterns: List[str],
    options: List[Tuple[str, str]],
    tags: List[str] = None,
    color: str = None,
) -> str:
    """Format a host block with metadata comments."""
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


def replace_host_block_with_metadata(
    target: Path,
    block: HostBlock,
    patterns: List[str],
    options: List[Tuple[str, str]],
) -> Optional[Path]:
    """Replace a host block, preserving or updating metadata."""
    target = target.expanduser()
    if not target.exists():
        raise FileNotFoundError(f"Config file {target} does not exist.")

    with target.open("r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    backup = _backup_file(target)

    # Start from metadata line if it exists, otherwise from Host line
    start_idx = max(block.metadata_lineno - 1, 0)
    end_idx = block.lineno  # Start from Host line

    # Find end of block
    while end_idx < len(lines):
        stripped = lines[end_idx].strip()
        if stripped and not stripped.startswith("#"):
            keyword = stripped.split(None, 1)[0].lower()
            if keyword in {"host", "match"}:
                break
        end_idx += 1

    # Generate new block with metadata
    new_block_lines = format_host_block_with_metadata(
        patterns, options, block.tags, block.color
    ).rstrip("\n").split("\n")
    
    lines[start_idx:end_idx] = new_block_lines

    new_content = "\n".join(lines)
    if not new_content.endswith("\n"):
        new_content += "\n"

    with target.open("w", encoding="utf-8") as handle:
        handle.write(new_content)
    return backup
```

## Data Models

### HostBlock Extended Schema

```python
{
    "patterns": ["prod-web-01", "web-*"],
    "options": {
        "HostName": "10.0.1.5",
        "User": "deploy",
        "Port": "22"
    },
    "source_file": Path("/home/user/.ssh/config"),
    "lineno": 15,
    "metadata_lineno": 13,
    "tags": ["prod", "web", "critical"],
    "color": "red"
}
```

### SSH Config File Format

```ssh
# @tags: prod, web, critical
# @color: red
Host prod-web-01
    HostName 10.0.1.5
    User deploy
    Port 22

# @tags: dev, database
Host dev-db-01
    HostName 192.168.1.10
    User admin
```

## Error Handling

### Parsing Errors

1. **Malformed metadata comments**: Silently ignore and treat as regular comments
2. **Invalid tag characters**: Accept any non-comma characters, trim whitespace
3. **Duplicate tags**: Deduplicate when parsing
4. **Missing config file**: Existing error handling continues to work

### Writing Errors

1. **File permission errors**: Propagate existing exceptions
2. **Backup failures**: Propagate existing exceptions
3. **Invalid tag values**: Validate before writing (no commas in individual tags)

### Edge Cases

1. **Empty tags list**: Don't write metadata comments
2. **Tags with special characters**: Allow but escape if needed
3. **Very long tag lists**: No artificial limit, but UI may truncate display
4. **Metadata comments not immediately before Host**: Ignore, only parse comments directly preceding Host line

## Testing Strategy

### Unit Tests

**File:** `tests/test_metadata.py`

```python
def test_parse_metadata_comment_tags():
    """Test parsing @tags comment."""
    key, value = parse_metadata_comment("# @tags: prod, web")
    assert key == "tags"
    assert value == "prod, web"

def test_parse_metadata_comment_color():
    """Test parsing @color comment."""
    key, value = parse_metadata_comment("# @color: red")
    assert key == "color"
    assert value == "red"

def test_parse_metadata_comment_regular():
    """Test that regular comments return None."""
    key, value = parse_metadata_comment("# regular comment")
    assert key is None
    assert value is None

def test_parse_tags():
    """Test tag parsing from comma-separated string."""
    tags = parse_tags("prod, web, critical")
    assert tags == ["prod", "web", "critical"]

def test_format_metadata_comments():
    """Test formatting metadata as comments."""
    lines = format_metadata_comments(["prod", "web"], "red")
    assert lines == ["# @tags: prod, web", "# @color: red"]
```

**File:** `tests/test_config_metadata.py`

```python
def test_parse_host_with_tags(tmp_path):
    """Test parsing a host block with tags."""
    config = tmp_path / "config"
    config.write_text("""
# @tags: prod, web
Host test-host
    HostName example.com
""")
    blocks = parse_config_files([config])
    assert len(blocks) == 1
    assert blocks[0].tags == ["prod", "web"]

def test_parse_host_without_tags(tmp_path):
    """Test parsing a host block without tags."""
    config = tmp_path / "config"
    config.write_text("""
Host test-host
    HostName example.com
""")
    blocks = parse_config_files([config])
    assert len(blocks) == 1
    assert blocks[0].tags == []

def test_write_host_with_tags(tmp_path):
    """Test writing a host block with tags."""
    config = tmp_path / "config"
    block_text = format_host_block_with_metadata(
        ["test-host"],
        [("HostName", "example.com")],
        tags=["prod", "web"],
        color="red"
    )
    config.write_text(block_text)
    
    content = config.read_text()
    assert "# @tags: prod, web" in content
    assert "# @color: red" in content
    assert "Host test-host" in content
```

### Integration Tests

**File:** `tests/test_tag_workflow.py`

```python
def test_add_tag_to_existing_host(tmp_path):
    """Test adding tags to an existing host."""
    config = tmp_path / "config"
    config.write_text("""
Host test-host
    HostName example.com
""")
    
    # Load, modify, save
    blocks = parse_config_files([config])
    block = blocks[0]
    block.add_tag("prod")
    block.add_tag("web")
    
    replace_host_block_with_metadata(
        config, block, block.patterns, list(block.options.items())
    )
    
    # Reload and verify
    blocks = parse_config_files([config])
    assert blocks[0].tags == ["prod", "web"]

def test_remove_tag_from_host(tmp_path):
    """Test removing tags from a host."""
    config = tmp_path / "config"
    config.write_text("""
# @tags: prod, web, database
Host test-host
    HostName example.com
""")
    
    blocks = parse_config_files([config])
    block = blocks[0]
    block.remove_tag("web")
    
    replace_host_block_with_metadata(
        config, block, block.patterns, list(block.options.items())
    )
    
    blocks = parse_config_files([config])
    assert blocks[0].tags == ["prod", "database"]
```

### UI Tests

**File:** `tests/test_ui_tags.py`

```python
def test_tag_display_in_list(qtbot):
    """Test that tags are displayed in the host list."""
    # Create window with tagged hosts
    # Verify tag badges are visible

def test_tag_filter(qtbot):
    """Test filtering hosts by tag."""
    # Apply tag filter
    # Verify only matching hosts are shown

def test_tag_edit_dialog(qtbot):
    """Test the tag editing dialog."""
    # Open dialog
    # Add/remove tags
    # Verify changes are saved
```

### CLI Tests

**File:** `tests/test_cli_tags.py`

```python
def test_list_with_tag_filter(tmp_path):
    """Test CLI list command with tag filter."""
    # Create config with tagged hosts
    # Run: sshcli list --tag prod
    # Verify output contains only prod hosts

def test_show_displays_tags(tmp_path):
    """Test that show command displays tags."""
    # Create config with tagged host
    # Run: sshcli show test-host
    # Verify tags are in output
```

## UI Design

### Tag Display in Host List

```
┌─ Hosts ────────────────────────────┐
│ ● prod-web-01  [prod][web][nginx] │
│ ● dev-db-01    [dev][database]    │
│   staging-api  [staging][api]     │
└────────────────────────────────────┘
```

- Colored dot indicates host color
- Tag badges displayed inline after host name
- Tags use subtle background colors

### Tag Filter Control

```
┌─ Filter ──────────────────────────┐
│ [Hosts ▼] [Type to filter...    ]│
│ Tags: [All ▼] [prod(5)][dev(3)] │
└────────────────────────────────────┘
```

- Dropdown showing all available tags with counts
- Click tag to filter
- Multiple tag selection support

### Tag Edit Dialog

```
┌─ Edit Tags: prod-web-01 ──────────┐
│                                    │
│ Current Tags:                      │
│ [prod ×] [web ×] [nginx ×]        │
│                                    │
│ Add Tag: [____________] [Add]     │
│          (autocomplete dropdown)   │
│                                    │
│ Color: [●red ▼]                   │
│                                    │
│        [Cancel]  [Save]           │
└────────────────────────────────────┘
```

## CLI Design

### Enhanced Existing Commands

**List Command with Tag Filter:**

```bash
$ sshcli list --tag prod
prod-web-01    10.0.1.5    [prod, web, nginx]
prod-db-01     10.0.1.6    [prod, database]

$ sshcli list --tag prod --tag web
prod-web-01    10.0.1.5    [prod, web, nginx]
```

Modify `sshcli/commands/list.py`:
```python
@app.command()
def list_hosts(
    patterns: bool = typer.Option(False, "--patterns", help="Show wildcard patterns"),
    files: bool = typer.Option(False, "--files", help="Show source files"),
    tag: List[str] = typer.Option(None, "--tag", help="Filter by tag (can be repeated)"),
) -> None:
    """List all discovered SSH hosts."""
    blocks = load_host_blocks()
    
    # Filter by tags if specified
    if tag:
        blocks = [b for b in blocks if any(b.has_tag(t) for t in tag)]
    
    # ... rest of existing logic, but include tags in output
```

**Show Command with Tags:**

```bash
$ sshcli show prod-web-01
Host: prod-web-01
Tags: prod, web, nginx
Color: red
HostName: 10.0.1.5
User: deploy
Port: 22
```

Modify `sshcli/commands/show.py`:
```python
def render_host_block(block: HostBlock, details: bool = False) -> None:
    """Render a host block with tags."""
    # ... existing code ...
    
    # Add tags section
    if block.tags:
        table.add_row("Tags", ", ".join(block.tags))
    if block.color:
        table.add_row("Color", block.color)
    
    # ... rest of existing code
```

**Find Command with Tags:**

```bash
$ sshcli find --tag prod database
# Shows hosts that match "database" AND have "prod" tag
```

Modify `sshcli/commands/find.py`:
```python
@app.command()
def find_hosts(
    query: str = typer.Argument(..., help="Search query"),
    tag: List[str] = typer.Option(None, "--tag", help="Filter by tag"),
) -> None:
    """Find hosts by pattern or hostname."""
    blocks = load_host_blocks()
    
    # Apply tag filter first
    if tag:
        blocks = [b for b in blocks if any(b.has_tag(t) for t in tag)]
    
    # ... rest of existing search logic
```

### Tag Management Commands

New CLI commands for managing tags:

```bash
# Add tags to a host
$ sshcli tag add prod-web-01 critical monitoring
Added tags 'critical', 'monitoring' to prod-web-01

# Remove tags from a host
$ sshcli tag remove prod-web-01 nginx
Removed tag 'nginx' from prod-web-01

# List all tags across all hosts
$ sshcli tag list
critical (3 hosts)
database (5 hosts)
dev (8 hosts)
monitoring (2 hosts)
nginx (4 hosts)
prod (5 hosts)
web (6 hosts)

# Show hosts with a specific tag
$ sshcli tag show prod
prod-web-01    10.0.1.5    [prod, web, nginx]
prod-db-01     10.0.1.6    [prod, database]
prod-api-01    10.0.1.7    [prod, api]

# Set color for a host
$ sshcli tag color prod-web-01 red
Set color 'red' for prod-web-01
```

## Performance Considerations

1. **Parsing overhead**: Minimal - only adds comment line processing
2. **Memory usage**: Small increase - tags are lightweight strings
3. **File I/O**: No change - still reads entire config file
4. **UI rendering**: Tag badges may add slight overhead for large lists

## Security Considerations

1. **Tag injection**: Tags are written as comments, no SSH security impact
2. **File permissions**: Existing backup and write permissions apply
3. **Tag content**: No validation needed - tags are display-only metadata
4. **XSS in UI**: Escape tag content when rendering in UI

## CLI and UI Alignment

Both CLI and UI use the same core modules, ensuring consistency:

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Commands                          │
│  sshcli tag add/remove/list/show/color                  │
│  sshcli list --tag                                      │
│  sshcli show (displays tags)                            │
│  sshcli find --tag                                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ├──────────────────────────────────────┐
                 │                                      │
                 ▼                                      ▼
┌─────────────────────────────┐    ┌──────────────────────────────┐
│      UI Components          │    │    Shared Core Modules       │
│  - Tag edit dialog          │    │  - models.py (HostBlock)     │
│  - Tag filter dropdown      │    │  - core/config.py (parser)   │
│  - Tag badges in list       │    │  - core/metadata.py (new)    │
│  - Context menu actions     │    │  - core/config.py (writer)   │
└────────────────┬────────────┘    └──────────────┬───────────────┘
                 │                                 │
                 └─────────────┬───────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   SSH Config Files   │
                    │  (Single Source of   │
                    │       Truth)         │
                    └──────────────────────┘
```

### Workflow Examples

**Adding tags via CLI:**
```bash
$ sshcli tag add prod-web-01 monitoring
# Writes metadata comment to config file
# UI will show the tag on next refresh
```

**Adding tags via UI:**
```
User clicks "Edit Tags" → Adds "monitoring" → Saves
# UI calls replace_host_block_with_metadata()
# CLI will show the tag immediately
```

**Manual editing:**
```bash
$ vim ~/.ssh/config
# User adds: # @tags: monitoring
# Both CLI and UI will show the tag on next load
```

All three methods use the same underlying functions:
- `parse_config_files()` - reads tags from comments
- `replace_host_block_with_metadata()` - writes tags as comments
- `HostBlock.add_tag()` / `remove_tag()` - manipulates tag list

## Migration and Compatibility

### Backward Compatibility

- Existing configs without tags work unchanged
- Old versions of sshcli ignore metadata comments
- Standard SSH clients ignore all comments

### Forward Compatibility

- New metadata keys can be added (e.g., `@priority:`, `@notes:`)
- Unknown metadata keys are preserved but ignored

### Migration Path

1. Users can gradually add tags to hosts
2. No migration script needed
3. Tags can be added manually or via UI/CLI
4. No breaking changes to existing functionality
