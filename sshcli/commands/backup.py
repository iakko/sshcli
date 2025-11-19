from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import click
import typer
from rich import box
from rich.table import Table

from .. import config as config_module
from sshcore import backups as backups_core
from .common import console
from typer.main import get_command

backup_app = typer.Typer(help="Inspect, restore, and prune SSH config backups.")


def _resolve_target(target: Optional[Path]) -> Path:
    base = target or backups_core.get_default_config_path()
    return base.expanduser()


def _format_timestamp(dt: Optional[datetime]) -> str:
    if dt is None:
        return "unknown"
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _format_age(dt: Optional[datetime]) -> str:
    if dt is None:
        return "unknown"
    now = datetime.now(tz=timezone.utc)
    delta = now - dt
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    if months < 12:
        return f"{months}mo ago"
    years = months // 12
    return f"{years}y ago"


def _format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size / 1024:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


@backup_app.command("list")
def list_backups(
    target: Optional[Path] = typer.Option(
        None,
        "--target",
        "-t",
        help="SSH config whose backups should be listed.",
        rich_help_panel="Targeting",
    ),
):
    """Display available backups for the selected SSH config."""
    resolved_target = _resolve_target(target)
    backups = backups_core.discover_backups(resolved_target)
    if not backups:
        console.print("[yellow]No backups found for the selected config.[/yellow]")
        raise typer.Exit(code=0)

    table = Table(box=box.SIMPLE_HEAVY, show_lines=False)
    table.add_column("Stamp", style="bold cyan")
    table.add_column("Created", style="green")
    table.add_column("Age", style="magenta")
    table.add_column("Size", justify="right")
    table.add_column("Path", overflow="fold")

    for entry in backups:
        table.add_row(
            entry.stamp,
            _format_timestamp(entry.timestamp),
            _format_age(entry.timestamp),
            _format_size(entry.size),
            str(entry.path),
        )

    console.print(table)


@backup_app.command("restore")
def restore_backup(
    identifier: str = typer.Argument(
        ...,
        help="Backup stamp or file name to restore from.",
        metavar="STAMP|NAME",
    ),
    target: Optional[Path] = typer.Option(
        None,
        "--target",
        "-t",
        help="SSH config to restore.",
        rich_help_panel="Targeting",
    ),
    create_backup: bool = typer.Option(
        True,
        "--backup-current/--no-backup-current",
        help="Save a backup of the current config before restoring.",
    ),
):
    """Restore the config from a specific backup."""
    resolved_target = _resolve_target(target)
    backups = backups_core.discover_backups(resolved_target)
    if not backups:
        console.print("[red]No backups available to restore.[/red]")
        raise typer.Exit(code=1)

    entry = backups_core.select_backup(identifier, backups)
    if entry is None:
        console.print(f"[red]Backup '{identifier}' not found.[/red]")
        raise typer.Exit(code=1)

    resolved_target.parent.mkdir(parents=True, exist_ok=True)

    if create_backup and resolved_target.exists():
        backup_path = backups_core.create_backup(resolved_target)
        if backup_path is not None:
            console.print(f"[dim]Current config backed up to {backup_path}.[/dim]")

    shutil.copy2(entry.path, resolved_target)
    console.print(
        f"[green]Restored {resolved_target} from backup {entry.path.name}.[/green]"
    )


@backup_app.command("prune")
def prune_backups(
    target: Optional[Path] = typer.Option(
        None,
        "--target",
        "-t",
        help="SSH config whose backups should be pruned.",
        rich_help_panel="Targeting",
    ),
    keep: Optional[int] = typer.Option(
        None,
        "--keep",
        "-k",
        help="Keep the most recent N backups and remove the rest.",
    ),
    before: Optional[str] = typer.Option(
        None,
        "--before",
        help="Remove backups created before the given stamp (YYYYMMDDHHMMSS).",
        metavar="STAMP",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show which backups would be deleted without removing them.",
    ),
):
    """Delete old backups by count or timestamp."""
    resolved_target = _resolve_target(target)
    cutoff = _validate_prune_arguments(keep, before)
    backups = backups_core.discover_backups(resolved_target)
    if not backups:
        console.print("[yellow]No backups found.[/yellow]")
        raise typer.Exit(code=0)

    removal_paths = _select_backups_to_remove(backups, keep, cutoff)
    if not removal_paths:
        console.print("[green]Nothing to prune.[/green]")
        raise typer.Exit(code=0)

    if dry_run:
        console.print("[yellow]Backups that would be removed:[/yellow]")
        for path in sorted(removal_paths):
            console.print(f"  - {path}")
        raise typer.Exit(code=0)

    removed = _delete_backups(removal_paths)
    if removed:
        console.print("[green]Removed backups:[/green]")
        for path in removed:
            console.print(f"  - {path}")
    else:
        console.print("[yellow]No backups were removed.[/yellow]")


def _validate_prune_arguments(keep: Optional[int], before: Optional[str]) -> Optional[datetime]:
    if keep is None and before is None:
        console.print("[red]Specify --keep and/or --before to prune backups.[/red]")
        raise typer.Exit(code=1)

    if keep is not None and keep < 0:
        console.print("[red]--keep must be zero or greater.[/red]")
        raise typer.Exit(code=1)

    if before is None:
        return None
    cutoff = backups_core.parse_backup_timestamp(before)
    if cutoff is None:
        console.print("[red]--before must be in YYYYMMDDHHMMSS format.[/red]")
        raise typer.Exit(code=1)
    return cutoff


def _select_backups_to_remove(
    backups: List[backups_core.BackupEntry],
    keep: Optional[int],
    cutoff: Optional[datetime],
) -> List[Path]:
    candidates: List[backups_core.BackupEntry] = []

    if keep is not None and keep < len(backups):
        candidates.extend(backups[keep:])

    if cutoff is not None:
        for entry in backups:
            if entry.timestamp is not None and entry.timestamp < cutoff:
                candidates.append(entry)

    unique_paths = {entry.path for entry in candidates}
    return sorted(unique_paths)


def _delete_backups(paths: List[Path]) -> List[Path]:
    removed: List[Path] = []
    for path in paths:
        try:
            path.unlink()
            removed.append(path)
        except OSError as exc:
            console.print(f"[red]Failed to delete {path}: {exc}[/red]")
    return removed


def register(app: typer.Typer) -> None:
    app.add_typer(backup_app, name="backup")


@backup_app.command("help")
def backup_help() -> None:
    """Show help for the backup command group."""
    command = get_command(backup_app)
    ctx = click.Context(command, info_name="backup")
    typer.echo(command.get_help(ctx))


__all__ = ["register"]
