from __future__ import annotations

import typer

from . import (
    add,
    backup,
    config_source,
    copy,
    edit,
    find,
    help_cmd,
    key,
    list as list_cmd,
    remove,
    show,
    tag,
)


def register_commands(app: typer.Typer) -> None:
    """Register all CLI commands with the Typer app."""
    add.register(app)
    backup.register(app)
    copy.register(app)
    config_source.register(app)
    edit.register(app)
    find.register(app)
    help_cmd.register(app)
    key.register(app)
    list_cmd.register(app)
    remove.register(app)
    show.register(app)
    tag.register(app)


__all__ = ["register_commands"]
