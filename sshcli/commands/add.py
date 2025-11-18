from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import typer

from .. import config as config_module
from ..models import HostBlock
from .common import console, parse_option_entry


def _build_options(
    hostname: str,
    user: str,
    port: int,
    option_entries: List[str],
) -> List[Tuple[str, str]]:
    options: List[Tuple[str, str]] = []

    if hostname:
        options.append(("HostName", hostname))
    if user:
        options.append(("User", user))
    if port:
        options.append(("Port", str(port)))

    for entry in option_entries:
        try:
            options.append(parse_option_entry(entry))
        except typer.BadParameter:
            console.print(
                f"[red]Options must be supplied as KEY=VALUE (received '{entry}').[/red]"
            )
            raise typer.Exit(1)
    return options


def _load_existing_blocks(resolved_target: Path) -> List[HostBlock]:
    if not resolved_target.exists():
        return []
    return [
        block
        for block in config_module.parse_config_files([resolved_target])
        if block.source_file == resolved_target
    ]


def _guard_duplicates(
    patterns: List[str],
    existing_blocks: List[HostBlock],
    force: bool,
) -> None:
    duplicate = next((block for block in existing_blocks if block.patterns == patterns), None)
    if duplicate and not force:
        console.print(
            f"[red]Host block for patterns {' '.join(patterns)} already exists at "
            f"{duplicate.source_file}:{duplicate.lineno}. Use --force to append anyway.[/red]"
        )
        raise typer.Exit(code=1)


def register(app: typer.Typer) -> None:
    @app.command("add")
    def add_host(
        patterns: List[str] = typer.Argument(..., help="Host pattern(s) to add (space separated).", metavar="PATTERN"),
        hostname: str = typer.Option("", "--hostname", "-H", help="Set the HostName option."),
        user: str = typer.Option("", "--user", "-u", help="Set the User option."),
        port: int = typer.Option(0, "--port", "-p", help="Set the Port option."),
        option: List[str] = typer.Option(
            [],
            "--option",
            "-o",
            help="Additional option in KEY=VALUE form. Repeat for multiple options.",
        ),
        target: Optional[Path] = typer.Option(
            None,
            "--target",
            "-t",
            help="SSH config file to modify.",
            rich_help_panel="Targeting",
        ),
        force: bool = typer.Option(
            False,
            "--force",
            help="Append even if a Host block with identical patterns already exists.",
        ),
    ):
        """Append a new Host block to an SSH config."""
        if not patterns:
            raise typer.BadParameter("At least one host pattern is required.")

        if target is None:
            target = config_module.default_config_path()

        resolved_target = target.expanduser()
        options = _build_options(hostname, user, port, option)
        existing_blocks = _load_existing_blocks(resolved_target)
        _guard_duplicates(patterns, existing_blocks, force)

        backup = config_module.append_host_block(resolved_target, patterns, options)
        console.print(
            f"[green]Added Host block for {' '.join(patterns)} to {resolved_target}.[/green]"
        )
        if backup:
            console.print(f"[dim]Backup saved to {backup}.[/dim]")


__all__ = ["register"]
