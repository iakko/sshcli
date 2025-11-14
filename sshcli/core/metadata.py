"""Metadata parsing and formatting for SSH host tags and colors."""

from typing import List, Tuple, Optional


def parse_metadata_comment(line: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a metadata comment line.
    
    Args:
        line: A line from the SSH config file
    
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


def format_metadata_comments(tags: List[str], color: Optional[str]) -> List[str]:
    """
    Format metadata as comment lines.
    
    Args:
        tags: List of tag strings
        color: Optional color value
    
    Returns:
        List of comment lines to write before Host declaration
    
    Example:
        (["prod", "web"], "red") -> ["# @tags: prod, web", "# @color: red"]
    """
    lines = []
    if tags:
        tags_str = ", ".join(tags)
        lines.append(f"# @tags: {tags_str}")
    if color:
        lines.append(f"# @color: {color}")
    return lines
