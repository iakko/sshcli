import pytest
from rich.console import Console

from sshcli.commands import common


def test_matching_blocks_prefers_exact_matches(host_block_factory):
    wildcard = host_block_factory(
        ["web-*"],
        lineno=5,
        options={"HostName": "wild.example.com"},
    )
    literal = host_block_factory(
        ["web-01"],
        lineno=10,
        options={"HostName": "literal.example.com"},
    )

    primary, matched = common.matching_blocks("web-01", [wildcard, literal])
    assert len(matched) == 2
    assert primary == [literal]


def test_matching_blocks_returns_empty_when_no_match(host_block_factory):
    block = host_block_factory(["db-*"])
    primary, matched = common.matching_blocks("web-01", [block])
    assert primary == []
    assert matched == []


def test_parse_option_entry_validates_format():
    assert common.parse_option_entry("User=root") == ("User", "root")
    with pytest.raises(common.typer.BadParameter):
        common.parse_option_entry("invalid")


def test_format_block_table_includes_tags(host_block_factory):
    block = host_block_factory(
        ["app"],
        options={"HostName": "example.com", "User": "ubuntu"},
        tags=["prod", "web"],
    )
    table = common.format_block_table(block)
    console = Console(record=True, force_terminal=False)
    console.print(table)
    output = console.export_text()
    assert "prod, web" in output
