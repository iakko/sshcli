from __future__ import annotations

import textwrap
from typing import Dict

import pytest
from typer.testing import CliRunner


@pytest.fixture()
def sample_config(tmp_path) -> Dict[str, object]:
    """Create a temporary SSH config with an include for testing."""
    ssh_dir = tmp_path / "ssh"
    ssh_dir.mkdir()

    config_path = ssh_dir / "config"
    include_path = ssh_dir / "extra.conf"

    config_path.write_text(
        textwrap.dedent(
            """
            Host foo
                HostName foo.example.com
                User alice

            Include extra.conf
            """
        ).lstrip()
    )

    include_path.write_text(
        textwrap.dedent(
            """
            Host *.example.com
                User wildcard
            """
        ).lstrip()
    )

    return {
        "ssh_dir": ssh_dir,
        "config": config_path,
        "include": include_path,
    }


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()
