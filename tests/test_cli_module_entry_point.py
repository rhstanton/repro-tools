"""`python -m repro_tools.cli <command>` must run the command, or fail loudly.

THE BUG THIS PINS

Until 2026-08-17 this module had no `if __name__ == "__main__"` block. Running a
module with `-m` and no such block IMPORTS it: definitions execute, nothing is
called, arguments are ignored, and the process exits 0.

Project Makefiles invoke repro-tools this way -- not through the console
scripts -- so that the interpreter is the project's own .venv rather than
whatever is first on PATH:

    REPRO_PUBLISH := $(PYTHON) -m repro_tools.cli publish

The result in project_template was that `make publish`, `make diff-outputs`,
`make pre-submit`, `make pre-submit-strict` and `make replication-report` all
did nothing and reported success. `make publish` printed "Publishing complete!"
over a paper/ directory it had not written to in seven months, and make -- given
a zero exit -- went on to touch the stamp files recording the work as done.

The cheapest probe for "is anything reading my arguments" is to pass a flag that
cannot possibly be valid. It answered 0. Several tests below are exactly that
probe, kept because it is the one question whose answer distinguishes a working
CLI from an imported module.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"

from repro_tools.cli import _COMMANDS, main  # noqa: E402


def run_module(*args: str) -> subprocess.CompletedProcess:
    """Invoke the module the way a Makefile does, in a real subprocess."""
    env = {"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"}
    return subprocess.run(
        [sys.executable, "-m", "repro_tools.cli", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


# --- the regression itself -------------------------------------------------


@pytest.mark.parametrize("command", sorted(_COMMANDS))
def test_unrecognized_flag_is_never_a_silent_success(command):
    """The probe that would have caught this in one line.

    Every command must reject a flag that does not exist. A zero exit here
    means arguments are not being parsed at all -- the module is being imported
    rather than run.
    """
    result = run_module(command, "--nonsense-flag-that-cannot-exist")
    assert result.returncode != 0, (
        f"`python -m repro_tools.cli {command} --nonsense-flag-that-cannot-exist` "
        f"exited 0. Nothing is parsing arguments, so every Makefile target built "
        f"on this command is a no-op that reports success."
    )


def test_module_has_a_main_guard():
    """Pin the mechanism, not just the symptom.

    Someone refactoring this file could delete the guard and every subprocess
    test above would still pass if a console script happened to be installed.
    """
    source = (SRC / "repro_tools" / "cli.py").read_text()
    assert 'if __name__ == "__main__":' in source


# --- dispatch --------------------------------------------------------------


def test_no_arguments_is_an_error_with_usage():
    result = run_module()
    assert result.returncode == 2
    assert "usage:" in (result.stdout + result.stderr)


def test_unknown_command_names_what_was_wrong():
    result = run_module("definitely-not-a-command")
    assert result.returncode == 2
    combined = result.stdout + result.stderr
    assert "definitely-not-a-command" in combined
    assert "unknown command" in combined


def test_help_lists_every_command():
    result = run_module("--help")
    assert result.returncode == 0
    for name in _COMMANDS:
        assert name in result.stdout, f"{name} missing from usage output"


@pytest.mark.parametrize("command", sorted(_COMMANDS))
def test_every_command_is_reachable(command):
    """--help must reach the command's own parser, not the dispatcher's."""
    result = run_module(command, "--help")
    assert result.returncode == 0, result.stderr
    assert f"repro-{command}" in result.stdout, (
        "the subcommand's parser should report the name a user typed"
    )


# --- main() as a function --------------------------------------------------


def test_main_returns_status_rather_than_exiting():
    """Returning keeps it testable; sys.exit in a library is a trap."""
    assert main(["definitely-not-a-command"]) == 2


def test_main_does_not_mutate_sys_argv():
    """It rewrites sys.argv for argparse and must put it back.

    Otherwise a second call in the same process -- or a test running after
    one -- sees a corrupted argv.
    """
    before = list(sys.argv)
    main(["definitely-not-a-command"])
    assert sys.argv == before


# --- the two ways in must stay in step -------------------------------------


def test_every_console_script_has_a_module_command():
    """`repro-publish` and `python -m repro_tools.cli publish` are one feature.

    They dispatch to the same functions on purpose. If a console script is
    added without a dispatcher entry, Makefiles calling the module form get the
    old silent-no-op behavior for that command only, which is far harder to
    notice than a total failure.
    """
    scripts = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["scripts"]
    targets = {value.split(":", 1)[1] for value in scripts.values()}
    dispatched = {func.__name__ for func in _COMMANDS.values()}
    missing = targets - dispatched
    assert not missing, (
        f"console scripts with no `python -m` equivalent: {sorted(missing)}"
    )
