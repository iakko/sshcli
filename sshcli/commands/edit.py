from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import typer

from ..config import parse_config_files, replace_host_block
from ..models import HostBlock
from .common import console, matching_blocks, parse_option_entry


def register(app: typer.Typer) -> None:
    @app.command("edit")
    def edit_host(
        name: str = typer.Argument(..., help="Host block name or pattern to edit."),
        hostname: Optional[str] = typer.Option(None, "--hostname", "-H", help="Update the HostName option."),
        user: Optional[str] = typer.Option(None, "--user", "-u", help="Update the User option."),
        port: Optional[int] = typer.Option(None, "--port", "-p", help="Update the Port option."),
        option: List[str] = typer.Option(
            [],
            "--option",
            "-o",
            help="Set or update option in KEY=VALUE form. Repeat for multiple options.",
        ),
        remove_option: List[str] = typer.Option(
            [],
            "--remove-option",
            "-r",
            help="Remove an option by key. Repeat for multiple keys.",
        ),
        set_pattern: Optional[List[str]] = typer.Option(
            None,
            "--set-pattern",
            "-P",
            help="Replace the Host patterns for the block. Repeat to supply multiple patterns.",
        ),
        clear_options: bool = typer.Option(
            False,
            "--clear-options",
            help="Drop all existing options before applying updates.",
        ),
        target: Path = typer.Option(
            Path("~/.ssh/config"),
            "--target",
            "-t",
            help="SSH config file to edit.",
            rich_help_panel="Targeting",
        ),
    ):
        """Edit options or patterns of an existing Host block."""
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
            console.print("[red]Multiple host blocks match. Refine your selection:[/red]")
            for block in matched:
                console.print(
                    f"  - {' '.join(block.patterns)} ({block.source_file}:{block.lineno})"
                )
            raise typer.Exit(1)

        block = matched[0]
        if set_pattern is not None and len(set_pattern) == 0:
            console.print("[red]At least one pattern is required when replacing patterns.[/red]")
            raise typer.Exit(1)

        new_patterns = list(set_pattern) if set_pattern is not None else list(block.patterns)

        options_list: List[Tuple[str, str]]
        if clear_options:
            options_list = []
        else:
            options_list = list(block.options.items())

        def set_option_value(key: str, value: str) -> None:
            lower = key.lower()
            for idx, (existing_key, _) in enumerate(options_list):
                if existing_key.lower() == lower:
                    options_list[idx] = (existing_key, value)
                    return
            options_list.append((key, value))

        def remove_option_key(key: str) -> bool:
            lower = key.lower()
            for idx, (existing_key, _) in enumerate(options_list):
                if existing_key.lower() == lower:
                    del options_list[idx]
                    return True
            return False

        if hostname is not None:
            if hostname == "":
                remove_option_key("HostName")
            else:
                set_option_value("HostName", hostname)

        if user is not None:
            if user == "":
                remove_option_key("User")
            else:
                set_option_value("User", user)

        if port is not None:
            set_option_value("Port", str(port))

        for entry in option:
            try:
                key, value = parse_option_entry(entry)
            except typer.BadParameter:
                console.print(
                    f"[red]Options must be supplied as KEY=VALUE (received '{entry}').[/red]"
                )
                raise typer.Exit(1)
            set_option_value(key, value)

        for key in remove_option:
            removed = remove_option_key(key)
            if not removed:
                console.print(f"[yellow]Option '{key}' not present; skipping removal.[/yellow]")

        backup = replace_host_block(resolved_target, block, new_patterns, options_list)
        console.print(
            f"[green]Updated Host block {' '.join(new_patterns)} in {resolved_target}.[/green]"
        )
        if backup:
            console.print(f"[dim]Backup saved to {backup}.[/dim]")


__all__ = ["register"]
