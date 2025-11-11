from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import typer

from .. import config as config_module
from ..models import HostBlock
from .common import console, matching_blocks, parse_option_entry


def _resolve_edit_target(target: Path) -> Path:
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


def _select_block_for_edit(name: str, blocks: List[HostBlock], target: Path) -> HostBlock:
    _, matched = matching_blocks(name, blocks)
    if not matched:
        console.print(f"[yellow]No host block matches '{name}' in {target}.[/yellow]")
        raise typer.Exit(1)
    if len(matched) > 1:
        console.print("[red]Multiple host blocks match. Refine your selection:[/red]")
        for block in matched:
            console.print(
                f"  - {' '.join(block.patterns)} ({block.source_file}:{block.lineno})"
            )
        raise typer.Exit(1)
    return matched[0]


def _compute_patterns(set_pattern: Optional[List[str]], block: HostBlock) -> List[str]:
    if set_pattern is not None:
        if not set_pattern:
            console.print("[red]At least one pattern is required when replacing patterns.[/red]")
            raise typer.Exit(1)
        return list(set_pattern)
    return list(block.patterns)


def _initial_options(
    block: HostBlock,
    clear_options: bool,
) -> List[Tuple[str, str]]:
    if clear_options:
        return []
    return list(block.options.items())


def _set_option(options: List[Tuple[str, str]], key: str, value: str) -> None:
    lower = key.lower()
    for idx, (existing_key, _) in enumerate(options):
        if existing_key.lower() == lower:
            options[idx] = (existing_key, value)
            return
    options.append((key, value))


def _remove_option(options: List[Tuple[str, str]], key: str) -> bool:
    lower = key.lower()
    for idx, (existing_key, _) in enumerate(options):
        if existing_key.lower() == lower:
            del options[idx]
            return True
    return False


def _apply_option_updates(
    options: List[Tuple[str, str]],
    hostname: Optional[str],
    user: Optional[str],
    port: Optional[int],
    extra_options: List[str],
) -> None:
    if hostname is not None:
        if hostname == "":
            _remove_option(options, "HostName")
        else:
            _set_option(options, "HostName", hostname)

    if user is not None:
        if user == "":
            _remove_option(options, "User")
        else:
            _set_option(options, "User", user)

    if port is not None:
        _set_option(options, "Port", str(port))

    for entry in extra_options:
        try:
            key, value = parse_option_entry(entry)
        except typer.BadParameter:
            console.print(
                f"[red]Options must be supplied as KEY=VALUE (received '{entry}').[/red]"
            )
            raise typer.Exit(1)
        _set_option(options, key, value)


def _remove_declared_options(options: List[Tuple[str, str]], remove_option: List[str]) -> None:
    for key in remove_option:
        removed = _remove_option(options, key)
        if not removed:
            console.print(f"[yellow]Option '{key}' not present; skipping removal.[/yellow]")


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
        resolved_target = _resolve_edit_target(target)
        blocks = _load_blocks_for_target(resolved_target)
        block = _select_block_for_edit(name, blocks, resolved_target)
        new_patterns = _compute_patterns(set_pattern, block)
        options_list = _initial_options(block, clear_options)

        _apply_option_updates(options_list, hostname, user, port, option)
        _remove_declared_options(options_list, remove_option)

        backup = config_module.replace_host_block(resolved_target, block, new_patterns, options_list)
        console.print(
            f"[green]Updated Host block {' '.join(new_patterns)} in {resolved_target}.[/green]"
        )
        if backup:
            console.print(f"[dim]Backup saved to {backup}.[/dim]")


__all__ = ["register"]
