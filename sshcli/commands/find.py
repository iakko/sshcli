from __future__ import annotations

import fnmatch
from typing import List, Tuple

import typer
from rich import box
from rich.table import Table

from .. import config as config_module
from ..models import HostBlock
from .common import console


def register(app: typer.Typer) -> None:
    @app.command("find")
    def find_hosts(
        query: str = typer.Argument(..., help="Substring or wildcard pattern to search in Host patterns or HostName."),
        tag: List[str] = typer.Option(None, "--tag", help="Filter by tag before searching."),
    ):
        """Search Host blocks by pattern (wildcards) or HostName substring."""
        blocks = config_module.load_host_blocks()
        
        # Apply tag filter first
        if tag:
            blocks = [b for b in blocks if any(b.has_tag(t) for t in tag)]
        
        hits: List[Tuple[str, HostBlock]] = []

        for block in blocks:
            patterns_match = any(
                fnmatch.fnmatch(pattern, query) or query.lower() in pattern.lower()
                for pattern in block.patterns
            )
            host_name = block.options.get("HostName", "")
            hostname_match = fnmatch.fnmatch(host_name, query) or query.lower() in host_name.lower()
            if patterns_match or hostname_match:
                label = ", ".join(block.names_for_listing or block.patterns)
                hits.append((label, block))

        if not hits:
            console.print(f"[yellow]No results for '{query}'.[/yellow]")
            raise typer.Exit(0)

        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Host", style="bold cyan")
        table.add_column("Patterns")
        table.add_column("HostName")
        table.add_column("User")
        table.add_column("File:Line")

        for label, block in hits:
            table.add_row(
                label,
                " ".join(block.patterns),
                block.options.get("HostName", ""),
                block.options.get("User", ""),
                f"{block.source_file}:{block.lineno}",
            )
        console.print(table)


__all__ = ["register"]
