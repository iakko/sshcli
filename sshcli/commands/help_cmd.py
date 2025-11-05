from __future__ import annotations

import typer
from rich import box
from rich.table import Table

from .common import console


def register(app: typer.Typer) -> None:
    @app.command("help")
    def help_command():
        """List available commands."""
        table = Table(box=box.SIMPLE, show_header=True, show_lines=False)
        table.add_column("Command", style="bold cyan")
        table.add_column("Description")

        command_infos = sorted(
            (info for info in app.registered_commands if info.callback is not None),
            key=lambda info: info.name or "",
        )
        for info in command_infos:
            name = info.name or ""
            description = info.help or (info.callback.__doc__ or "").strip()
            table.add_row(name, description)

        console.print(table)
        console.print("Use `sshcli <host>` to show a host block quickly (add --details for all matches).")
        console.print("Run `sshcli COMMAND --help` for details on a specific command.")


__all__ = ["register"]
