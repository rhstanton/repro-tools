#!/usr/bin/env python3
"""
pre_submit_check.py

Comprehensive pre-publication checklist.
Runs all checks to ensure package is ready for journal submission.

Usage:
    python scripts/pre_submit_check.py [--strict]
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

from repro_tools.core import resolve_recorded_path


class CheckResult:
    """Result of a check.

    `warning` marks a check that passes only because strict mode is off. It
    exists because the output was actively misleading without it: a stale
    provenance record is recorded as `passed = not self.strict`, so a
    non-strict run printed

        ✅ Provenance Current    5 artifacts from old commits

    a green tick beside a sentence saying the artifacts do not match HEAD. The
    verdict was defensible -- non-strict pre-submit is advisory -- but the glyph
    claimed something the message denied, and the glyph is what people read.
    """

    def __init__(self, name, passed, message="", details="", warning=False):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details
        self.warning = warning


class PreSubmitChecker:
    """Pre-submission checklist runner."""

    # Seconds allowed for the project's whole test suite. The old value was a
    # hard-coded 60, which no real research project can meet -- this template's
    # own suite takes about six minutes -- so "Tests Pass" reported "Tests timed
    # out" on every run. A check that always fails teaches people to ignore the
    # report, which costs as much as one that can never fail.
    DEFAULT_TEST_TIMEOUT = 900

    def __init__(self, repo_root, strict=False, test_timeout=DEFAULT_TEST_TIMEOUT):
        self.repo_root = Path(repo_root)
        self.strict = strict
        self.test_timeout = test_timeout
        self.results = []

    def run_all_checks(self):
        """Run all pre-submission checks."""
        print("=" * 60)
        print("PRE-SUBMISSION CHECKLIST")
        print("=" * 60)
        print()

        self.check_git_status()
        self.check_environment()
        self.check_data_files()
        self.check_artifacts_built()
        self.check_provenance()
        self.check_checksums()
        self.check_documentation()
        self.check_tests()

        return self.print_summary()

    def check_git_status(self):
        """Check git repository status."""
        print("📝 Checking Git Status...")

        # Check if git repo
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=5,
            )
            if result.returncode != 0:
                self.results.append(
                    CheckResult(
                        "Git Repository",
                        False,
                        "Not a git repository",
                    )
                )
                return
        except Exception as e:
            self.results.append(
                CheckResult(
                    "Git Repository",
                    False,
                    f"Error: {e}",
                )
            )
            return

        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=self.repo_root,
        )

        if result.stdout.strip():
            self.results.append(
                CheckResult(
                    "Clean Working Tree",
                    not self.strict,
                    "Uncommitted changes detected",
                    result.stdout.strip()[:200],
                    warning=not self.strict,
                )
            )
        else:
            self.results.append(
                CheckResult(
                    "Clean Working Tree",
                    True,
                    "No uncommitted changes",
                )
            )

        # Check if behind upstream
        # capture_output=True already redirects both streams; passing stderr=
        # as well raises ValueError before git is even spawned:
        #   "stdout and stderr arguments may not be used with capture_output."
        # stderr is captured rather than discarded because this command fails
        # routinely and for an ordinary reason -- @{u} does not resolve when the
        # branch has no upstream, which is the normal state on a CI runner --
        # and the message is worth having when diagnosing.
        #
        # This line had never executed. `make pre-submit` reached it only after
        # cli.py gained a __main__ block on 2026-08-17; before that the whole
        # command was an import that exited 0.
        result = subprocess.run(
            ["git", "rev-list", "--count", "@{u}..HEAD"],
            capture_output=True,
            text=True,
            cwd=self.repo_root,
        )

        if result.returncode == 0:
            ahead = int(result.stdout.strip())

            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD..@{u}"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
            )
            behind = int(result.stdout.strip())

            if behind > 0:
                self.results.append(
                    CheckResult(
                        "Up to Date with Remote",
                        not self.strict,
                        f"Behind upstream by {behind} commit(s)",
                        warning=not self.strict,
                    )
                )
            else:
                self.results.append(
                    CheckResult(
                        "Up to Date with Remote",
                        True,
                        f"Ahead by {ahead}, behind by 0",
                    )
                )
        else:
            self.results.append(
                CheckResult(
                    "Up to Date with Remote",
                    True,
                    "No upstream configured (OK)",
                )
            )

    def check_environment(self):
        """Check environment is set up."""
        print("🔧 Checking Environment...")

        # .venv first, .env second. The conda-era `.env` was the ONLY path
        # checked until 2026-08-19, so this reported "Python environment not
        # found" for every uv project -- which is all of them since the
        # migration. It went unnoticed because one repository still had a stale
        # 2.4 GB conda .env/ from February sitting in its working copy, so the
        # check passed there and nowhere else. Deleting that directory is what
        # exposed it.
        candidates = [
            self.repo_root / ".venv" / "bin" / "python",
            self.repo_root / ".env" / "bin" / "python",
        ]
        found = next((c for c in candidates if c.exists()), None)
        if found:
            where = found.relative_to(self.repo_root)
            self.results.append(
                CheckResult(
                    "Python Environment",
                    True,
                    f"Python environment exists ({where})",
                )
            )
        else:
            self.results.append(
                CheckResult(
                    "Python Environment",
                    False,
                    "Python environment not found",
                    "Looked for .venv/bin/python and .env/bin/python. "
                    "Run: make environment",
                )
            )

        julia_dir = self.repo_root / ".julia" / "pyjuliapkg"
        if julia_dir.exists():
            self.results.append(
                CheckResult(
                    "Julia Environment",
                    True,
                    "Julia installed",
                )
            )
        else:
            self.results.append(
                CheckResult(
                    "Julia Environment",
                    not self.strict,
                    "Julia not installed (optional)",
                    warning=not self.strict,
                )
            )

    def check_data_files(self):
        """Check data files exist and match checksums."""
        print("📊 Checking Data Files...")

        data_dir = self.repo_root / "data"
        checksums_file = data_dir / "CHECKSUMS.txt"

        if not checksums_file.exists():
            self.results.append(
                CheckResult(
                    "Data Checksums",
                    not self.strict,
                    "CHECKSUMS.txt not found",
                    warning=not self.strict,
                )
            )
            return

        # Read checksums
        with open(checksums_file) as f:
            lines = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]

        # Missing and altered are different failures with different fixes, and
        # both used to collapse into one boolean whose whole report was "Some
        # data files don't match checksums / Check data/CHECKSUMS.txt". That
        # tells the reader nothing they did not already know: not which file,
        # not whether it is absent or changed, not what the hashes were. A
        # check is only as useful as the next action it makes possible.
        import hashlib

        missing = []
        altered = []
        for line in lines:
            parts = line.split()
            if len(parts) < 2:
                continue
            expected_hash = parts[0]
            filename = " ".join(parts[1:])
            filepath = data_dir / filename

            if not filepath.exists():
                missing.append(filename)
                continue

            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            actual_hash = h.hexdigest()

            if actual_hash != expected_hash:
                altered.append((filename, expected_hash, actual_hash))

        if not missing and not altered:
            self.results.append(
                CheckResult(
                    "Data Checksums",
                    True,
                    f"All {len(lines)} data files match checksums",
                )
            )
        else:
            summary = []
            if missing:
                summary.append(f"{len(missing)} missing")
            if altered:
                summary.append(f"{len(altered)} changed")

            details = []
            for filename in missing:
                details.append(f"missing: {filename}")
            for filename, expected_hash, actual_hash in altered:
                details.append(
                    f"changed: {filename}\n"
                    f"    recorded {expected_hash[:16]}...\n"
                    f"    actual   {actual_hash[:16]}..."
                )
            details.append(
                "A changed input invalidates every result built from it. If the "
                "change is intended, rebuild and re-record data/CHECKSUMS.txt; "
                "if not, restore the file."
            )

            self.results.append(
                CheckResult(
                    "Data Checksums",
                    False,
                    f"Data files do not match CHECKSUMS.txt ({', '.join(summary)})",
                    "\n".join(details),
                )
            )

    def check_artifacts_built(self):
        """Check all artifacts have been built."""
        print("🔨 Checking Artifacts...")

        output_dir = self.repo_root / "output"
        if not output_dir.exists():
            self.results.append(
                CheckResult(
                    "Artifacts Built",
                    False,
                    "Output directory not found",
                    "Run: make all",
                )
            )
            return

        # Read Makefile to get artifact list
        makefile = self.repo_root / "Makefile"
        artifacts = []

        if makefile.exists():
            with open(makefile) as f:
                for line in f:
                    # Look for ANALYSES or ARTIFACTS (backward compatibility)
                    if line.startswith("ANALYSES") or line.startswith("ARTIFACTS"):
                        artifacts = line.split("=", 1)[1].strip().split()
                        break

        if not artifacts:
            self.results.append(
                CheckResult(
                    "Artifacts Built",
                    not self.strict,
                    "Could not determine artifact list",
                    warning=not self.strict,
                )
            )
            return

        missing = []
        for artifact in artifacts:
            fig = output_dir / "figures" / f"{artifact}.pdf"
            tbl = output_dir / "tables" / f"{artifact}.tex"
            prov = output_dir / "provenance" / f"{artifact}.yml"

            if not (fig.exists() and tbl.exists() and prov.exists()):
                missing.append(artifact)

        if not missing:
            self.results.append(
                CheckResult(
                    "Artifacts Built",
                    True,
                    f"All {len(artifacts)} artifacts complete",
                )
            )
        else:
            self.results.append(
                CheckResult(
                    "Artifacts Built",
                    False,
                    f"{len(missing)} artifacts missing: {', '.join(missing)}",
                    "Run: make all",
                )
            )

    def check_provenance(self):
        """Check provenance is complete and from current HEAD."""
        print("📋 Checking Provenance...")

        prov_dir = self.repo_root / "output" / "provenance"
        if not prov_dir.exists():
            self.results.append(
                CheckResult(
                    "Provenance Complete",
                    False,
                    "Provenance directory not found",
                )
            )
            return

        # Get current git commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=self.repo_root,
        )
        current_commit = result.stdout.strip() if result.returncode == 0 else None

        prov_files = list(prov_dir.glob("*.yml"))
        if not prov_files:
            self.results.append(
                CheckResult(
                    "Provenance Complete",
                    False,
                    "No provenance files found",
                )
            )
            return

        stale_artifacts = []
        for prov_file in prov_files:
            with open(prov_file) as f:
                data = yaml.safe_load(f)

            prov_commit = data.get("git", {}).get("commit", "")

            if current_commit and prov_commit != current_commit:
                stale_artifacts.append(prov_file.stem)

        if not stale_artifacts:
            self.results.append(
                CheckResult(
                    "Provenance Current",
                    True,
                    f"All {len(prov_files)} artifacts from current HEAD",
                )
            )
        else:
            self.results.append(
                CheckResult(
                    "Provenance Current",
                    not self.strict,
                    f"{len(stale_artifacts)} artifacts from old commits",
                    f"Stale: {', '.join(stale_artifacts)}\nRun: make clean && make all",
                    warning=not self.strict,
                )
            )

    def check_checksums(self):
        """Verify output checksums match provenance."""
        print("🔐 Checking Output Checksums...")

        prov_dir = self.repo_root / "output" / "provenance"
        if not prov_dir.exists():
            return

        import hashlib

        mismatches = []
        for prov_file in prov_dir.glob("*.yml"):
            with open(prov_file) as f:
                data = yaml.safe_load(f)

            for output in data.get("outputs", []):
                # Recorded paths are relative to the record's repo_root since
                # 2026-08-18; older records store them absolute. The helper
                # handles both, so a project with a mix of old and new records
                # keeps working.
                filepath = resolve_recorded_path(output, data)
                expected_hash = output.get("sha256")

                if not filepath.exists():
                    continue

                # Compute actual hash
                h = hashlib.sha256()
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                actual_hash = h.hexdigest()

                if actual_hash != expected_hash:
                    mismatches.append(filepath.name)

        if not mismatches:
            self.results.append(
                CheckResult(
                    "Output Checksums",
                    True,
                    "All outputs match provenance checksums",
                )
            )
        else:
            self.results.append(
                CheckResult(
                    "Output Checksums",
                    False,
                    f"{len(mismatches)} outputs modified after build",
                    f"Modified: {', '.join(mismatches)}",
                )
            )

    def check_documentation(self):
        """Check required documentation exists."""
        print("📚 Checking Documentation...")

        required_docs = [
            ("README.md", True),
            ("DATA_AVAILABILITY.md", not self.strict),
            ("CITATION.cff", not self.strict),
            ("docs/journal_editor_readme.md", not self.strict),
        ]

        missing = []
        for doc, required in required_docs:
            filepath = self.repo_root / doc
            if not filepath.exists() and required:
                missing.append(doc)

        if not missing:
            self.results.append(
                CheckResult(
                    "Documentation Complete",
                    True,
                    "All required documentation present",
                )
            )
        else:
            self.results.append(
                CheckResult(
                    "Documentation Complete",
                    False,
                    f"Missing: {', '.join(missing)}",
                )
            )

    def check_tests(self):
        """Check if tests pass."""
        print("🧪 Checking Tests...")

        tests_dir = self.repo_root / "tests"
        if not tests_dir.exists():
            self.results.append(
                CheckResult(
                    "Tests Pass",
                    not self.strict,
                    "No tests directory (optional)",
                    warning=not self.strict,
                )
            )
            return

        # Try to run pytest
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=self.test_timeout,
            )

            if result.returncode == 0:
                self.results.append(
                    CheckResult(
                        "Tests Pass",
                        True,
                        "All tests passed",
                    )
                )
            else:
                self.results.append(
                    CheckResult(
                        "Tests Pass",
                        False,
                        "Some tests failed",
                        result.stdout[:200],
                    )
                )
        except subprocess.TimeoutExpired:
            self.results.append(
                CheckResult(
                    "Tests Pass",
                    False,
                    f"Tests timed out after {self.test_timeout}s",
                    "Raise the limit with --test-timeout if the suite is "
                    "legitimately slower than this.",
                )
            )
        except Exception as e:
            self.results.append(
                CheckResult(
                    "Tests Pass",
                    not self.strict,
                    f"Could not run tests: {e}",
                    warning=not self.strict,
                )
            )

    def print_summary(self):
        """Print summary of all checks."""
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print()

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        for result in self.results:
            if not result.passed:
                status = "❌"
            elif result.warning:
                status = "⚠️ "
            else:
                status = "✅"
            print(f"{status} {result.name:30s} {result.message}")
            if result.details and not result.passed:
                print(f"   {result.details}")

        print()
        print("=" * 60)
        print(f"Results: {passed}/{total} checks passed")

        if passed == total:
            print("✅ READY FOR SUBMISSION")
            print()
            print("Next steps:")
            print("  1. make publish REQUIRE_CURRENT_HEAD=1")
            print("  2. make journal-package")
            print("  3. Review journal-package/ contents")
            print("  4. Submit to journal")
            return 0
        else:
            print("⚠️  ISSUES FOUND - Address above items before submission")
            return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: all checks must pass (no warnings allowed)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory",
    )
    parser.add_argument(
        "--test-timeout",
        type=int,
        default=PreSubmitChecker.DEFAULT_TEST_TIMEOUT,
        metavar="SECONDS",
        help=(
            "Seconds allowed for the test suite "
            f"(default: {PreSubmitChecker.DEFAULT_TEST_TIMEOUT})"
        ),
    )
    args = parser.parse_args()

    checker = PreSubmitChecker(
        args.repo_root, strict=args.strict, test_timeout=args.test_timeout
    )
    return checker.run_all_checks()


if __name__ == "__main__":
    sys.exit(main())
