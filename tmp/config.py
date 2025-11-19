from __future__ import annotations

"""Compatibility shim: importers of `sshcli.config` get the core config module."""

import sys as _sys

from sshcore import config as _core_config

_sys.modules[__name__] = _core_config
