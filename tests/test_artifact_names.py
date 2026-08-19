"""`repro-tools check` must be able to learn what a project should have built.

The defect this guards: the artifact list was found by regexing the root
Makefile for a line starting `ANALYSES`. That works only when the list is
literal and lives at the root. fire assembles it from
`$(REMODEL_ANALYSES) $(MORTGAGE_ANALYSES) ...` inside housing-analysis/Makefile,
so the regex found nothing and the check downgraded itself to a warning --
"Could not determine artifact list" -- rather than failing. A check that stops
checking and still passes is the failure mode this package exists to remove.

Measured 2026-08-19 against fire: `make -s list-analyses-names` yields 43 names,
the regex yields none.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from repro_tools.presubmit import PreSubmitChecker

pytestmark = pytest.mark.skipif(
    shutil.which("make") is None, reason="make not installed"
)


def _checker(root):
    return PreSubmitChecker(root)


def test_make_target_is_preferred_over_the_regex(tmp_path):
    """A composed list is unparseable by regex and correct via make."""
    (tmp_path / "Makefile").write_text(
        "GROUP_A := alpha beta\n"
        "GROUP_B := gamma\n"
        "ANALYSES := $(GROUP_A) $(GROUP_B)\n"
        ".PHONY: list-analyses-names\n"
        "list-analyses-names:\n"
        "\t@$(foreach a,$(ANALYSES),echo $(a);)\n"
    )
    assert _checker(tmp_path)._artifact_names() == ["alpha", "beta", "gamma"]


def test_falls_back_to_the_makefile_when_the_target_is_absent(tmp_path):
    """Projects that do not include common.mk still get the old behavior."""
    (tmp_path / "Makefile").write_text("ANALYSES := alpha beta\nall:\n\t@true\n")
    assert _checker(tmp_path)._artifact_names() == ["alpha", "beta"]


def test_fallback_discards_unexpanded_variable_references(tmp_path):
    """`$(GROUP_A)` is not an artifact name.

    The old code returned it as one, so downstream the checker looked for
    output/figures/$(GROUP_A).pdf and reported it missing -- a wrong answer
    dressed as a real one.
    """
    (tmp_path / "Makefile").write_text(
        "ANALYSES := $(GROUP_A) literal\nall:\n\t@true\n"
    )
    assert _checker(tmp_path)._artifact_names() == ["literal"]


def test_no_makefile_and_no_make_target_yields_empty(tmp_path):
    assert _checker(tmp_path)._artifact_names() == []


def test_a_failing_make_does_not_crash_the_check(tmp_path):
    """A Makefile with a syntax error must degrade, not raise."""
    (tmp_path / "Makefile").write_text("this is not a makefile\n\tindented nonsense\n")
    assert _checker(tmp_path)._artifact_names() == []


def test_the_shared_target_exists_in_the_shared_machinery():
    """The contract lives in the shared machinery, so every project inherits it.

    Searches all of lib/*.mk rather than naming common.mk: the split on
    2026-08-19 moved this target into layout.mk, and a test that hardcodes a
    filename fails on a reorganization that changed nothing it was testing.
    """
    from repro_tools.core import lib_dir

    defining = [
        mk.name
        for mk in sorted(lib_dir().glob("*.mk"))
        if "list-analyses-names:" in mk.read_text()
    ]
    assert defining, "no lib/*.mk defines list-analyses-names"
    assert len(defining) == 1, f"defined in more than one layer: {defining}"


def test_the_target_prints_bare_names_only(tmp_path):
    """No header, no bullets -- parsing a display format is what this replaces."""
    (tmp_path / "Makefile").write_text(
        "ANALYSES := alpha beta\n"
        ".PHONY: list-analyses-names\n"
        "list-analyses-names:\n"
        "\t@$(foreach a,$(ANALYSES),echo $(a);)\n"
    )
    out = subprocess.run(
        ["make", "-s", "--no-print-directory", "list-analyses-names"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.stdout == "alpha\nbeta\n"


def test_an_empty_analyses_list_prints_nothing(tmp_path):
    """`printf '%s\\n' $(ANALYSES)` would emit a blank line here and be read as
    one nameless artifact."""
    (tmp_path / "Makefile").write_text(
        "ANALYSES :=\n"
        ".PHONY: list-analyses-names\n"
        "list-analyses-names:\n"
        "\t@$(foreach a,$(ANALYSES),echo $(a);)\n"
    )
    assert _checker(tmp_path)._artifact_names() == []
