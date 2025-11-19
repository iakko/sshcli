from pathlib import Path

import pytest

from sshcore.models import HostBlock


@pytest.fixture()
def host_block_factory():
    def _make(
        patterns,
        *,
        source="~/.ssh/config",
        lineno=1,
        options=None,
        tags=None,
    ):
        block = HostBlock(list(patterns), Path(source), lineno)
        if options:
            block.options.update(options)
        if tags:
            block.tags = list(tags)
        return block

    return _make
