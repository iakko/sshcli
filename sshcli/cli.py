from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version as pkg_version
from typing import List, Sequence

import typer
from typer.main import get_command

from click.exceptions import UsageError

from .commands import register_commands
from .config import DEFAULT_INCLUDE_FALLBACKS
from .commands.common import console

app = typer.Typer(help="A tiny, modern SSH config explorer.")
register_commands(app)


def _current_version() -> str:
    for dist_name in ("ixlab-sshcli", "sshcli"):
        try:
            return pkg_version(dist_name)
        except PackageNotFoundError:
            continue
    return "unknown"


@app.callback(invoke_without_command=True)
def _root_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the sshcli version and exit.",
        is_eager=True,
    ),
) -> None:
    if version:
        console.print(f"sshcli {_current_version()}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None and not ctx.args:
        console.print(ctx.get_help())
        raise typer.Exit()


def _command_names() -> List[str]:
    command_names = [
        info.name
        for info in app.registered_commands
        if info.name is not None
    ]
    group_names = [
        info.name
        for info in app.registered_groups
        if info.name is not None
    ]
    return command_names + group_names


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
    except UsageError as exc:
        message = exc.format_message()
        if message:
            console.print(f"[red]{message}[/red]")
        if exc.ctx is not None:
            console.print()
            console.print(exc.ctx.get_help())
        return exc.exit_code or 2

__all__ = ["app", "run", "DEFAULT_INCLUDE_FALLBACKS"]
