"""Metadata parsing and formatting for SSH host tags."""

from typing import Dict, List, Tuple, Optional


def parse_metadata_comment(line: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse metadata comment lines that precede Host blocks."""
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
    
    Args:
        value: Comma-separated tag string
    
    Returns:
        List of tag strings with whitespace trimmed
    
    Example:
        "prod, web, critical" -> ["prod", "web", "critical"]
    """
    if not value:
        return []
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def format_metadata_comments(tags: List[str]) -> List[str]:
    """Return comment lines that encode the tags attached to a host."""

    if not tags:
        return []
    tags_str = ", ".join(tags)
    return [f"# @tags: {tags_str}"]


def parse_tag_definition(line: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a tag definition comment of the form '# @tagdef name color'."""
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None, None
    content = stripped[1:].strip()
    if not content.lower().startswith("@tagdef"):
        return None, None
    parts = content.split(None, 2)
    if len(parts) < 2:
        return None, None
    tag = parts[1].strip()
    color = parts[2].strip() if len(parts) >= 3 else ""
    return tag, color


def format_tag_definitions(definitions: Dict[str, str]) -> List[str]:
    """Format tag definitions as comment lines."""
    lines: List[str] = []
    for tag in sorted(definitions.keys(), key=str.lower):
        color = definitions[tag]
        if color:
            lines.append(f"# @tagdef {tag} {color}")
        else:
            lines.append(f"# @tagdef {tag}")
    return lines
