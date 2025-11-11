from __future__ import annotations

from pathlib import Path
from typing import List

import typer

from .. import config as config_module
from ..models import HostBlock
from .common import console, matching_blocks


def _resolve_target(target: Path) -> Path:
    resolved = target.expanduser()
    if not resolved.exists():
        console.print(f"[red]Config file {resolved} does not exist.[/red]")
        raise typer.Exit(1)
    return resolved


def _load_blocks_for_target(resolved_target: Path) -> List[HostBlock]:
    return [
        block
        for block in config_module.parse_config_files([resolved_target])
        if block.source_file == resolved_target
    ]


def _find_matching_blocks(name: str, blocks: List[HostBlock], target: Path) -> List[HostBlock]:
    _, matched = matching_blocks(name, blocks)
    if not matched:
        console.print(f"[yellow]No host block matches '{name}' in {target}.[/yellow]")
        raise typer.Exit(1)
    return matched


def _select_blocks_to_remove(matched: List[HostBlock]) -> List[HostBlock]:
    if len(matched) == 1:
        return [matched[0]]

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
        return matched

    try:
        index = int(selection)
    except ValueError:
        console.print("[red]Invalid selection.[/red]")
        raise typer.Exit(1)

    if index < 1 or index > len(matched):
        console.print("[red]Selection out of range.[/red]")
        raise typer.Exit(1)

    return [matched[index - 1]]


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
        resolved_target = _resolve_target(target)
        blocks = _load_blocks_for_target(resolved_target)
        matched = _find_matching_blocks(name, blocks, resolved_target)
        selected = _select_blocks_to_remove(matched)
        ordered_blocks: List[HostBlock] = sorted(selected, key=lambda b: b.lineno, reverse=True)

        for block in ordered_blocks:
            backup = config_module.remove_host_block(resolved_target, block)
            console.print(
                f"[green]Removed Host block {' '.join(block.patterns)} from {resolved_target}.[/green]"
            )
            if backup:
                console.print(f"[dim]Backup saved to {backup}.[/dim]")


__all__ = ["register"]
