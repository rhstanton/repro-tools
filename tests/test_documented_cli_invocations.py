"""Every repro-* command shown in the docs must actually parse.

WHY

README.md, docs/README.md and docs/MIGRATION.md all documented a CLI that did
not exist. Measured 2026-08-17, the published examples used:

    repro-publish analyses --paper-root paper --names "price_base remodel_base" \
        --require-current-head

against a command whose analyses are POSITIONAL (there is no --names), whose
--project-root is required and was absent, and whose --require-current-head
takes an int rather than being a bare flag. docs/MIGRATION.md used --kinds where
the option is --kind.

Nobody noticed because nothing ever ran them, and because project Makefiles
invoked the CLI through `python -m repro_tools.cli`, which had no entry point
and so accepted anything at all. Wrong documentation and a CLI that could not
reject wrong input are the same failure seen twice.

These are public archives. A reader who types what the README shows must get the
behavior it describes, and if they do not, that is a defect in the repository
rather than a mistake by the reader.

WHAT THIS CHECKS, AND WHAT IT DOES NOT

Every long option in a documented invocation is checked against that
subcommand's real `--help` output. Values are not executed -- nothing here
publishes, clones or writes -- so this catches names that do not exist, which is
the entire class of error found above. It does not check that a documented
command would succeed with real data.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
DOCS = [REPO / "README.md", REPO / "docs" / "README.md", REPO / "docs" / "MIGRATION.md"]

# Console script name -> `python -m repro_tools.cli` subcommand.
SCRIPT_TO_COMMAND = {
    "repro-record": "record",
    "repro-publish": "publish",
    "repro-compare": "compare",
    "repro-sysinfo": "sysinfo",
    "repro-check": "check",
    "repro-report": "report",
    "repro-template-diff": "template-diff",
}


def join_continuations(text: str) -> str:
    """Fold shell line continuations so one invocation is one line."""
    return re.sub(r"\\\n\s*", " ", text)


def documented_invocations() -> list[tuple[str, str, str]]:
    """(source file, script name, full command line) for each documented call."""
    found = []
    for path in DOCS:
        if not path.is_file():
            continue
        text = join_continuations(path.read_text())
        for line in text.splitlines():
            stripped = line.strip().lstrip("$").strip()
            # Makefile examples embed the module form; treat it the same way.
            stripped = stripped.replace(
                "$(PYTHON) -m repro_tools.cli ", "repro-"
            ).replace("python -m repro_tools.cli ", "repro-")
            for script in SCRIPT_TO_COMMAND:
                if stripped.startswith(script + " ") or stripped == script:
                    found.append((path.name, script, stripped))
                    break
    return found


def help_text(command: str, subcommand: str | None = None) -> str:
    args = [command] + ([subcommand] if subcommand else []) + ["--help"]
    result = subprocess.run(
        [sys.executable, "-m", "repro_tools.cli", *args],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"},
        timeout=120,
    )
    assert result.returncode == 0, f"{args} failed: {result.stderr}"
    return result.stdout


def test_the_docs_contain_invocations_to_check():
    """Guard the guard: a parser that finds nothing would pass silently."""
    invocations = documented_invocations()
    assert len(invocations) >= 5, (
        f"only found {len(invocations)} documented repro-* invocations; "
        "the doc parser is probably broken rather than the docs being empty"
    )


@pytest.mark.parametrize(
    "source,script,line",
    [(s, k, ln) for s, k, ln in documented_invocations()],
    ids=lambda v: v if isinstance(v, str) and len(v) < 40 else "",
)
def test_documented_options_exist(source, script, line):
    """Every --option in a documented command must appear in its --help."""
    tokens = line.split()
    command = SCRIPT_TO_COMMAND[tokens[0]]

    # A leading non-option token is a subcommand (publish analyses / files).
    subcommand = None
    if len(tokens) > 1 and not tokens[1].startswith("-"):
        candidate = tokens[1]
        if candidate in {"analyses", "files"}:
            subcommand = candidate

    text = help_text(command, subcommand)

    for token in tokens[1:]:
        if not token.startswith("--"):
            continue
        option = token.split("=", 1)[0]
        # Makefile variables such as $(PUBLISH_ANALYSES) are values, not options.
        if "$" in option:
            continue
        assert option in text, (
            f"{source} documents `{option}` for `{script}"
            f"{' ' + subcommand if subcommand else ''}`, which does not accept it.\n"
            f"Documented line: {line}\n"
            f"Real usage:\n{text.splitlines()[0] if text else '(none)'}"
        )


def test_no_doc_uses_the_removed_names_option():
    """--names and --kinds never existed; both appeared in published examples.

    Kept as an explicit check because these are the exact strings that were
    wrong, and a reader copying them got an argparse error with no clue that
    the documentation, not their typing, was at fault.
    """
    for path in DOCS:
        if not path.is_file():
            continue
        text = path.read_text()
        for bad in ("--names ", "--kinds "):
            assert bad not in text, f"{path.name} still documents {bad.strip()}"
