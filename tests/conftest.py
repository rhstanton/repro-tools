"""Fail loudly if the tests are not testing this checkout.

WHY THIS EXISTS

On 2026-08-17 the suite was run from a shell whose PATH and VIRTUAL_ENV pointed
at a *different* project's venv (fire's). `import repro_tools` resolved to

    ~/01_work/research/fire/.venv/lib/python3.12/site-packages/repro_tools/

so the suite exercised that project's installed snapshot while appearing to
test the working tree. Source edits had no effect on the result, and a "64
passed" was recorded as evidence for a fix the tests had never executed.

This is the same class of defect as a check that cannot fail: the suite ran, it
was green, and the green meant nothing. It is easy to hit because repro-tools
is normally a submodule inside a project that installs it -- so the wrong copy
is not merely present, it is the one on the path by default.

Comparing resolved paths is the whole check. If `repro_tools` is imported from
anywhere other than this repository, stop rather than report a verdict about
code nobody has run.

    PYTHONPATH=src python3 -m pytest tests/
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def pytest_configure(config: pytest.Config) -> None:
    try:
        import repro_tools
    except ImportError:  # pragma: no cover - the suite cannot run at all
        return

    imported = Path(repro_tools.__file__).resolve()
    expected = (REPO / "src" / "repro_tools").resolve()

    if expected not in imported.parents:
        raise pytest.UsageError(
            "repro_tools was imported from a different checkout, so this suite "
            "would be testing code that is not in this working tree.\n"
            f"  imported from: {imported}\n"
            f"  expected under: {expected}\n"
            f"  sys.executable: {sys.executable}\n"
            "Run with the source on the path:\n"
            "  PYTHONPATH=src python3 -m pytest tests/\n"
            "or install this checkout in the active environment:\n"
            "  python3 -m pip install -e ."
        )
