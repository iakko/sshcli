from datetime import datetime
from pathlib import Path

from typer.testing import CliRunner

from sshcli.cli import app
from sshcli.commands import key as key_module
from sshcore import keys as core_keys


runner = CliRunner()


def test_key_add_generates_pair(monkeypatch, tmp_path):
    generated = {}

    def fake_generate(**kwargs):
        generated.update(kwargs)
        return core_keys.KeyGenerationResult(
            private_path=Path(tmp_path / "id_rsa"),
            public_path=Path(tmp_path / "id_rsa.pub"),
        )

    monkeypatch.setattr(key_module.core_keys, "generate_key_pair", fake_generate)

    result = runner.invoke(app, ["key", "add", "id_rsa", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert generated["name"] == "id_rsa"
    assert "Generated key" in result.stdout


def test_key_add_reports_errors(monkeypatch):
    def fake_generate(**kwargs):
        raise core_keys.KeyOperationError("boom")

    monkeypatch.setattr(key_module.core_keys, "generate_key_pair", fake_generate)

    result = runner.invoke(app, ["key", "add", "id_rsa"])
    assert result.exit_code == 1
    assert "boom" in result.stdout


def test_key_list_outputs_table(monkeypatch):
    info = core_keys.KeyFileInfo(
        path=Path("/tmp/id_rsa"),
        exists=True,
        size=123,
        mode=0o600,
        modified_at=datetime.now(),
        description="rsa",
    )
    summary = core_keys.KeyPairSummary(base_name="id_rsa", private_info=info, public_info=info)

    monkeypatch.setattr(key_module.core_keys, "list_key_pairs", lambda path: [summary])

    result = runner.invoke(app, ["key", "list"])
    assert result.exit_code == 0
    assert "Keys in" in result.stdout
    assert "id_rsa" in result.stdout


def test_key_list_handles_errors(monkeypatch):
    def fake_list(path):
        raise core_keys.KeyOperationError("cannot list")

    monkeypatch.setattr(key_module.core_keys, "list_key_pairs", fake_list)

    result = runner.invoke(app, ["key", "list"])
    assert result.exit_code == 1
    assert "cannot list" in result.stdout


def test_key_show_displays_details(monkeypatch):
    info = core_keys.KeyFileInfo(
        path=Path("/tmp/id_rsa"),
        exists=True,
        size=64,
        mode=0o600,
        modified_at=datetime.now(),
        description="rsa",
    )
    details = core_keys.KeyDetails(name="id_rsa", private_info=info, public_info=info)
    monkeypatch.setattr(key_module.core_keys, "describe_key", lambda name, path: details)

    result = runner.invoke(app, ["key", "show", "id_rsa"])
    assert result.exit_code == 0
    assert "Key 'id_rsa' details" in result.stdout
    assert "/tmp/id_rsa" in result.stdout


def test_key_show_handles_errors(monkeypatch):
    def fake_describe(name, path):
        raise core_keys.KeyOperationError("missing key")

    monkeypatch.setattr(key_module.core_keys, "describe_key", fake_describe)

    result = runner.invoke(app, ["key", "show", "missing"])
    assert result.exit_code == 1
    assert "missing key" in result.stdout
