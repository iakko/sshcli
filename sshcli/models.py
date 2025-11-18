from __future__ import annotations

from pathlib import Path
from typing import Dict, List


class HostBlock:
    """Represents a single `Host` block parsed from an SSH config."""

    def __init__(self, patterns: List[str], source_file: Path, lineno: int):
        self.patterns = patterns
        self.options: Dict[str, str] = {}
        self.source_file = source_file
        self.lineno = lineno
        
        # Metadata fields
        self.tags: List[str] = []
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


__all__ = ["HostBlock"]
