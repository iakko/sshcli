from __future__ import annotations

import typer
from rich.table import Table

from ..config import DEFAULT_KEYS_DIR
from sshcore import keys as core_keys
from .common import console

key_app = typer.Typer(help="Manage SSH keys referenced by the CLI.")

_PRIVATE_FORMAT_OPTIONS = ", ".join(core_keys.PRIVATE_FORMAT_OPTIONS)
_PUBLIC_FORMAT_OPTIONS = ", ".join(core_keys.PUBLIC_FORMAT_OPTIONS)
_ENCODING_OPTIONS = ", ".join(core_keys.ENCODING_OPTIONS)

_OUTPUT_YES = "[green]yes[/green]"
_OUTPUT_NO = "[red]no[/red]"
_OUTPUT_PARTIAL = "[yellow]partial[/yellow]"


@key_app.command("add")
def add_key(
    name: str = typer.Argument(..., help="Name identifier for the key.", metavar="NAME"),
    size: int = typer.Option(2048, help="Size of the key to generate (in bits).", metavar="SIZE"),
    public_exponent: int = typer.Option(
        65537, help="Public exponent for RSA keys.", metavar="PUBLIC_EXPONENT"
    ),
    path: str = typer.Option(
        DEFAULT_KEYS_DIR,
        help="Path to the private key file to add.",
        metavar="KEYS_PATH",
    ),
    key_type: str = typer.Option(
        "rsa",
        "--type",
        help="Type of key to generate (currently only RSA).",
        metavar="TYPE",
    ),
    password: str = typer.Option("", help="Password for the key, if applicable.", metavar="PASSWORD"),
    comment: str = typer.Option("", help="Comment to associate with the key.", metavar="COMMENT"),
    private_format: str = typer.Option(
        "pem",
        help=f"Private key format (alias 'pem' -> TraditionalOpenSSL). Options: {_PRIVATE_FORMAT_OPTIONS}.",
        metavar="PRIVATE_KEY_FORMAT",
    ),
    private_encoding: str = typer.Option(
        "pem",
        help=f"Private key encoding. Options: {_ENCODING_OPTIONS}.",
        metavar="PRIVATE_KEY_ENCODING",
    ),
    public_format: str = typer.Option(
        "openssh",
        help=f"Public key format. Options: {_PUBLIC_FORMAT_OPTIONS}.",
        metavar="PUBLIC_KEY_FORMAT",
    ),
    public_encoding: str = typer.Option(
        "openssh",
        help=f"Public key encoding. Options: {_ENCODING_OPTIONS}.",
        metavar="PUBLIC_KEY_ENCODING",
    ),
    overwrite: bool = typer.Option(
        False, help="Overwrite existing key files if they exist.", metavar="OVERWRITE"
    ),
    verbose: bool = typer.Option(False, help="Enable verbose output.", metavar="VERBOSE"),
) -> None:
    """Generate and store a new key pair."""
    try:
        result = core_keys.generate_key_pair(
            name=name,
            size=size,
            public_exponent=public_exponent,
            path=path,
            key_type=key_type,
            password=password,
            comment=comment,
            private_format=private_format,
            private_encoding=private_encoding,
            public_format=public_format,
            public_encoding=public_encoding,
            overwrite=overwrite,
            verbose=verbose,
        )
    except core_keys.KeyOperationError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    console.print(
        f"[green]Generated key '{name}' (Private: '{result.private_path}', Public: '{result.public_path}')[/green]"
    )


@key_app.command("list")
def list_keys(
    path: str = typer.Option(DEFAULT_KEYS_DIR, help="Path containing SSH key files.", metavar="KEYS_PATH"),
) -> None:
    """List keys and report whether private/public pairs exist."""
    try:
        summaries = core_keys.list_key_pairs(path)
    except core_keys.KeyOperationError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if not summaries:
        console.print(f"[blue]No keys found in '{path}'.[/blue]")
        return

    table = Table(title=f"Keys in {path}", show_header=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Pair Exists", justify="center", style="bold")
    table.add_column("Implicit Infos")

    for summary in summaries:
        table.add_row(
            summary.base_name,
            _OUTPUT_YES if summary.pair_complete else _OUTPUT_NO,
            _format_summary_details(summary),
        )

    console.print(table)


@key_app.command("show")
def show_key(
    name: str = typer.Argument(..., help="Base name of the key to inspect.", metavar="NAME"),
    path: str = typer.Option(DEFAULT_KEYS_DIR, help="Path containing SSH key files.", metavar="KEYS_PATH"),
) -> None:
    """Display a detailed breakdown for a specific key."""
    try:
        details = core_keys.describe_key(name, path)
    except core_keys.KeyOperationError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    table = Table(title=f"Key '{name}' details", show_header=True)
    table.add_column("Attribute", style="bold")
    table.add_column("Private", style="cyan")
    table.add_column("Public", style="green")

    table.add_row("Path", _format_path(details.private_info), _format_path(details.public_info))
    table.add_row("Exists", _format_exists(details.private_info), _format_exists(details.public_info))
    table.add_row("Size (bytes)", _format_size(details.private_info), _format_size(details.public_info))
    table.add_row("Permissions", _format_mode(details.private_info), _format_mode(details.public_info))
    table.add_row("Modified", _format_time(details.private_info), _format_time(details.public_info))
    table.add_row("Key Info", _format_desc(details.private_info), _format_desc(details.public_info))
    table.add_row("Errors", _format_error(details.private_info), _format_error(details.public_info))

    pair_status = _OUTPUT_YES if details.pair_complete else _OUTPUT_PARTIAL
    table.add_row("Pair Complete", pair_status, pair_status)

    console.print(table)


def _format_summary_details(summary: core_keys.KeyPairSummary) -> str:
    parts: list[str] = []
    if summary.private_info and summary.private_info.exists:
        parts.append(f"private: {summary.private_info.path.name} ({summary.private_info.description})")
    else:
        parts.append("missing private key")

    if summary.public_info and summary.public_info.exists:
        parts.append(f"public: {summary.public_info.path.name} ({summary.public_info.description})")
    else:
        parts.append("missing .pub key")
    return ", ".join(parts)


def _format_path(info: core_keys.KeyFileInfo | None) -> str:
    if not info:
        return "—"
    suffix = "" if info.exists else " (missing)"
    error = f" [red]{info.error}[/red]" if info.error else ""
    return f"{info.path}{suffix}{error}"


def _format_exists(info: core_keys.KeyFileInfo | None) -> str:
    if info and info.exists:
        return _OUTPUT_YES
    if info:
        return _OUTPUT_NO
    return "—"


def _format_size(info: core_keys.KeyFileInfo | None) -> str:
    return str(info.size) if info and info.size is not None else "—"


def _format_mode(info: core_keys.KeyFileInfo | None) -> str:
    return oct(info.mode) if info and info.mode is not None else "—"


def _format_time(info: core_keys.KeyFileInfo | None) -> str:
    return info.modified_at.isoformat() if info and info.modified_at else "—"


def _format_desc(info: core_keys.KeyFileInfo | None) -> str:
    return info.description if info else "—"


def _format_error(info: core_keys.KeyFileInfo | None) -> str:
    return info.error if info and info.error else "—"


def register(app: typer.Typer) -> None:
    app.add_typer(key_app, name="key")


__all__ = ["register"]
