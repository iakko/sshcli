from __future__ import annotations

import textwrap
from pathlib import Path
from typer.testing import CliRunner

from sshcli.cli import app as cli_app


def _setup_backups(target: Path, stamps: list[str]) -> None:
    backup_dir = target.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for stamp in stamps:
        backup_file = backup_dir / f"{target.name}.backup.{stamp}"
        backup_file.write_text(f"# backup {stamp}\n")


def test_show_command_uses_discovered_configs(sample_config, cli_runner, monkeypatch):
    config_path: Path = sample_config["config"]

    monkeypatch.setattr(
        "sshcli.config.discover_config_files",
        lambda: [config_path],
    )

    result = cli_runner.invoke(cli_app, ["show", "foo"])

    assert result.exit_code == 0
    assert "foo.example.com" in result.stdout
    assert "Host foo" in result.stdout


def test_list_command_outputs_hosts(sample_config, cli_runner, monkeypatch):
    config_path: Path = sample_config["config"]

    monkeypatch.setattr(
        "sshcli.config.discover_config_files",
        lambda: [config_path],
    )

    result = cli_runner.invoke(cli_app, ["list"])

    assert result.exit_code == 0
    output = result.stdout
    assert "foo" in output
    assert "foo.example.com" in output


def test_find_command_matches_patterns(sample_config, cli_runner, monkeypatch):
    config_path: Path = sample_config["config"]

    monkeypatch.setattr(
        "sshcli.config.discover_config_files",
        lambda: [config_path],
    )

    result = cli_runner.invoke(cli_app, ["find", "foo"])

    assert result.exit_code == 0
    output = result.stdout
    assert "foo" in output
    assert "foo.example.com" in output


