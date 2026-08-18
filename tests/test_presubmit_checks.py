"""Tests for the pre-submission checklist.

This code had never run. `make pre-submit` invoked it through
`$(PYTHON) -m repro_tools.cli check`, and cli.py had no __main__ block, so the
command imported the module and exited 0 without calling anything. The first
real execution, on 2026-08-17, crashed immediately:

    ValueError: stdout and stderr arguments may not be used with capture_output.

That line had been there since the file was written. Two more defects were
visible in the first run that completed:

  * `Tests Pass` ran the project's whole suite with a hard-coded 60 second
    timeout. This template's own suite takes about six minutes, so the check
    reported "Tests timed out" every time. A check that always fails is as
    useless as one that can never fail, and teaches people to ignore the report.
  * `Data Checksums` collapsed every failure into one boolean and reported
    "Some data files don't match checksums / Check data/CHECKSUMS.txt" -- not
    which file, not whether it was missing or altered, not what the hashes were.

Code that has never executed is not tested code, whatever its coverage number
says, so these tests exercise the check methods directly against fixtures.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from repro_tools.presubmit import CheckResult, PreSubmitChecker


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "data").mkdir()
    return tmp_path


def write_data(project: Path, name: str, content: str) -> Path:
    path = project / "data" / name
    path.write_text(content)
    return path


def write_checksums(project: Path, entries: dict[str, str]) -> None:
    lines = ["# SHA256 Checksums", ""]
    lines += [f"{digest}  {name}" for name, digest in entries.items()]
    (project / "data" / "CHECKSUMS.txt").write_text("\n".join(lines) + "\n")


def result_named(checker: PreSubmitChecker, name: str) -> CheckResult:
    matches = [r for r in checker.results if r.name == name]
    assert matches, f"no check named {name!r} in {[r.name for r in checker.results]}"
    return matches[-1]


class TestGitStatusDoesNotCrash:
    """The ValueError that the dead entry point had been hiding."""

    def test_check_git_status_runs(self, project):
        subprocess.run(["git", "init", "-q", "."], cwd=project, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@example.com"], cwd=project, check=True
        )
        subprocess.run(["git", "config", "user.name", "T"], cwd=project, check=True)
        (project / "README.md").write_text("x\n")
        subprocess.run(["git", "add", "-A"], cwd=project, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=project, check=True)

        checker = PreSubmitChecker(project)
        checker.check_git_status()  # must not raise
        assert checker.results

    def test_no_upstream_is_survivable(self, project):
        """A branch with no upstream is the normal state on a CI runner.

        `git rev-list @{u}..HEAD` fails there, which is expected and must not
        crash or be reported as a repository problem.
        """
        subprocess.run(["git", "init", "-q", "."], cwd=project, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@example.com"], cwd=project, check=True
        )
        subprocess.run(["git", "config", "user.name", "T"], cwd=project, check=True)
        (project / "README.md").write_text("x\n")
        subprocess.run(["git", "add", "-A"], cwd=project, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=project, check=True)

        checker = PreSubmitChecker(project)
        checker.check_git_status()
        assert not any("@{u}" in (r.details or "") for r in checker.results)


class TestDataChecksums:
    def test_all_matching_passes(self, project):
        path = write_data(project, "a.csv", "1,2\n")
        write_checksums(project, {"a.csv": sha256(path)})

        checker = PreSubmitChecker(project)
        checker.check_data_files()
        assert result_named(checker, "Data Checksums").passed

    def test_changed_file_is_reported_by_name_and_hash(self, project):
        path = write_data(project, "a.csv", "1,2\n")
        recorded = sha256(path)
        path.write_text("9,9\n")  # the change
        write_checksums(project, {"a.csv": recorded})

        checker = PreSubmitChecker(project)
        checker.check_data_files()
        result = result_named(checker, "Data Checksums")

        assert not result.passed
        assert "1 changed" in result.message
        assert "a.csv" in result.details
        assert recorded[:16] in result.details, "the recorded hash should be shown"

    def test_missing_and_changed_are_distinguished(self, project):
        """Different problems with different fixes; one boolean cannot say which."""
        path = write_data(project, "present.csv", "1\n")
        recorded = sha256(path)
        path.write_text("2\n")
        write_checksums(project, {"present.csv": recorded, "gone.csv": "0" * 64})

        checker = PreSubmitChecker(project)
        checker.check_data_files()
        result = result_named(checker, "Data Checksums")

        assert "1 missing" in result.message
        assert "1 changed" in result.message
        assert "missing: gone.csv" in result.details
        assert "changed: present.csv" in result.details

    def test_details_say_what_to_do_about_it(self, project):
        path = write_data(project, "a.csv", "1\n")
        recorded = sha256(path)
        path.write_text("2\n")
        write_checksums(project, {"a.csv": recorded})

        checker = PreSubmitChecker(project)
        checker.check_data_files()
        details = result_named(checker, "Data Checksums").details
        assert "invalidates every result" in details

    def test_absent_checksums_file_is_a_warning_not_a_pass(self, project):
        checker = PreSubmitChecker(project)
        checker.check_data_files()
        result = result_named(checker, "Data Checksums")
        assert result.passed is True  # non-strict
        assert result.warning is True, "a missing CHECKSUMS.txt must not show a tick"

    def test_absent_checksums_file_fails_in_strict_mode(self, project):
        checker = PreSubmitChecker(project, strict=True)
        checker.check_data_files()
        assert not result_named(checker, "Data Checksums").passed


class TestTestTimeout:
    def test_default_is_long_enough_for_a_real_suite(self):
        """60 seconds could not pass. The default must fit an actual project.

        This template's suite takes ~356s; fire's takes longer still.
        """
        assert PreSubmitChecker.DEFAULT_TEST_TIMEOUT >= 600

    def test_timeout_is_configurable(self, project):
        checker = PreSubmitChecker(project, test_timeout=1234)
        assert checker.test_timeout == 1234

    def test_timeout_message_names_the_limit(self, project, monkeypatch):
        """ "Tests timed out" alone does not tell you what to change."""
        (project / "tests").mkdir()

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=7)

        monkeypatch.setattr(subprocess, "run", fake_run)
        checker = PreSubmitChecker(project, test_timeout=7)
        checker.check_tests()
        result = result_named(checker, "Tests Pass")
        assert not result.passed
        assert "7s" in result.message
        assert "--test-timeout" in result.details


class TestWarningRendering:
    def test_warning_defaults_to_false(self):
        assert CheckResult("x", True).warning is False

    def test_passed_with_warning_is_representable(self):
        result = CheckResult("x", True, "stale", warning=True)
        assert result.passed and result.warning

    def test_strict_mode_turns_warnings_into_failures(self, project):
        """The contract behind `passed = not self.strict`."""
        strict = PreSubmitChecker(project, strict=True)
        strict.check_data_files()
        lenient = PreSubmitChecker(project)
        lenient.check_data_files()

        assert not result_named(strict, "Data Checksums").passed
        assert result_named(lenient, "Data Checksums").passed
