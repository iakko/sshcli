from __future__ import annotations

from typing import List

import typer
from rich.panel import Panel

from .. import config as config_module
from .common import console, format_block_table, matching_blocks


def register(app: typer.Typer) -> None:
    @app.command("show")
    def show_host(
        name: str = typer.Argument(..., help="The host block name/pattern to display (exact match or wildcard)."),
        details: bool = typer.Option(
            False,
            "--details",
            help="Include all matching Host blocks (wildcards) instead of only the most specific match.",
        ),
    ):
        """Show the options of a specific Host block."""
        blocks = config_module.load_host_blocks()
        primary_blocks, matched_blocks = matching_blocks(name, blocks)

        if not matched_blocks:
            console.print(f"[yellow]No host block matches '{name}'.[/yellow]")
            raise typer.Exit(1)

        console.print(f"[bold cyan]Query[/bold cyan]: {name}")

        blocks_to_display: List = matched_blocks if details else primary_blocks

        for block in blocks_to_display:
            header = f"[bold]Host {' '.join(block.patterns)}[/bold]"
            meta = f"{block.source_file} :{block.lineno}"
            console.print(Panel.fit(meta, title=header, title_align="left"))
            console.print(format_block_table(block))
            console.print()

        if not details and len(matched_blocks) > len(blocks_to_display):
            console.print(
                "[yellow]Additional matching blocks exist. Re-run with --details to view them.[/yellow]"
            )


__all__ = ["register"]
