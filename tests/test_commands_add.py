import pytest
import typer

from sshcli.commands import add as add_module


def test_build_options_accepts_core_fields():
    options = add_module._build_options(
        hostname="example.com",
        user="ubuntu",
        port=2200,
        option_entries=["IdentityFile=~/.ssh/id_rsa"],
    )
    assert ("HostName", "example.com") in options
    assert ("User", "ubuntu") in options
    assert ("Port", "2200") in options
    assert ("IdentityFile", "~/.ssh/id_rsa") in options


def test_build_options_validates_custom_entries():
    with pytest.raises(typer.Exit):
        add_module._build_options(
            hostname="example.com",
            user="",
            port=0,
            option_entries=["invalid-entry"],
        )


def test_guard_duplicates_detects_existing_blocks(host_block_factory):
    existing = host_block_factory(["app"], lineno=5)
    with pytest.raises(typer.Exit):
        add_module._guard_duplicates(["app"], [existing], force=False)

    # Should pass when force flag is used
    add_module._guard_duplicates(["app"], [existing], force=True)
