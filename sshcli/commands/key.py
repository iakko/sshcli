from __future__ import annotations

import typer

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import datetime
from pathlib import Path
import os


from rich.table import Table

from .common import console
from ..config import DEFAULT_KEYS_DIR

key_app = typer.Typer(help="Manage SSH keys referenced by the CLI.")

_PRIVATE_FORMAT_LOOKUP = {fmt.name.lower(): fmt for fmt in serialization.PrivateFormat}
_PUBLIC_FORMAT_LOOKUP = {fmt.name.lower(): fmt for fmt in serialization.PublicFormat}
_ENCODING_LOOKUP = {enc.name.lower(): enc for enc in serialization.Encoding}

_PRIVATE_FORMAT_OPTIONS = ", ".join(sorted(_PRIVATE_FORMAT_LOOKUP))
_PUBLIC_FORMAT_OPTIONS = ", ".join(sorted(_PUBLIC_FORMAT_LOOKUP))
_ENCODING_OPTIONS = ", ".join(sorted(_ENCODING_LOOKUP))

_OUTPUT_YES = "[green]yes[/green]"
_OUTPUT_NO = "[red]no[/red]"
_OUTPUT_PARTIAL = "[yellow]partial[/yellow]"

def _get_private_key_format(format_str: str) -> serialization.PrivateFormat:
    format_str = format_str.lower()

    if format_str == "pem":
        format_str = "traditionalopenssl"

    selected_format = _PRIVATE_FORMAT_LOOKUP.get(format_str)
    if selected_format is None:
        raise ValueError(f"Unsupported private key format: {format_str}")
    return selected_format

def _get_private_key_encoding(encoding_str: str) -> serialization.Encoding:
    encoding = _ENCODING_LOOKUP.get(encoding_str.lower())
    if encoding is None:
        raise ValueError(f"Unsupported private key encoding: {encoding_str}")
    return encoding

def _get_public_key_format(format_str: str) -> serialization.PublicFormat:
    selected_format = _PUBLIC_FORMAT_LOOKUP.get(format_str.lower())
    if selected_format is None:
        raise ValueError(f"Unsupported public key format: {format_str}")
    return selected_format

def _get_public_key_encoding(encoding_str: str) -> serialization.Encoding:
    encoding = _ENCODING_LOOKUP.get(encoding_str.lower())
    if encoding is None:
        raise ValueError(f"Unsupported public key encoding: {encoding_str}")
    return encoding

def _def_generate_private_bytes(
    private_format: str,
    private_encoding: str,
    private_key: rsa.RSAPrivateKey,
    algorithm: serialization.KeySerializationEncryption,
    verbose: bool,
) -> bytes:
    try:
        selected_private_key_format = _get_private_key_format(private_format)
        selected_private_key_encoding = _get_private_key_encoding(private_encoding)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    try:
        if verbose:
            console.print(f"[blue]Serializing private key with format '{selected_private_key_format}' and encoding '{selected_private_key_encoding}'[/blue]")
        private_bytes = private_key.private_bytes(
            encoding=selected_private_key_encoding,
            format=selected_private_key_format,
            encryption_algorithm=algorithm,
        )
    except ValueError as e:
        console.print(f"[red]Error serializing private key: {e}[/red]")
        raise typer.Exit(code=1)
    
    return private_bytes

def _def_generate_public_bytes(
    public_format: str,
    public_encoding: str,
    public_key: rsa.RSAPublicKey,
    verbose: bool,
) -> bytes:
    try:
        selected_public_format = _get_public_key_format(public_format)
        selected_public_encoding = _get_public_key_encoding(public_encoding)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    try:
        if verbose:
            console.print(f"[blue]Serializing public key with format '{selected_public_format}' and encoding '{selected_public_encoding}'[/blue]")

        public_bytes = public_key.public_bytes(
            encoding=selected_public_encoding,
            format=selected_public_format,
        )
    except ValueError as e:
        console.print(f"[red]Error serializing public key: {e}[/red]")
        raise typer.Exit(code=1)

    return public_bytes

