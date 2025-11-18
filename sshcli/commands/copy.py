from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .. import config as config_module
from .common import console, matching_blocks


def register(app: typer.Typer) -> None:
    @app.command("copy")
    def copy_host(
        source: str = typer.Argument(..., help="Host block name or pattern to copy."),
        name: str = typer.Option(
            ...,
            "--name",
            "-n",
            help="Name for the new Host block.",
        ),
        target: Optional[Path] = typer.Option(
            None,
            "--target",
            "-t",
            help="SSH config file to append to.",
            rich_help_panel="Targeting",
        ),
        force: bool = typer.Option(
            False,
            "--force",
            help="Allow copying even if another block already uses the destination name.",
        ),
    ):
        """Copy an existing Host block into a new entry."""
        if not name.strip():
            raise typer.BadParameter("Destination name must be a non-empty string.")

        if target is None:
            target = config_module.default_config_path()

        resolved_target = target.expanduser()
        if not resolved_target.exists():
            console.print(f"[red]Config file {resolved_target} does not exist.[/red]")
            raise typer.Exit(1)

        blocks = [
            block
            for block in config_module.parse_config_files([resolved_target])
            if block.source_file == resolved_target
        ]

        primary_blocks, matched_blocks = matching_blocks(source, blocks)
        if not matched_blocks:
            console.print(f"[yellow]No host block matches '{source}' in {resolved_target}.[/yellow]")
            raise typer.Exit(1)

        source_block = primary_blocks[0] if primary_blocks else matched_blocks[0]

        duplicate = next(
            (
                block
                for block in blocks
                if name in block.patterns or name in block.names_for_listing
            ),
            None,
        )
        if duplicate and not force:
            console.print(
                f"[red]Host block '{name}' already exists at {duplicate.source_file}:{duplicate.lineno}. "
                "Use --force to create a duplicate entry.[/red]"
            )
            raise typer.Exit(1)

        new_patterns = [name]
        new_options = list(source_block.options.items())

        backup = config_module.append_host_block(resolved_target, new_patterns, new_options)
        console.print(
            f"[green]Copied Host block '{source_block.patterns[0]}' to new block '{name}' in {resolved_target}.[/green]"
        )
        if backup:
            console.print(f"[dim]Backup saved to {backup}.[/dim]")


__all__ = ["register"]
