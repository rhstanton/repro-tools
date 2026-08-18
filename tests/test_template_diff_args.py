"""repro-template-diff must reject what it does not understand.

This command parses argv by hand rather than with argparse, because the module
predates its console script and is also imported directly. Hand parsing is
allowed; being permissive is not.

Until 2026-08-17 it read options with `"--verbose" in argv` and looked at
nothing else. Two consequences:

  * `--verbos` (a plausible typo) ran a full template diff with verbosity
    silently off, cloned the template, and exited 0 -- the user gets a correct
    but less detailed answer and no hint they mistyped;
  * there was no --help, so `repro-template-diff --help` did not print usage,
    it fetched the template and diffed it.

A CLI that ignores unrecognized input cannot tell a user they made a mistake,
and this one is in a public archive.
"""

from __future__ import annotations

import pytest

from repro_tools.template_update import USAGE, main


class TestHelp:
    def test_help_exits_zero_and_prints_usage(self, capsys):
        assert main(["--help"]) == 0
        assert "usage: repro-template-diff" in capsys.readouterr().out

    def test_short_help_is_accepted(self, capsys):
        assert main(["-h"]) == 0
        assert "usage:" in capsys.readouterr().out

    def test_help_does_no_work(self, capsys, monkeypatch):
        """--help must not touch the network or the filesystem.

        Enforced by making the first real step explode: if help is handled
        before it, this passes; if help falls through, the fake raises.
        """

        def explode(*args, **kwargs):
            raise AssertionError("--help reached template_clone(); it did work")

        monkeypatch.setattr("repro_tools.template_update.template_clone", explode)
        assert main(["--help"]) == 0

    def test_usage_documents_every_option_it_accepts(self):
        for option in ("--verbose", "--template-ref", "--help"):
            assert option in USAGE


class TestUnknownArguments:
    def test_typo_is_rejected(self, capsys):
        """The motivating case: --verbos is not --verbose."""
        assert main(["--verbos"]) == 2
        assert "unknown argument(s): --verbos" in capsys.readouterr().err

    def test_unknown_argument_prints_usage(self, capsys):
        main(["--wat"])
        assert "usage:" in capsys.readouterr().err

    def test_positional_junk_is_rejected(self, capsys):
        assert main(["some-file.txt"]) == 2
        assert "some-file.txt" in capsys.readouterr().err

    def test_rejection_happens_before_any_work(self, monkeypatch):
        def explode(*args, **kwargs):
            raise AssertionError("bad arguments reached template_clone()")

        monkeypatch.setattr("repro_tools.template_update.template_clone", explode)
        assert main(["--nope"]) == 2


class TestTemplateRef:
    def test_missing_value_is_an_error_not_an_index_crash(self, capsys):
        """`--template-ref` at the end used to raise IndexError.

        A stack trace is a worse error message than a sentence, and an
        IndexError from argv handling looks like a bug in the tool rather than
        a mistake by the user.
        """
        assert main(["--template-ref"]) == 2
        assert "--template-ref needs a value" in capsys.readouterr().err

    def test_its_value_is_not_treated_as_unknown(self, monkeypatch):
        """The ref itself must not trip the unknown-argument check.

        This is the subtle failure of allowlisting by value: the check has to
        know that the token after --template-ref is data, not a flag.
        """
        seen = {}

        def fake_clone(url, cache):
            seen["called"] = True
            raise SystemExit(0)

        monkeypatch.setattr("repro_tools.template_update.template_clone", fake_clone)
        monkeypatch.setattr(
            "repro_tools.template_update.read_origin",
            lambda project: {
                "template": {"url": "u", "commit": "abc123", "version": "1"}
            },
        )
        with pytest.raises(SystemExit):
            main(["--template-ref", "v2.0.0"])
        assert seen.get("called"), "parsing rejected a valid --template-ref value"
