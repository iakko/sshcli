from __future__ import annotations

from typing import List

import typer
from rich import box
from rich.table import Table

from .. import config as config_module
from .common import console


def register(app: typer.Typer) -> None:
    @app.command("list")
    def list_hosts(
        show_patterns: bool = typer.Option(
            False, "--patterns", help="Show full Host patterns (including wildcards)."
        ),
        files: bool = typer.Option(False, "--files", help="Show origin file and line for each block."),
        tag: List[str] = typer.Option(None, "--tag", help="Filter by tag (can be repeated)."),
    ):
        """List Host blocks discovered in your SSH configs."""
        blocks = config_module.load_host_blocks()
        
        # Filter by tags if specified
        if tag:
            blocks = [b for b in blocks if any(b.has_tag(t) for t in tag)]
        
        if not blocks:
            console.print("[yellow]No SSH host blocks found.[/yellow]")
            raise typer.Exit(code=0)

        table = Table(box=box.SIMPLE_HEAVY, show_lines=False)
        table.add_column("Host", style="bold cyan")
        table.add_column("HostName")
        table.add_column("User")
        table.add_column("Port", justify="right")
        table.add_column("Tags")
        if show_patterns:
            table.add_column("Patterns")
        if files:
            table.add_column("Defined at")

        for block in blocks:
            hostnames = block.options.get("HostName", "")
            user = block.options.get("User", "")
            port = block.options.get("Port", "")
            names = block.names_for_listing or [block.patterns[0]]
            name_str = ", ".join(names)
            tags_str = ", ".join(block.tags) if block.tags else ""

            row: List[str] = [name_str, hostnames, user, port, tags_str]
            if show_patterns:
                row.append(" ".join(block.patterns))
            if files:
                row.append(f"{block.source_file} :{block.lineno}")
            table.add_row(*row)

        console.print(table)


__all__ = ["register"]
