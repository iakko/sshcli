from __future__ import annotations

from pathlib import Path

import typer
from rich import box
from rich.table import Table

from sshcore import settings as settings_module
from .common import console


def register(app: typer.Typer) -> None:
    source_app = typer.Typer(help="Manage which SSH config files sshcli reads.")

    @source_app.command("list")
    def list_sources() -> None:
        """Show configured config sources and their status."""
        settings = settings_module.load_settings()
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Path", overflow="fold")
        table.add_column("Enabled", justify="center")
        table.add_column("Exists", justify="center")
        table.add_column("Default", justify="center")

        for source in settings.config_sources:
            path = Path(source.path).expanduser()
            table.add_row(
                str(path),
                "yes" if source.enabled else "no",
                "yes" if path.is_file() else "no",
                "yes" if source.is_default else "",
            )

        console.print(table)

    @source_app.command("add")
    def add_source(
        path: Path = typer.Argument(..., metavar="PATH", help="SSH config file to add."),
        enable: bool = typer.Option(
            True,
            "--enable/--disable",
            help="Whether the source should be enabled immediately.",
        ),
        make_default: bool = typer.Option(
            False,
            "--default/--no-default",
            help="Whether this source should become the default for single-target commands.",
        ),
    ) -> None:
        """Add or update a config source in sshcli.json."""
        path = path.expanduser()
        settings_module.add_or_update_source(path, enabled=enable, make_default=make_default)
        console.print(
            f"[green]Config source '{path}' {'enabled' if enable else 'disabled'}"
            + (" and set as default" if make_default else "")
            + ".[/green]"
        )

    @source_app.command("enable")
    def enable_source(
        path: Path = typer.Argument(..., metavar="PATH", help="Config source to enable."),
    ) -> None:
        """Enable a config source without changing others."""
        try:
            settings_module.set_source_enabled(path, True)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Enabled config source '{path}'.[/green]")

    @source_app.command("disable")
    def disable_source(
        path: Path = typer.Argument(..., metavar="PATH", help="Config source to disable."),
    ) -> None:
        """Disable a config source so it is ignored."""
        try:
            settings_module.set_source_enabled(path, False)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Disabled config source '{path}'.[/green]")

    @source_app.command("remove")
    def remove_source(
        path: Path = typer.Argument(..., metavar="PATH", help="Config source to remove."),
    ) -> None:
        """Remove a config source definition entirely."""
        try:
            settings_module.remove_source(path)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Removed config source '{path}'.[/green]")

    @source_app.command("reset")
    def reset_sources() -> None:
        """Reset config sources back to the defaults."""
        settings_module.reset_sources()
        console.print("[green]Config sources reset to defaults.[/green]")

    @source_app.command("default")
    def set_default(
        path: Path = typer.Argument(..., metavar="PATH", help="Config source to use as default."),
    ) -> None:
        """Mark one config source as the default for commands needing a single file."""
        try:
            settings_module.set_default_source(path)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Set default config source to '{path}'.[/green]")

    app.add_typer(source_app, name="config-source")


__all__ = ["register"]
