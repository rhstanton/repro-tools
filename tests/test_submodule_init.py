"""`make init-submodules` must fail when submodule init actually fails.

The recipe used to be:

    @git submodule update --init --recursive 2>/dev/null || true

which discarded stderr and the exit status, so an unreachable URL, a private
repo without credentials, and a clean success were indistinguishable. The build
continued against submodules that were not on disk, and the real failure
surfaced much later as a missing import -- somewhere giving no hint the cause
was a swallowed clone.

Measured 2026-08-17 on a repo whose .gitmodules points at a nonexistent URL:
the old recipe exited 0 and printed nothing; the new one exits 2 and says why.

The distinction the recipe has to preserve is that "nothing to initialize" and
"initialization failed" are different, and only the first is fine. So all three
paths are tested, not just the one that was broken.

Note for anyone extending this: a `.gitmodules` entry ALONE is not enough to
make git do anything. Git acts on the gitlink in the index, so the fixture has
to `update-index --cacheinfo 160000,...`. Without it `git submodule update`
exits 0 having correctly done nothing, and a test built that way passes against
the broken recipe too -- which is how the first version of this test fooled us.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

COMMON_MK = Path(__file__).resolve().parents[1] / "src/repro_tools/lib/common.mk"

OLD_RECIPE = (
    "init-submodules:\n\t@git submodule update --init --recursive 2>/dev/null || true\n"
)


def _recipe() -> str:
    """Extract the init-submodules target from common.mk verbatim."""
    text = COMMON_MK.read_text()
    m = re.search(r"^init-submodules:\n(?:\t.*\n)+", text, re.MULTILINE)
    assert m, "init-submodules target not found in common.mk"
    return m.group(0)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _make(repo: Path, recipe: str) -> subprocess.CompletedProcess:
    """Run the recipe in a make that is not talking to an outer make.

    These tests are themselves usually run from `make test`, so without this the
    nested make inherits MAKEFLAGS/MAKELEVEL, decides it is recursive, and
    prints its own "Entering directory"/"Leaving directory" lines into stdout.
    That is make talking about make; it says nothing about the recipe. Stripping
    those variables and passing --no-print-directory keeps the captured output
    to what the recipe itself emitted.
    """
    (repo / "Makefile").write_text(recipe)
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"MAKEFLAGS", "MAKELEVEL", "MFLAGS"}
    }
    return subprocess.run(
        ["make", "--no-print-directory", "init-submodules"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def _recipe_output(result: subprocess.CompletedProcess) -> str:
    """Output the recipe produced, with any residual make chatter removed."""
    lines = [
        ln for ln in result.stdout.splitlines() if not ln.startswith(("make[", "make:"))
    ]
    return "\n".join(lines).strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "proj"
    repo.mkdir()
    _git(repo, "init", "-q", ".")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (repo / "README.md").write_text("x\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "init")
    return repo


def _declare_broken_submodule(repo: Path) -> None:
    (repo / ".gitmodules").write_text(
        '[submodule "nope"]\n'
        "\tpath = lib/nope\n"
        "\turl = https://github.com/rhstanton/no-such-repo-xyzzy.git\n"
    )
    _git(repo, "add", ".gitmodules")
    # The gitlink is what git actually acts on -- see the module docstring.
    _git(
        repo,
        "update-index",
        "--add",
        "--cacheinfo",
        "160000,0000000000000000000000000000000000000001,lib/nope",
    )
    _git(repo, "commit", "-qm", "declare submodule")


def test_no_gitmodules_is_silent_success(tmp_path):
    """A project with no submodules has nothing to do, and says nothing."""
    result = _make(_repo(tmp_path), _recipe())
    assert result.returncode == 0
    assert _recipe_output(result) == ""


@pytest.mark.slow
def test_unfetchable_submodule_fails_loudly(tmp_path):
    """The regression: a declared submodule that cannot be fetched must fail."""
    repo = _repo(tmp_path)
    _declare_broken_submodule(repo)
    result = _make(repo, _recipe())
    assert result.returncode != 0, (
        "init-submodules exited 0 despite an unfetchable submodule; "
        "the failure is being swallowed again"
    )
    assert "submodule update failed" in result.stdout + result.stderr


@pytest.mark.slow
def test_old_recipe_would_have_passed(tmp_path):
    """Guard the guard: prove this fixture can tell the two recipes apart.

    Without this, a fixture that silently stopped provoking a failure would
    make the test above pass for the wrong reason -- which is exactly what
    happened before the gitlink was added.
    """
    repo = _repo(tmp_path)
    _declare_broken_submodule(repo)
    assert _make(repo, OLD_RECIPE).returncode == 0
