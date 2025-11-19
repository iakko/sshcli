from __future__ import annotations

"""Compatibility shim so `sshcli.settings` maps to the core settings module."""

import sys as _sys

from sshcore import settings as _core_settings

_sys.modules[__name__] = _core_settings
