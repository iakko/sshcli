from __future__ import annotations

import sys
from typing import List, Sequence

import typer
from typer.main import get_command

from .commands import register_commands
from .config import DEFAULT_CONFIG_PATHS, DEFAULT_INCLUDE_FALLBACKS

app = typer.Typer(help="A tiny, modern SSH config explorer.")
register_commands(app)


def _command_names() -> List[str]:
    return [
        info.name
        for info in app.registered_commands
        if info.name is not None
    ]


def _rewrite_default_invocation(args: Sequence[str]) -> List[str]:
    if not args:
        return list(args)

    first, *rest = args
    if first.startswith("-") or first in _command_names():
        return list(args)

    details = False
    forwarded: List[str] = []
    for value in rest:
        if value == "--details":
            details = True
        else:
            forwarded.append(value)

    show_args = ["show", first]
    if details:
        show_args.append("--details")
    show_args.extend(forwarded)
    return show_args


def run(argv: Sequence[str] | None = None) -> None:
    """Entry point that supports `sshcli <host>` shorthand."""
    command = get_command(app)
    if argv is None:
        argv = tuple(sys.argv[1:])
    rewritten = _rewrite_default_invocation(list(argv))
    try:
        command.main(args=rewritten, prog_name="sshcli", standalone_mode=False)
    except SystemExit as exc:  # pragma: no cover - passthrough
        raise exc


__all__ = ["app", "run", "DEFAULT_CONFIG_PATHS", "DEFAULT_INCLUDE_FALLBACKS"]
