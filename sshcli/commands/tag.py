from __future__ import annotations

from typing import List

import typer

from .. import config as config_module, settings as settings_module
from .common import console


def register(app: typer.Typer) -> None:
    tag_app = typer.Typer(help="Manage tags and their global definitions")

    @tag_app.command("add")
    def add_tags(
        host_pattern: str = typer.Argument(..., help="Host pattern to add tags to"),
        tags: List[str] = typer.Argument(..., help="Tags to add"),
    ) -> None:
        """Add one or more tags to a host."""
        blocks = config_module.load_host_blocks()
        matching = [b for b in blocks if host_pattern in b.patterns]

        if not matching:
            console.print(f"[red]No host found matching '{host_pattern}'[/red]")
            raise typer.Exit(1)

        if len(matching) > 1:
            console.print(f"[yellow]Multiple hosts match '{host_pattern}':[/yellow]")
            for block in matching:
                console.print(f"  - {', '.join(block.patterns)}")
            raise typer.Exit(1)

        block = matching[0]

        definitions = settings_module.get_tag_definitions()
        lookup = {name.lower(): name for name in definitions.keys()}

        missing = [tag for tag in tags if tag.lower() not in lookup]
        if missing:
            console.print(
                "[red]The following tags are not defined: "
                + ", ".join(repr(t) for t in missing)
                + "[/red]"
            )
            console.print(
                "[yellow]Define tags (and their colors) with 'sshcli tag color TAG COLOR' before assigning them.[/yellow]"
            )
            raise typer.Exit(1)

        for tag in tags:
            canonical = lookup[tag.lower()]
            block.add_tag(canonical)

        config_module.replace_host_block_with_metadata(
            block.source_file,
            block,
            block.patterns,
            list(block.options.items()),
        )

        console.print(f"[green]Added tags {', '.join(repr(t) for t in tags)} to {host_pattern}[/green]")

    @tag_app.command("remove")
    def remove_tags(
        host_pattern: str = typer.Argument(..., help="Host pattern to remove tags from"),
        tags: List[str] = typer.Argument(..., help="Tags to remove"),
    ) -> None:
        """Remove one or more tags from a host."""
        blocks = config_module.load_host_blocks()
        matching = [b for b in blocks if host_pattern in b.patterns]

        if not matching:
            console.print(f"[red]No host found matching '{host_pattern}'[/red]")
            raise typer.Exit(1)

        if len(matching) > 1:
            console.print(f"[yellow]Multiple hosts match '{host_pattern}':[/yellow]")
            for block in matching:
                console.print(f"  - {', '.join(block.patterns)}")
            raise typer.Exit(1)

        block = matching[0]
        for tag in tags:
            block.remove_tag(tag)

        config_module.replace_host_block_with_metadata(
            block.source_file,
            block,
            block.patterns,
            list(block.options.items()),
        )

        console.print(f"[green]Removed tags {', '.join(repr(t) for t in tags)} from {host_pattern}[/green]")

    @tag_app.command("list")
    def list_tags() -> None:
        """List all tags and their usage counts."""
        blocks = config_module.load_host_blocks()
        tag_counts: dict[str, int] = {}

        for block in blocks:
            for tag in block.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            console.print("[yellow]No tags found[/yellow]")
            return

        for tag in sorted(tag_counts.keys()):
            count = tag_counts[tag]
            console.print(f"{tag} ({count} host{'s' if count != 1 else ''})")

    @tag_app.command("show")
    def show_tag(
        tag: str = typer.Argument(..., help="Tag to filter by"),
    ) -> None:
        """Show all hosts with a specific tag."""
        blocks = config_module.load_host_blocks()
        matching = [b for b in blocks if b.has_tag(tag)]

        if not matching:
            console.print(f"[yellow]No hosts found with tag '{tag}'[/yellow]")
            return

        for block in matching:
            hostname = block.options.get("HostName", "")
            tags_str = ", ".join(block.tags)
            console.print(f"{', '.join(block.patterns):20} {hostname:20} [{tags_str}]")

    @tag_app.command("color")
    def set_color(
        tag: str = typer.Argument(..., help="Tag to define or update"),
        color: str = typer.Argument(..., help="Color name or hex code"),
    ) -> None:
        """Create or update a tag definition (tag + color) in the central sshcli.json."""
        # Load existing definitions from the central sshcli.json
        definitions = settings_module.get_tag_definitions()
        # Update the specific tag's color
        definitions[tag] = color
        # Save all definitions back to sshcli.json
        settings_module.update_tag_definitions(definitions)
        console.print(
            f"[green]Set color for tag '{tag}' to '{color}' in the central configuration.[/green]"
        )

    app.add_typer(tag_app, name="tag")


__all__ = ["register"]
