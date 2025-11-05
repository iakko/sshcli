from __future__ import annotations

from pathlib import Path
from typing import List

import typer

from ..config import parse_config_files, remove_host_block
from ..models import HostBlock
from .common import console, matching_blocks


def register(app: typer.Typer) -> None:
    @app.command("remove")
    def remove_host(
        name: str = typer.Argument(..., help="Host block name or pattern to remove."),
        target: Path = typer.Option(
            Path("~/.ssh/config"),
            "--target",
            "-t",
            help="SSH config file to modify.",
            rich_help_panel="Targeting",
        ),
    ):
        """Remove a host block from the specified SSH config."""
        resolved_target = target.expanduser()
        if not resolved_target.exists():
            console.print(f"[red]Config file {resolved_target} does not exist.[/red]")
            raise typer.Exit(1)

        blocks = [
            block
            for block in parse_config_files([resolved_target])
            if block.source_file == resolved_target
        ]

        _, matched = matching_blocks(name, blocks)

        if not matched:
            console.print(f"[yellow]No host block matches '{name}' in {resolved_target}.[/yellow]")
            raise typer.Exit(1)

        if len(matched) > 1:
            console.print("[yellow]Multiple host blocks match. Select which to remove:[/yellow]")
            for idx, block in enumerate(matched, start=1):
                console.print(
                    f"  {idx}. {' '.join(block.patterns)} ({block.source_file}:{block.lineno})"
                )
            console.print("  a. Remove all matches")

            try:
                selection = typer.prompt("Choice").strip().lower()
            except typer.Abort:
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(1)

            if selection == "a":
                to_remove = matched
            else:
                try:
                    index = int(selection)
                except ValueError:
                    console.print("[red]Invalid selection.[/red]")
                    raise typer.Exit(1)
                if index < 1 or index > len(matched):
                    console.print("[red]Selection out of range.[/red]")
                    raise typer.Exit(1)
                to_remove = [matched[index - 1]]
        else:
            to_remove = [matched[0]]

        ordered_blocks: List[HostBlock] = sorted(to_remove, key=lambda b: b.lineno, reverse=True)

        for block in ordered_blocks:
            backup = remove_host_block(resolved_target, block)
            console.print(
                f"[green]Removed Host block {' '.join(block.patterns)} from {resolved_target}.[/green]"
            )
            if backup:
                console.print(f"[dim]Backup saved to {backup}.[/dim]")


__all__ = ["register"]
