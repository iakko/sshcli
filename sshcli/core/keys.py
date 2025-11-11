from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class KeyOperationError(RuntimeError):
    """Raised when a key operation cannot be completed."""

_PRIVATE_FORMAT_LOOKUP = {fmt.name.lower(): fmt for fmt in serialization.PrivateFormat}
_PUBLIC_FORMAT_LOOKUP = {fmt.name.lower(): fmt for fmt in serialization.PublicFormat}
_ENCODING_LOOKUP = {enc.name.lower(): enc for enc in serialization.Encoding}

PRIVATE_FORMAT_OPTIONS: tuple[str, ...] = tuple(sorted(_PRIVATE_FORMAT_LOOKUP))
PUBLIC_FORMAT_OPTIONS: tuple[str, ...] = tuple(sorted(_PUBLIC_FORMAT_LOOKUP))
ENCODING_OPTIONS: tuple[str, ...] = tuple(sorted(_ENCODING_LOOKUP))


@dataclass
class KeyFileInfo:
    path: Path
    exists: bool
    size: Optional[int]
    mode: Optional[int]
    modified_at: Optional[datetime]
    description: str
    error: Optional[str] = None


@dataclass
class KeyPairSummary:
    base_name: str
    private_info: Optional[KeyFileInfo]
    public_info: Optional[KeyFileInfo]

    @property
    def pair_complete(self) -> bool:
        return bool(
            self.private_info
            and self.private_info.exists
            and self.public_info
            and self.public_info.exists
        )


@dataclass
class KeyDetails:
    name: str
    private_info: Optional[KeyFileInfo]
    public_info: Optional[KeyFileInfo]

    @property
    def pair_complete(self) -> bool:
        return bool(
            self.private_info
            and self.private_info.exists
            and self.public_info
            and self.public_info.exists
        )


@dataclass
class KeyGenerationResult:
    private_path: Path
    public_path: Path


def generate_key_pair(
    *,
    name: str,
    size: int,
    public_exponent: int,
    path: str,
    key_type: str,
    password: str,
    comment: str,
    private_format: str,
    private_encoding: str,
    public_format: str,
    public_encoding: str,
    overwrite: bool
) -> KeyGenerationResult:
    if key_type.lower() != "rsa":
        raise KeyOperationError("Only RSA keys are supported at this time.")

    key_path = Path(path).expanduser()
    _ensure_directory(key_path)

    private_key = rsa.generate_private_key(
        public_exponent=public_exponent,
        key_size=size,
    )

    algorithm: serialization.KeySerializationEncryption
    if password:
        algorithm = serialization.BestAvailableEncryption(password.encode())
    else:
        algorithm = serialization.NoEncryption()

    private_bytes = _serialize_private_key(
        private_key,
        private_format,
        private_encoding,
        algorithm,
    )
    public_bytes = _serialize_public_key(
        private_key.public_key(),
        public_format,
        public_encoding,
    )
    if comment:
        public_bytes += b" " + comment.encode()

    private_file = key_path / name
    public_file = key_path / f"{name}.pub"

    if not overwrite:
        conflicts = [str(file) for file in (private_file, public_file) if file.exists()]
        if conflicts:
            raise KeyOperationError(
                "Key file(s) already exist: "
                + ", ".join(conflicts)
                + ". Use overwrite to replace them."
            )

    private_file.write_bytes(private_bytes)
    os_chmod(private_file, 0o600)

    public_file.write_bytes(public_bytes)
    os_chmod(public_file, 0o644)

    return KeyGenerationResult(private_path=private_file, public_path=public_file)


def list_key_pairs(path: str) -> List[KeyPairSummary]:
    key_path = _validated_keys_path(path)
    files = [p for p in key_path.iterdir() if p.is_file()]
    if not files:
        return []

    pairs: dict[str, dict[str, Path]] = {}
    for file_path in files:
        is_public = file_path.name.endswith(".pub")
        base_name = file_path.name[:-4] if is_public else file_path.name
        entry = pairs.setdefault(base_name, {})
        entry["pub" if is_public else "priv"] = file_path

    summaries: List[KeyPairSummary] = []
    for base_name in sorted(pairs):
        entry = pairs[base_name]
        priv_path = entry.get("priv", key_path / base_name)
        pub_path = entry.get("pub", key_path / f"{base_name}.pub")
        priv_info = _collect_file_details(priv_path)
        pub_info = _collect_file_details(pub_path)
        summaries.append(
            KeyPairSummary(
                base_name=base_name,
                private_info=priv_info,
                public_info=pub_info,
            )
        )
    return summaries


