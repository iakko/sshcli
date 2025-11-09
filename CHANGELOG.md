# Changelog

All notable changes to this project are documented here. Dates use the ISO
`YYYY-MM-DD` format.

## [Unreleased]

- Nothing yet.

## [0.1.2] - 2025-11-09

- Published the project to PyPI under the new name `ixlab-sshcli` while keeping
  the `sshcli` command-line entry point.
- Added the `--version` flag to the root command and improved version detection
  so it works for both source installs and the renamed distribution.
- Refined CLI commands (add/edit/remove/backup) and config parsing to satisfy
  complexity checks and improve maintainability.
- Updated documentation to cover PyPI installation, naming differences, and
  release workflow guidance.

## [0.1.1] - 2025-11-07

- First public release on TestPyPI under the original `sshcli` distribution
  name.
- Shipped the initial command set (show/list/find/add/edit/copy/remove/backup)
  built with Typer and Rich, including automatic backups for mutating actions.
- Added comprehensive pytest coverage and README documentation for installing
  from source.
