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

    @property
    def names_for_listing(self) -> List[str]:
        """Return non-wildcard host names for concise listing output."""
        return [p for p in self.patterns if not any(ch in p for ch in "*?[]")]


__all__ = ["HostBlock"]
