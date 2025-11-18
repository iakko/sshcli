from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .constants import DEFAULT_HOME_SSH_CONFIG

SETTINGS_ENV_VAR = "SSHCLI_SETTINGS_PATH"
DEFAULT_SETTINGS_PATH = Path("~/.ssh/sshcli.json")


@dataclass
class ConfigSource:
    path: str
    enabled: bool = True
    is_default: bool = False


@dataclass
class AppSettings:
    config_sources: List[ConfigSource]


def _normalize_path(path: str | Path) -> str:
    return str(Path(path).expanduser())


_DEFAULT_SOURCE_PATHS = [
    "/etc/ssh/ssh_config",
    DEFAULT_HOME_SSH_CONFIG,
]


def _default_config_sources() -> List[ConfigSource]:
    sources: List[ConfigSource] = []
    for raw in _DEFAULT_SOURCE_PATHS:
        normalized = _normalize_path(raw)
        sources.append(
            ConfigSource(
                path=normalized,
                enabled=True,
                is_default=(normalized == _normalize_path(DEFAULT_HOME_SSH_CONFIG)),
            )
        )
    if not any(source.is_default for source in sources) and sources:
        sources[0].is_default = True
    return sources


def default_settings() -> AppSettings:
    return AppSettings(config_sources=_default_config_sources())


def settings_path() -> Path:
    override = os.environ.get(SETTINGS_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return DEFAULT_SETTINGS_PATH.expanduser()


def load_settings() -> AppSettings:
    path = settings_path()
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return default_settings()
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse sshcli settings file {path}: {exc}") from exc

    entries = data.get("configSources")
    sources: List[ConfigSource] = []
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw_path = entry.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                continue
            enabled = entry.get("enabled", True)
            is_default = bool(entry.get("default", False))
            sources.append(
                ConfigSource(
                    path=_normalize_path(raw_path),
                    enabled=bool(enabled),
                    is_default=is_default,
                )
            )

    if not sources:
        sources = _default_config_sources()
    else:
        # Ensure at most one default flag.
        default_seen = False
        for source in sources:
            if source.is_default:
                if not default_seen:
                    default_seen = True
                else:
                    source.is_default = False
        if not default_seen and sources:
            sources[0].is_default = True
    return AppSettings(config_sources=sources)


def save_settings(settings: AppSettings) -> Path:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "configSources": [
            {"path": source.path, "enabled": source.enabled, "default": source.is_default}
            for source in settings.config_sources
        ]
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return path


def active_config_paths(settings: Optional[AppSettings] = None) -> List[Path]:
    if settings is None:
        settings = load_settings()
    active: List[Path] = []
    for source in settings.config_sources:
        if not source.enabled:
            continue
        active.append(Path(source.path).expanduser())
    return active


def add_or_update_source(path: str | Path, enabled: bool = True, make_default: bool = False) -> AppSettings:
    normalized = _normalize_path(path)
    settings = load_settings()
    found = False
    for source in settings.config_sources:
        if _normalize_path(source.path) == normalized:
            source.enabled = enabled
            source.path = normalized
            if make_default:
                _mark_default(settings, source)
            found = True
            break
    if not found:
        new_source = ConfigSource(path=normalized, enabled=enabled, is_default=False)
        settings.config_sources.append(new_source)
        if make_default or not any(src.is_default for src in settings.config_sources):
            _mark_default(settings, new_source)
    save_settings(settings)
    return settings


def set_source_enabled(path: str | Path, enabled: bool) -> AppSettings:
    normalized = _normalize_path(path)
    settings = load_settings()
    for source in settings.config_sources:
        if _normalize_path(source.path) == normalized:
            source.enabled = enabled
            save_settings(settings)
            return settings
    raise ValueError(f"No config source registered for {normalized}")


def remove_source(path: str | Path) -> AppSettings:
    normalized = _normalize_path(path)
    settings = load_settings()
    removed_default = False
    updated: List[ConfigSource] = []
    for source in settings.config_sources:
        if _normalize_path(source.path) == normalized:
            if source.is_default:
                removed_default = True
            continue
        updated.append(source)
    if len(updated) == len(settings.config_sources):
        raise ValueError(f"No config source registered for {normalized}")
    settings.config_sources = updated or _default_config_sources()
    if removed_default and settings.config_sources:
        _mark_default(settings, settings.config_sources[0])
    save_settings(settings)
    return settings


def reset_sources() -> AppSettings:
    settings = default_settings()
    save_settings(settings)
    return settings


def default_config_path(settings: Optional[AppSettings] = None) -> Path:
    if settings is None:
        settings = load_settings()
    chosen: Optional[ConfigSource] = next(
        (source for source in settings.config_sources if source.is_default),
        None,
    )
    if chosen is None:
        chosen = next((source for source in settings.config_sources if source.enabled), None)
    if chosen is None:
        chosen = settings.config_sources[0] if settings.config_sources else ConfigSource(
            path=_normalize_path(DEFAULT_HOME_SSH_CONFIG),
            enabled=True,
            is_default=True,
        )
    return Path(chosen.path).expanduser()


def set_default_source(path: str | Path) -> AppSettings:
    normalized = _normalize_path(path)
    settings = load_settings()
    target = None
    for source in settings.config_sources:
        if _normalize_path(source.path) == normalized:
            target = source
            break
    if target is None:
        target = ConfigSource(path=normalized, enabled=True, is_default=True)
        settings.config_sources.append(target)
    _mark_default(settings, target)
    save_settings(settings)
    return settings


def _mark_default(settings: AppSettings, target: ConfigSource) -> None:
    for source in settings.config_sources:
        source.is_default = source is target


__all__ = [
    "AppSettings",
    "ConfigSource",
    "DEFAULT_SETTINGS_PATH",
    "SETTINGS_ENV_VAR",
    "add_or_update_source",
    "active_config_paths",
    "default_settings",
    "default_config_path",
    "load_settings",
    "remove_source",
    "reset_sources",
    "save_settings",
    "set_source_enabled",
    "set_default_source",
    "settings_path",
]
