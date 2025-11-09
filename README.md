# sshcli

`sshcli` is a lightweight command line tool for exploring and editing your OpenSSH client configuration. It discovers `Host` blocks across your SSH config files, renders them with Rich-powered tables, and provides convenient subcommands for searching, inspecting, and managing entries without leaving the terminal.

> **Note:** the published PyPI package is named `ixlab-sshcli`, but it still installs the `sshcli` command-line entry point.

## Highlights
- Quick lookup: run `sshcli <host>` to jump straight to a matching `Host` block (with optional `--details`).
- Rich listings: format hosts, patterns, and key options in compact tables.
- Powerful search: filter hosts by wildcard pattern or `HostName` value.
- Safe editing: add, copy, edit, or remove blocks with automatic backups of modified files.
- Include awareness: follows `Include` directives and honours the default SSH config locations.

## Installation

> Requires Python 3.10 or newer.

### From PyPI (recommended)

```bash
python -m pip install --upgrade pip
python -m pip install ixlab-sshcli
```

This installs the latest release and exposes the `sshcli` executable on your `PATH`.

### From source
```bash
git clone https://github.com/iakko/sshcli
cd sshcli
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

The project depends on `typer`, `rich`, and friends (see `pyproject.toml`). Installing from source pulls in the same runtime requirements you get from PyPI; optional niceties such as `prompt_toolkit` will be picked up automatically when those packages declare them.

### Requirements file (optional)

If you prefer to mirror the development environment used in this repository:
```bash
python -m pip install -r requirements.txt
```

## Usage

After installation, the `sshcli` command becomes available on your `$PATH`.

```bash
# Show the most specific block matching "prod-web"
sshcli prod-web

# View every block that matches the pattern
sshcli prod-web --details

# List all discovered Host entries
sshcli list --patterns --files

# Search by wildcard or substring
sshcli find bastion
sshcli find "corp-*"
```

Use `sshcli help` for an overview and `sshcli COMMAND --help` to inspect options for an individual subcommand.

### Command tour

| Command | Purpose |
| --- | --- |
| `sshcli show [NAME] [--details]` | Render one or all matching `Host` blocks with syntax-highlighted tables. Falls back to interactive completion (via `prompt_toolkit`) when the host argument is omitted in a TTY. |
| `sshcli list [--patterns] [--files]` | Summarise every discovered block, optionally displaying wildcard patterns and source file locations. |
| `sshcli find QUERY` | Locate blocks by wildcard (`fnmatch`) or substring match against host patterns and `HostName` values. |
| `sshcli add PATTERN... [options]` | Append a new block to a target config file (`~/.ssh/config` by default). Supports setting core options plus arbitrary `--option KEY=VALUE` pairs. |
| `sshcli edit NAME [options]` | Update patterns or option values in-place. Can clear all existing settings, replace patterns, or remove specific keys. |
| `sshcli copy SOURCE --name NAME` | Duplicate an existing block into a new entry, preserving options. |
| `sshcli remove NAME` | Delete matching blocks from a target file, with selection when multiple matches exist. |
| `sshcli backup list` | Show available backups for a target config with timestamps, file sizes, and paths. |
| `sshcli backup restore STAMP` | Restore the target config from a specific backup (optionally saving the current state first). |
| `sshcli backup prune [--keep N] [--before STAMP]` | Prune old backups by keeping the most recent N or dropping everything older than a timestamp. |
| `sshcli help` | Display a Rich table of available commands and tips. |

## Configuration discovery

- Entry points default to `/etc/ssh/ssh_config` and `~/.ssh/config`.
- If neither exists, the CLI looks for `~/.ssh/config.d/*.conf` include fragments.
- `Include` directives inside any parsed file are followed recursively, and relative paths resolve against the including file.
- `Match` blocks are ignored, keeping the focus on client-side `Host` definitions.

## Editing safety

When writing to an SSH config file, `sshcli` automatically:
- Creates parent directories as needed.
- Generates a timestamped backup (stored under `~/.ssh/backups/`) before modifying existing content.
- Preserves existing spacing and ensures the file ends with a newline.

All mutating commands (`add`, `edit`, `copy`, `remove`) accept `--target PATH` so you can work against alternate configuration files or sandboxed copies.

## Development

```bash
git clone https://github.com/iakko/sshcli
cd sshcli
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

### Testing

Install development dependencies (including `pytest`) and run the suite:

```bash
python -m pip install -r requirements.txt
pytest
```

The tests exercise config parsing, CLI behaviour, and backup tooling by working against temporary files, so they are safe to run on any machine.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a version-by-version summary of notable updates.

## Roadmap

Upcoming work includes:

- **Known hosts observability:** surface `known_hosts` entries alongside SSH config data to make it easier to audit trust relationships.
- **SSH key shortcuts:** add helper commands to inspect and reference private keys (e.g., quick copying of `IdentityFile` paths).

If there is a feature you would like to see, feel free to open an issue or pull request.

## License

This project is distributed under the MIT License. See `LICENSE` for details.