def _pem_header_info(header: str) -> tuple[str, str]:
    """Return (algorithm, format) derived from a PEM header label."""
    normalized = header.upper()
    mapping = {
        "OPENSSH PRIVATE KEY": ("OpenSSH", "OpenSSH"),
        "RSA PRIVATE KEY": ("RSA", "TraditionalOpenSSL"),
        "EC PRIVATE KEY": ("EC", "TraditionalOpenSSL"),
        "DSA PRIVATE KEY": ("DSA", "TraditionalOpenSSL"),
        "PRIVATE KEY": ("PKCS#8", "PKCS8"),
        "PUBLIC KEY": ("SubjectPublicKeyInfo", "SubjectPublicKeyInfo"),
        "RSA PUBLIC KEY": ("RSA", "PKCS1"),
        "EC PUBLIC KEY": ("EC", "SubjectPublicKeyInfo"),
    }
    if normalized in mapping:
        return mapping[normalized]

    algo = header.replace("PRIVATE KEY", "").replace("PUBLIC KEY", "").strip().upper() or "UNKNOWN"
    format_name = "SubjectPublicKeyInfo" if "PUBLIC" in normalized else "TraditionalOpenSSL"
    return algo, format_name

def _describe_key_file(path: Path) -> str:
    """Return algorithm/format/encoding hints for a key file."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return f"error reading ({exc.__class__.__name__})"

    first_line = raw.splitlines()[0].decode("utf-8", errors="ignore").strip() if raw else ""
    if not first_line:
        return "empty file"

    if first_line.startswith("-----BEGIN ") and first_line.endswith("-----"):
        header = first_line[len("-----BEGIN "):-5].strip()
        algorithm, fmt = _pem_header_info(header)
        return f"algorithm={algorithm}, format={fmt}, encoding=PEM"

    if path.suffix == ".pub" and first_line.startswith("ssh-"):
        algorithm = first_line.split()[0]
        return f"algorithm={algorithm}, format=RFC4253, encoding=OpenSSH"

    if raw[:2] == b"\x30\x82":
        return "algorithm=UNKNOWN, format=DER, encoding=DER"

    return "algorithm=UNKNOWN, format=UNKNOWN, encoding=UNKNOWN"

def _collect_file_details(path: Path) -> dict[str, object]:
    info: dict[str, object] = {
        "path": str(path),
        "exists": False,
        "size": "—",
        "mode": "—",
        "mtime": "—",
        "description": "missing",
        "error": "",
    }

    try:
        stat = path.stat()
    except FileNotFoundError:
        return info
    except OSError as exc:
        info["error"] = f"{exc.__class__.__name__}: {exc}"
        info["description"] = "unavailable"
        return info

    info["exists"] = True
    info["size"] = str(stat.st_size)
    info["mode"] = oct(stat.st_mode & 0o777)
    info["mtime"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    info["description"] = _describe_key_file(path)
    return info

def _format_exists(flag: bool) -> str:
    return _OUTPUT_YES if flag else _OUTPUT_NO

@key_app.command("add")
def add_key(
    name: str = typer.Argument(..., help="Name identifier for the key.", metavar="NAME"),
    size: int = typer.Option(2048, help="Size of the key to generate (in bits).", metavar="SIZE"),
    public_exponent: int = typer.Option(65537, help="Public exponent for RSA keys.", metavar="PUBLIC_EXPONENT"),
    path: str = typer.Option(DEFAULT_KEYS_DIR, help="Path to the private key file to add.", metavar="KEYS_PATH"),
    type: str = typer.Option("rsa", help="Type of key to generate (e.g., rsa, ed25519).", metavar="TYPE"),
    password: str = typer.Option("", help="Password for the key, if applicable.", metavar="PASSWORD"),
    comment: str = typer.Option("", help="Comment to associate with the key.", metavar="COMMENT"),
    private_format: str = typer.Option("pem", help=f"Private key format (alias 'pem' -> TraditionalOpenSSL). Options: {_PRIVATE_FORMAT_OPTIONS}.", metavar="PRIVATE_KEY_FORMAT"),
    private_encoding: str = typer.Option("pem", help=f"Private key encoding. Options: {_ENCODING_OPTIONS}.", metavar="PRIVATE_KEY_ENCODING"),
    public_format: str = typer.Option("openssh", help=f"Public key format. Options: {_PUBLIC_FORMAT_OPTIONS}.", metavar="PUBLIC_KEY_FORMAT"),
    public_encoding: str = typer.Option("openssh", help=f"Public key encoding. Options: {_ENCODING_OPTIONS}.", metavar="PUBLIC_KEY_ENCODING"),
    overwrite: bool = typer.Option(False, help="Overwrite existing key files if they exist.", metavar="OVERWRITE"),
    verbose: bool = typer.Option(False, help="Enable verbose output.", metavar="VERBOSE"),
) -> None:
    """Placeholder for adding a new key definition."""
    console.print(f"[yellow][mock] Adding key '{name}' of type '{type}' to path '{path} with comment '{comment}'[/yellow]")
    
    private_key = rsa.generate_private_key(
        public_exponent=public_exponent,
        key_size=size
    )

    algorithm = serialization.NoEncryption()
    if password:
        algorithm = serialization.BestAvailableEncryption(password.encode())

    private_bytes: bytes = _def_generate_private_bytes(
        private_format,
        private_encoding,
        private_key,
        algorithm,
        verbose
    )

    public_bytes: bytes = _def_generate_public_bytes(
        public_format,
        public_encoding,
        private_key.public_key(),
        verbose,
    ) + (b" " + comment.encode()) if comment else b""

    key_path = Path(path).expanduser()
    
    console.print(f"[blue]Ensuring key path exists at '{key_path}'[/blue]")
    
    key_path.mkdir(parents=True, exist_ok=True)

    private_key_file = key_path / f"{name}"
    public_key_file = key_path / f"{name}.pub"

    if not overwrite:
        conflicts = [str(file) for file in (private_key_file, public_key_file) if file.exists()]
        if conflicts:
            console.print(
                "[red]Key file(s) already exist: "
                + ", ".join(conflicts)
                + ". Use --overwrite to replace them.[/red]"
            )
            raise typer.Exit(code=1)

    with open(private_key_file, "wb") as f:
        f.write(private_bytes)
    os.chmod(private_key_file, 0o600)

    with open(public_key_file, "wb") as f:
        f.write(public_bytes)
    os.chmod(public_key_file, 0o644)

@key_app.command("list")
def list_keys(
        path: str = typer.Option(DEFAULT_KEYS_DIR, help="Path to the private key file to add.", metavar="KEYS_PATH"),
    ) -> None:
    """List keys and report whether private/public pairs exist."""
    console.print(f"[yellow][mock] Listing keys in path '{path}'[/yellow]")

    key_path = _validated_keys_path(path)
    files = _key_files_in_path(key_path)
    if not files:
        console.print(f"[blue]No keys found in '{path}'.[/blue]")
        return

    pairs = _detect_key_pairs(files)
    table = _build_key_table(key_path, pairs)
    console.print(table)

@key_app.command("show")
def show_key(
    name: str = typer.Argument(..., help="Base name of the key to inspect.", metavar="NAME"),
    path: str = typer.Option(DEFAULT_KEYS_DIR, help="Path containing SSH key files.", metavar="KEYS_PATH"),
) -> None:
    """Display a detailed breakdown for a specific key."""
    console.print(f"[yellow][mock] Showing key '{name}' in path '{path}'[/yellow]")

    key_path = _validated_keys_path(path)
    priv_path = key_path / name
    pub_path = key_path / f"{name}.pub"

    priv_info = _collect_file_details(priv_path)
    pub_info = _collect_file_details(pub_path)

    priv_exists = bool(priv_info["exists"])
    pub_exists = bool(pub_info["exists"])

    if not priv_exists and not pub_exists:
        console.print(f"[red]No key named '{name}' found in '{path}'.[/red]")
        raise typer.Exit(code=1)

    table = Table(title=f"Key '{name}' details", show_header=True)
    table.add_column("Attribute", style="bold")
    table.add_column("Private", style="cyan")
    table.add_column("Public", style="green")

    def _path_display(info: dict[str, object]) -> str:
        suffix = "" if info["exists"] else " (missing)"
        error = f" [red]{info['error']}[/red]" if info.get("error") else ""
        return f"{info['path']}{suffix}{error}"

    def _value(info: dict[str, object], key: str) -> str:
        value = info.get(key, "—")
        return value if isinstance(value, str) else str(value)

    table.add_row("Path", _path_display(priv_info), _path_display(pub_info))
    table.add_row("Exists", _format_exists(priv_exists), _format_exists(pub_exists))
    table.add_row("Size (bytes)", _value(priv_info, "size"), _value(pub_info, "size"))
    table.add_row("Permissions", _value(priv_info, "mode"), _value(pub_info, "mode"))
    table.add_row("Modified", _value(priv_info, "mtime"), _value(pub_info, "mtime"))
    table.add_row("Key Info", _value(priv_info, "description"), _value(pub_info, "description"))

    error_private = _value(priv_info, "error") if priv_info.get("error") else "—"
    error_public = _value(pub_info, "error") if pub_info.get("error") else "—"
    table.add_row("Errors", error_private, error_public)

    pair_status = _OUTPUT_YES if priv_exists and pub_exists else _OUTPUT_PARTIAL
    table.add_row("Pair Complete", pair_status, pair_status)

    console.print(table)


def _validated_keys_path(path: str) -> Path:
    key_path = Path(path).expanduser()
    if not key_path.exists() or not key_path.is_dir():
        console.print(f"[red]Keys path '{path}' does not exist or is not a directory.[/red]")
        raise typer.Exit(code=1)
    return key_path


def _key_files_in_path(key_path: Path) -> list[Path]:
    return [p for p in key_path.iterdir() if p.is_file()]


def _detect_key_pairs(files: list[Path]) -> dict[str, dict[str, bool]]:
    pairs: dict[str, dict[str, bool]] = {}
    for file_path in files:
        name = file_path.name
        is_public = name.endswith(".pub")
        base_name = name[:-4] if is_public else name
        entry = pairs.setdefault(base_name, {"priv": False, "pub": False})
        entry["pub" if is_public else "priv"] = True
    return pairs


def _build_key_table(key_path: Path, pairs: dict[str, dict[str, bool]]) -> Table:
    table = Table(title=f"Keys in {key_path}", show_header=True)
    table.add_column("Path", style="cyan", no_wrap=True)
    table.add_column("Pair Exists", justify="center", style="bold")
    table.add_column("Implicit Infos")

    for base_name in sorted(pairs):
        entry = pairs[base_name]
        priv_path = key_path / base_name
        pub_path = key_path / f"{base_name}.pub"

        pair_exists = entry["priv"] and entry["pub"]
        pair_status = _OUTPUT_YES if pair_exists else _OUTPUT_NO

        details: list[str] = []
        if entry["priv"]:
            details.append(f"private: {priv_path.name} ({_describe_key_file(priv_path)})")
        else:
            details.append("missing private key")

        if entry["pub"]:
            details.append(f"public: {pub_path.name} ({_describe_key_file(pub_path)})")
        else:
            details.append("missing .pub key")

        table.add_row(str(priv_path if entry["priv"] else pub_path), pair_status, ", ".join(details))
    return table

def register(app: typer.Typer) -> None:
    app.add_typer(key_app, name="key")


__all__ = ["register"]