def test_backup_list_shows_only_new_directory(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    target.write_text("Host foo\n    HostName foo.example.com\n")

    _setup_backups(target, ["20240101010101", "20240102020202"])

    # Legacy backup sitting alongside the config should be ignored.
    legacy = target.parent / f"{target.name}.backup.20231231235959"
    legacy.write_text("# legacy backup\n")

    result = cli_runner.invoke(
        cli_app,
        ["backup", "list", "--target", str(target)],
    )

    assert result.exit_code == 0
    output = result.stdout
    assert "20240101010101" in output
    assert "20240102020202" in output
    assert "20231231235959" not in output


def test_backup_restore_replaces_target(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    target.write_text("Host foo\n    HostName original.example.com\n")

    backup_dir = target.parent / "backups"
    backup_dir.mkdir()
    backup_file = backup_dir / f"{target.name}.backup.20240101010101"
    backup_file.write_text("Host foo\n    HostName restored.example.com\n")

    result = cli_runner.invoke(
        cli_app,
        [
            "backup",
            "restore",
            "20240101010101",
            "--target",
            str(target),
            "--no-backup-current",
        ],
    )

    assert result.exit_code == 0
    assert "restored.example.com" in target.read_text()


def test_backup_prune_respects_keep(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    target.write_text("Host foo\n    HostName foo.example.com\n")

    stamps = ["20240101010101", "20240102020202", "20240103030303"]
    _setup_backups(target, stamps)

    result = cli_runner.invoke(
        cli_app,
        ["backup", "prune", "--target", str(target), "--keep", "2"],
    )

    assert result.exit_code == 0

    remaining = sorted(p.name for p in (target.parent / "backups").iterdir())
    assert remaining == [
        f"{target.name}.backup.20240102020202",
        f"{target.name}.backup.20240103030303",
    ]


def _write_config(path: Path, content: str) -> None:
    formatted = textwrap.dedent(content).strip()
    if formatted and not formatted.endswith("\n"):
        formatted += "\n"
    path.write_text(formatted)


def test_add_command_appends_host(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    _write_config(
        target,
        """
        Host existing
            HostName existing.example.com
        """,
    )

    result = cli_runner.invoke(
        cli_app,
        [
            "add",
            "new-host",
            "--hostname",
            "new.example.com",
            "--user",
            "bob",
            "--target",
            str(target),
        ],
    )

    assert result.exit_code == 0
    content = target.read_text()
    assert "Host new-host" in content
    assert "HostName new.example.com" in content
    assert "User bob" in content
    backups = list((target.parent / "backups").glob("config.backup.*"))
    assert backups, "Expected a backup to be created"


def test_tag_color_creates_definition(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    _write_config(
        target,
        """
        Host foo
            HostName foo.example.com
        """,
    )

    result = cli_runner.invoke(
        cli_app,
        [
            "tag",
            "color",
            "prod",
            "red",
            "--target",
            str(target),
        ],
    )

    assert result.exit_code == 0
    content = target.read_text()
    assert "# @tagdef prod red" in content.splitlines()[0]


def test_tag_add_requires_defined_tag(tmp_path, cli_runner: CliRunner, monkeypatch):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    config_path = ssh_dir / "config"
    _write_config(
        config_path,
        """
        Host foo
            HostName foo.example.com
        """,
    )

    monkeypatch.setattr(
        "sshcli.config.discover_config_files",
        lambda: [config_path],
    )

    result = cli_runner.invoke(cli_app, ["tag", "add", "foo", "prod"])

    assert result.exit_code == 1
    assert "not defined" in result.stdout


def test_tag_add_assigns_defined_tag(tmp_path, cli_runner: CliRunner, monkeypatch):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    config_path = ssh_dir / "config"
    _write_config(
        config_path,
        """
        # @tagdef Prod red

        Host foo
            HostName foo.example.com
        """,
    )

    monkeypatch.setattr(
        "sshcli.config.discover_config_files",
        lambda: [config_path],
    )

    result = cli_runner.invoke(cli_app, ["tag", "add", "foo", "prod"])

    assert result.exit_code == 0
    content = config_path.read_text().splitlines()
    assert any(line.strip() == "# @tags: Prod" for line in content)


def test_edit_command_updates_existing_host(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    _write_config(
        target,
        """
        Host foo
            HostName foo.example.com
        """,
    )

    result = cli_runner.invoke(
        cli_app,
        [
            "edit",
            "foo",
            "--hostname",
            "updated.example.com",
            "--target",
            str(target),
        ],
    )

    assert result.exit_code == 0
    content = target.read_text()
    assert "HostName updated.example.com" in content
    backups = list((target.parent / "backups").glob("config.backup.*"))
    assert backups, "Expected a backup to be created"


def test_copy_command_creates_new_block(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    _write_config(
        target,
        """
        Host foo
            HostName foo.example.com
        """,
    )

    result = cli_runner.invoke(
        cli_app,
        [
            "copy",
            "foo",
            "--name",
            "foo-copy",
            "--target",
            str(target),
        ],
    )

    assert result.exit_code == 0
    content = target.read_text()
    assert "Host foo-copy" in content
    assert "HostName foo.example.com" in content


def test_remove_command_deletes_block(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    _write_config(
        target,
        """
        Host foo
            HostName foo.example.com

        Host bar
            HostName bar.example.com
        """,
    )

    result = cli_runner.invoke(
        cli_app,
        [
            "remove",
            "foo",
            "--target",
            str(target),
        ],
    )

    assert result.exit_code == 0
    content = target.read_text()
    assert "Host foo" not in content
    assert "Host bar" in content


def test_backup_prune_requires_selector(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    target.write_text("Host foo\n    HostName foo.example.com\n")

    result = cli_runner.invoke(
        cli_app,
        [
            "backup",
            "prune",
            "--target",
            str(target),
        ],
    )

    assert result.exit_code == 1
    assert "--keep and/or --before" in result.stdout


def test_backup_prune_rejects_negative_keep(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    target.write_text("Host foo\n    HostName foo.example.com\n")

    result = cli_runner.invoke(
        cli_app,
        [
            "backup",
            "prune",
            "--target",
            str(target),
            "--keep",
            "-1",
        ],
    )

    assert result.exit_code == 1
    assert "--keep must be zero or greater" in result.stdout


def test_backup_prune_validates_timestamp_format(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    target.write_text("Host foo\n    HostName foo.example.com\n")

    result = cli_runner.invoke(
        cli_app,
        [
            "backup",
            "prune",
            "--target",
            str(target),
            "--before",
            "invalidstamp",
        ],
    )

    assert result.exit_code == 1
    assert "YYYYMMDDHHMMSS" in result.stdout


def test_backup_restore_requires_existing_stamp(tmp_path, cli_runner: CliRunner):
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()
    target = ssh_dir / "config"
    target.write_text("Host foo\n    HostName foo.example.com\n")

    backup_dir = target.parent / "backups"
    backup_dir.mkdir()
    valid_backup = backup_dir / f"{target.name}.backup.20240101010101"
    valid_backup.write_text("Host foo\n    HostName valid.example.com\n")

    result = cli_runner.invoke(
        cli_app,
        [
            "backup",
            "restore",
            "99999999999999",
            "--target",
            str(target),
            "--no-backup-current",
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.stdout
