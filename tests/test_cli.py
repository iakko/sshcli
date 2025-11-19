from sshcli.cli import _rewrite_default_invocation, run


def test_rewrite_default_invocation_handles_host_shorthand():
    rewritten = _rewrite_default_invocation(["my-host", "--details", "--foo", "bar"])
    assert rewritten == ["show", "my-host", "--details", "--foo", "bar"]


def test_rewrite_default_invocation_preserves_commands_and_flags():
    assert _rewrite_default_invocation(["list", "--files"]) == ["list", "--files"]
    assert _rewrite_default_invocation(["--help"]) == ["--help"]


def test_run_passes_rewritten_arguments(monkeypatch):
    calls = {}

    class DummyCommand:
        def main(self, args, prog_name, standalone_mode):
            calls["args"] = args
            calls["prog"] = prog_name
            calls["standalone"] = standalone_mode

    dummy = DummyCommand()
    monkeypatch.setattr("sshcli.cli.get_command", lambda app: dummy)

    run(["my-host", "--details", "--flag"])

    assert calls["args"] == ["show", "my-host", "--details", "--flag"]
    assert calls["prog"] == "sshcli"
    assert calls["standalone"] is False
