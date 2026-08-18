"""The shared Stata rules, and the mistakes they are shaped by.

lib/stata.mk was hoisted out of project_template and fire on 2026-08-18. The two
copies had stayed almost identical while the Python and Julia sections around
them diverged: stata-requirements shared 23 of 25 recipe lines, stata-check 17
of 25, stata-vendored-clean 14 of 16, and the package stamp rule, stata-update
and $(STATA_LOCAL) were byte-identical.

It is also the half carrying the most easily-broken logic, which is the argument
for one copy rather than two:

  * SSC has no versioned install. `ssc install estout 3.1.2` is not "install
    version 3.1.2" -- in one project it silently installed whatever was current
    while printing the version it had been asked for, and in another it was a
    syntax error (varlist not allowed, r(101)) so nothing installed at all.
    Real pinning means vendoring .stata/ado/plus into git.
  * Stata exits 0 even when a do-file aborts, so the exit status cannot be
    trusted; the log has to be read.
  * The original rule wrapped everything in `cap noi`, sent output to
    /dev/null, appended `|| true` and touched the stamp regardless -- so
    "All Stata packages installed" printed on a machine with no Stata.

These tests pin the shape of the recipes rather than running Stata, so they run
anywhere. Anything that executes Stata belongs in a project, not here.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

STATA_MK = Path(__file__).resolve().parents[1] / "src/repro_tools/lib/stata.mk"

EXPECTED_TARGETS = [
    "stata-env",
    "stata-requirements",
    "stata-vendored-clean",
    "stata-check",
    "stata-update",
    "stata-clean",
    "stata-list",
]


@pytest.fixture(scope="module")
def text() -> str:
    return STATA_MK.read_text()


def recipe(text: str, target: str) -> str:
    """The recipe body of one target, comments stripped."""
    match = re.search(rf"^{re.escape(target)}:.*\n((?:\t.*\n)+)", text, re.MULTILINE)
    assert match, f"no recipe found for {target}"
    return "\n".join(
        line.strip()
        for line in match.group(1).splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


class TestStructure:
    @pytest.mark.parametrize("target", EXPECTED_TARGETS)
    def test_target_is_defined(self, text, target):
        assert re.search(rf"^{re.escape(target)}:", text, re.MULTILINE)

    @pytest.mark.parametrize("target", EXPECTED_TARGETS)
    def test_target_is_phony(self, text, target):
        assert re.search(rf"^\.PHONY:.*\b{re.escape(target)}\b", text, re.MULTILINE)

    def test_paths_are_parameterized(self, text):
        """A hoisted file must not hard-code one project's layout."""
        assert "STATA_DIR ?=" in text
        assert "STATA ?=" in text
        assert "../.stata/" not in text, (
            "a literal ../.stata path survived the hoist; use $(STATA_DIR)"
        )

    def test_stata_binary_is_not_hard_coded(self, text):
        """`stata-mp` may appear only as the default of the STATA variable.

        Anywhere else it is a hard-coded binary a project cannot override --
        which matters because Stata ships as stata-mp, stata-se and stata-be,
        and a site licence decides which one exists.
        """
        offenders = [
            line
            for line in text.splitlines()
            if "stata-mp" in line
            and not line.strip().startswith("#")
            and not line.startswith("STATA ?=")
        ]
        assert not offenders, f"hard-coded stata-mp: {offenders}"


class TestInstallRuleLessons:
    """Each assertion here corresponds to a defect that shipped once."""

    def test_ssc_install_carries_no_version(self, text):
        """SSC is unversioned; a version argument is a syntax error or a lie."""
        assert "ssc install $*, replace all" in text
        assert not re.search(r"ssc install \$\* [0-9]", text)

    def test_the_log_is_read_rather_than_the_exit_status(self, text):
        """Stata returns 0 even when a do-file aborts."""
        stamp = recipe(text, r"$(STATA_DIR)/.%.stamp")
        assert "install.log" in stamp
        assert "r([0-9]+);" in stamp or "r\\([0-9]+\\);" in stamp

    def test_a_missing_stata_binary_is_an_error(self, text):
        """It used to print success on a machine with no Stata at all."""
        stamp = recipe(text, r"$(STATA_DIR)/.%.stamp")
        assert "command -v" in stamp
        assert "exit 1" in stamp

    def test_installation_is_verified_on_disk(self, text):
        """ "Installed without error" is not the same as "the .ado is there"."""
        stamp = recipe(text, r"$(STATA_DIR)/.%.stamp")
        assert ".ado" in stamp
        assert "is not in" in stamp or "ERROR" in stamp

    def test_the_stamp_is_not_touched_unconditionally(self, text):
        """The original touched it regardless, so make never retried."""
        stamp = recipe(text, r"$(STATA_DIR)/.%.stamp")
        lines = stamp.splitlines()
        touches = [i for i, line in enumerate(lines) if line.startswith("touch $@")]
        assert touches, "the stamp is never written"
        # The FIRST touch is the vendored-package early exit, which is a
        # legitimate success path and correctly does no install. The one that
        # matters is the LAST: it must be reachable only after every check.
        assert any("exit 1" in line for line in lines[: touches[-1]]), (
            "nothing can fail before the install path touches the stamp"
        )

    def test_vendored_tree_is_checked_against_git(self, text):
        """The only real pinning available: compare the depot with HEAD."""
        body = recipe(text, "stata-vendored-clean")
        assert "git" in body and "diff" in body

    def test_stata_check_depends_on_the_vendored_check(self, text):
        assert re.search(r"^stata-check:.*stata-vendored-clean", text, re.MULTILINE)


class TestItParses:
    def test_make_can_read_the_file(self, tmp_path):
        """A syntax error here would break every project that includes it."""
        makefile = tmp_path / "Makefile"
        makefile.write_text(
            f"STATA_DIR := {tmp_path}/.stata\ninclude {STATA_MK}\n\nnoop:\n\t@true\n"
        )
        result = subprocess.run(
            ["make", "-n", "noop"], cwd=tmp_path, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("target", ["stata-clean", "stata-list"])
    def test_targets_expand_with_an_overridden_stata_dir(self, tmp_path, target):
        """Proves the parameterization works, not just that it is written."""
        depot = tmp_path / "custom-depot"
        makefile = tmp_path / "Makefile"
        makefile.write_text(f"STATA_DIR := {depot}\ninclude {STATA_MK}\n")
        result = subprocess.run(
            ["make", "-n", target], cwd=tmp_path, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        assert str(depot) in result.stdout, (
            f"{target} did not honor the overridden STATA_DIR"
        )