def describe_key(name: str, path: str) -> KeyDetails:
    key_path = _validated_keys_path(path)
    priv_path = key_path / name
    pub_path = key_path / f"{name}.pub"

    priv_info = _collect_file_details(priv_path)
    pub_info = _collect_file_details(pub_path)

    if (not priv_info.exists) and (not pub_info.exists):
        raise KeyOperationError(f"No key named '{name}' found in '{path}'.")

    return KeyDetails(name=name, private_info=priv_info, public_info=pub_info)


def _serialize_private_key(
    private_key: rsa.RSAPrivateKey,
    private_format: str,
    private_encoding: str,
    algorithm: serialization.KeySerializationEncryption,
) -> bytes:
    selected_format = _get_private_key_format(private_format)
    selected_encoding = _get_private_key_encoding(private_encoding)
    return private_key.private_bytes(
        encoding=selected_encoding,
        format=selected_format,
        encryption_algorithm=algorithm,
    )


def _serialize_public_key(
    public_key: rsa.RSAPublicKey,
    public_format: str,
    public_encoding: str,
) -> bytes:
    selected_format = _get_public_key_format(public_format)
    selected_encoding = _get_public_key_encoding(public_encoding)
    return public_key.public_bytes(
        encoding=selected_encoding,
        format=selected_format,
    )


def _get_private_key_format(format_str: str) -> serialization.PrivateFormat:
    format_key = format_str.lower()
    if format_key == "pem":
        format_key = "traditionalopenssl"
    selected_format = _PRIVATE_FORMAT_LOOKUP.get(format_key)
    if selected_format is None:
        raise KeyOperationError(f"Unsupported private key format: {format_str}")
    return selected_format


def _get_private_key_encoding(encoding_str: str) -> serialization.Encoding:
    encoding = _ENCODING_LOOKUP.get(encoding_str.lower())
    if encoding is None:
        raise KeyOperationError(f"Unsupported private key encoding: {encoding_str}")
    return encoding


def _get_public_key_format(format_str: str) -> serialization.PublicFormat:
    selected_format = _PUBLIC_FORMAT_LOOKUP.get(format_str.lower())
    if selected_format is None:
        raise KeyOperationError(f"Unsupported public key format: {format_str}")
    return selected_format


def _get_public_key_encoding(encoding_str: str) -> serialization.Encoding:
    encoding = _ENCODING_LOOKUP.get(encoding_str.lower())
    if encoding is None:
        raise KeyOperationError(f"Unsupported public key encoding: {encoding_str}")
    return encoding


def _validated_keys_path(path: str) -> Path:
    key_path = Path(path).expanduser()
    if not key_path.exists() or not key_path.is_dir():
        raise KeyOperationError(f"Keys path '{path}' does not exist or is not a directory.")
    return key_path


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _collect_file_details(path: Path) -> KeyFileInfo:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return KeyFileInfo(
            path=path,
            exists=False,
            size=None,
            mode=None,
            modified_at=None,
            description="missing",
        )
    except OSError as exc:
        return KeyFileInfo(
            path=path,
            exists=False,
            size=None,
            mode=None,
            modified_at=None,
            description="unavailable",
            error=f"{exc.__class__.__name__}: {exc}",
        )

    return KeyFileInfo(
        path=path,
        exists=True,
        size=stat.st_size,
        mode=stat.st_mode & 0o777,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
        description=_describe_key_file(path),
    )


def _describe_key_file(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return f"error reading ({exc.__class__.__name__})"

    if not raw:
        return "empty file"

    first_line = raw.splitlines()[0].decode("utf-8", errors="ignore").strip()
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


def _pem_header_info(header: str) -> tuple[str, str]:
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


def os_chmod(path: Path, mode: int) -> None:
    """Isolated wrapper to simplify testing/mocking."""
    path.chmod(mode)
