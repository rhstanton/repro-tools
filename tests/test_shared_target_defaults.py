"""Every command a shared target runs must have a default.

An undefined make variable expands to the empty string. It is not an error, and
make happily runs the result. So a shared target written as

    pre-submit:
        @echo "Running pre-submission checklist..."
        @$(REPRO_CHECK)

prints its banner, executes nothing, and exits 0 in any project that does not
define REPRO_CHECK. project_template defines it, so the split that moved these
targets into repro.mk looked fine there; fire does not, and `make pre-submit`
became a pre-submission check that ran nothing and reported success.

That is the failure this package exists to remove, introduced by the very change
meant to make the targets portable. These tests assert every such variable is
defaulted in the file that uses it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

LIB = Path(__file__).resolve().parents[1] / "src/repro_tools/lib"
LAYERS = ("tools.mk", "repro.mk", "git.mk", "layout.mk")

# Variables a consuming project is expected to define itself.
PROJECT_PROVIDED = {
    "PYTHON",
    "JULIA",
    "STATA",
    "NOTEBOOK",
    "DATA",
    "ANALYSES",
    "MAKE",
    "CURDIR",
    "MAKEFILE_LIST",
    "REPRO_LIB_DIR",
}
# Deliberate pass-throughs: the user supplies them on the command line
# (`make template-diff ARGS="--apply"`) and empty is the correct default.
PASS_THROUGH = {"ARGS"}
VAR = re.compile(r"\$\(([A-Z][A-Z0-9_]*)\)")
DEFAULT = re.compile(r"^([A-Z][A-Z0-9_]*)\s*\?=", re.M)


@pytest.mark.parametrize("layer", LAYERS)
def test_every_variable_used_in_a_recipe_has_a_default(layer):
    text = (LIB / layer).read_text()
    defaulted = set(DEFAULT.findall(text))
    # Every non-comment line, not only recipes. A variable can also appear in a
    # prerequisite list -- `check: $(CHECK_DEPS)`, `test: $(TEST_DEPS)` -- and an
    # undefined one there silently reduces the target to no prerequisites, which
    # is the same defect wearing different clothes: the gate still passes, having
    # checked less than it claims.
    used = set()
    for line in text.split("\n"):
        if line.lstrip().startswith("#"):
            continue
        used |= set(VAR.findall(line))
    undefaulted = sorted(
        used
        - defaulted
        - PROJECT_PROVIDED
        - PASS_THROUGH
        - {
            "OUT_FIG_DIR",
            "OUT_TBL_DIR",
            "OUT_PROV_DIR",
            "OUT_LOG_DIR",
            "OUT_EXEC_NB_DIR",
            "JULIA_NUM_THREADS",
        }
    )
    assert not undefaulted, (
        f"{layer} runs $({'), $('.join(undefaulted)}) with no ?= default; "
        "in a project that does not define it, the recipe executes the empty "
        "string and the target passes having done nothing"
    )


def test_repro_check_is_defaulted():
    """The specific regression: pre-submit ran nothing and exited 0."""
    assert re.search(r"^REPRO_CHECK\s*\?=", (LIB / "repro.mk").read_text(), re.M)


def test_an_undefined_command_variable_would_pass_silently(tmp_path):
    """Demonstrates why the rule is needed, rather than asserting it abstractly.

    If this ever fails, make has started treating an empty recipe as an error
    and the rule above could be relaxed.
    """
    (tmp_path / "Makefile").write_text(
        'demo:\n\t@echo "Running the check..."\n\t@$(NEVER_DEFINED)\n'
    )
    out = subprocess.run(
        ["make", "demo"], cwd=tmp_path, capture_output=True, text=True, timeout=60
    )
    assert out.returncode == 0
    assert "Running the check..." in out.stdout
