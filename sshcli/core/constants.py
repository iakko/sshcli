"""Common constants shared across config and settings modules."""

from __future__ import annotations

DEFAULT_HOME_SSH = "~/.ssh"
DEFAULT_HOME_SSH_CONFIG = f"{DEFAULT_HOME_SSH}/config"
DEFAULT_KEYS_DIR = f"{DEFAULT_HOME_SSH}/keys"

DEFAULT_INCLUDE_FALLBACKS = [
    "~/.ssh/config.d/*.conf",
]

__all__ = [
    "DEFAULT_HOME_SSH",
    "DEFAULT_HOME_SSH_CONFIG",
    "DEFAULT_KEYS_DIR",
    "DEFAULT_INCLUDE_FALLBACKS",
]
