from __future__ import annotations

import fnmatch
from typing import List, Optional, Tuple

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from ..models import HostBlock

console = Console()


def format_block_table(block: HostBlock) -> Table:
    table = Table(box=box.SIMPLE, show_lines=False)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    
    # Add tags row if block has tags
    if block.tags:
        table.add_row("[bold]Tags[/bold]", ", ".join(block.tags))
    
    for key in sorted(block.options.keys(), key=str.lower):
        table.add_row(f"[bold]{key}[/bold]", block.options[key])
    return table


def matching_blocks(name: str, blocks: List[HostBlock]) -> Tuple[List[HostBlock], List[HostBlock]]:
    matched: List[HostBlock] = []
    best_block: Optional[HostBlock] = None
    best_score: Optional[Tuple[int, int, int, int]] = None

    for idx, block in enumerate(blocks):
        block_best = _best_score_for_block(name, block, idx)
        if block_best is None:
            continue

        matched.append(block)
        if best_score is None or block_best > best_score:
            best_score = block_best
            best_block = block

    if not matched:
        return [], []

    primary = [best_block] if best_block is not None else []
    return primary, matched


def _best_score_for_block(
    name: str,
    block: HostBlock,
    index: int,
) -> Optional[Tuple[int, int, int, int]]:
    block_best: Optional[Tuple[int, int, int, int]] = None
    for pattern in block.patterns:
        score = _score_pattern(name, pattern, index)
        if score is None:
            continue
        if block_best is None or score > block_best:
            block_best = score
    return block_best


def _score_pattern(name: str, pattern: str, index: int) -> Optional[Tuple[int, int, int, int]]:
    if not fnmatch.fnmatch(name, pattern):
        return None
    literal = 1 if pattern == name else 0
    wildcard_count = sum(1 for ch in pattern if ch in "*?[]")
    return literal, -wildcard_count, len(pattern), index


def parse_option_entry(entry: str) -> Tuple[str, str]:
    if "=" not in entry:
        raise typer.BadParameter("Options must be in KEY=VALUE form.")
    key, value = entry.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key or not value:
        raise typer.BadParameter("Option entries require both key and value.")
    return key, value


__all__ = ["console", "format_block_table", "matching_blocks", "parse_option_entry"]
