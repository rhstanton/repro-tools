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


class CheckResult:
    """Result of a check."""
    def __init__(self, name, passed, message="", details=""):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details


class PreSubmitChecker:
    """Pre-submission checklist runner."""
    
    def __init__(self, repo_root, strict=False):
        self.repo_root = Path(repo_root)
        self.strict = strict
        self.results = []
    
    def run_all_checks(self):
        """Run all pre-submission checks."""
        print("="*60)
        print("PRE-SUBMISSION CHECKLIST")
        print("="*60)
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
                cwd=self.repo_root,
                timeout=5,
            )
            if result.returncode != 0:
                self.results.append(CheckResult(
                    "Git Repository",
                    False,
                    "Not a git repository",
                ))
                return
        except Exception as e:
            self.results.append(CheckResult(
                "Git Repository",
                False,
                f"Error: {e}",
            ))
            return
        
        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=self.repo_root,
        )
        
        if result.stdout.strip():
            self.results.append(CheckResult(
                "Clean Working Tree",
                not self.strict,
                "Uncommitted changes detected",
                result.stdout.strip()[:200],
            ))
        else:
            self.results.append(CheckResult(
                "Clean Working Tree",
                True,
                "No uncommitted changes",
            ))
        
        # Check if behind upstream
        result = subprocess.run(
            ["git", "rev-list", "--count", "@{u}..HEAD"],
            capture_output=True,
            text=True,
            cwd=self.repo_root,
            stderr=subprocess.DEVNULL,
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
                self.results.append(CheckResult(
                    "Up to Date with Remote",
                    not self.strict,
                    f"Behind upstream by {behind} commit(s)",
                ))
            else:
                self.results.append(CheckResult(
                    "Up to Date with Remote",
                    True,
                    f"Ahead by {ahead}, behind by 0",
                ))
        else:
            self.results.append(CheckResult(
                "Up to Date with Remote",
                True,
                "No upstream configured (OK)",
            ))
    
    def check_environment(self):
        """Check environment is set up."""
        print("🔧 Checking Environment...")
        
        python_env = self.repo_root / ".env" / "bin" / "python"
        if python_env.exists():
            self.results.append(CheckResult(
                "Python Environment",
                True,
                "Python environment exists",
            ))
        else:
            self.results.append(CheckResult(
                "Python Environment",
                False,
                "Python environment not found",
                "Run: make environment",
            ))
        
        julia_dir = self.repo_root / ".julia" / "pyjuliapkg"
        if julia_dir.exists():
            self.results.append(CheckResult(
                "Julia Environment",
                True,
                "Julia installed",
            ))
        else:
            self.results.append(CheckResult(
                "Julia Environment",
                not self.strict,
                "Julia not installed (optional)",
            ))
    
    def check_data_files(self):
        """Check data files exist and match checksums."""
        print("📊 Checking Data Files...")
        
        data_dir = self.repo_root / "data"
        checksums_file = data_dir / "CHECKSUMS.txt"
        
        if not checksums_file.exists():
            self.results.append(CheckResult(
                "Data Checksums",
                not self.strict,
                "CHECKSUMS.txt not found",
            ))
            return
        
        # Read checksums
        with open(checksums_file) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        all_match = True
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                expected_hash = parts[0]
                filename = ' '.join(parts[1:])
                filepath = data_dir / filename
                
                if not filepath.exists():
                    all_match = False
                    continue
                
                # Compute actual hash
                import hashlib
                h = hashlib.sha256()
                with open(filepath, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        h.update(chunk)
                actual_hash = h.hexdigest()
                
                if actual_hash != expected_hash:
                    all_match = False
        
        if all_match:
            self.results.append(CheckResult(
                "Data Checksums",
                True,
                f"All {len(lines)} data files match checksums",
            ))
        else:
            self.results.append(CheckResult(
                "Data Checksums",
                False,
                "Some data files don't match checksums",
                "Check data/CHECKSUMS.txt",
            ))
    
    def check_artifacts_built(self):
        """Check all artifacts have been built."""
        print("🔨 Checking Artifacts...")
        
        output_dir = self.repo_root / "output"
        if not output_dir.exists():
            self.results.append(CheckResult(
                "Artifacts Built",
                False,
                "Output directory not found",
                "Run: make all",
            ))
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
            self.results.append(CheckResult(
                "Artifacts Built",
                not self.strict,
                "Could not determine artifact list",
            ))
            return
        
        missing = []
        for artifact in artifacts:
            fig = output_dir / "figures" / f"{artifact}.pdf"
            tbl = output_dir / "tables" / f"{artifact}.tex"
            prov = output_dir / "provenance" / f"{artifact}.yml"
            
            if not (fig.exists() and tbl.exists() and prov.exists()):
                missing.append(artifact)
        
        if not missing:
            self.results.append(CheckResult(
                "Artifacts Built",
                True,
                f"All {len(artifacts)} artifacts complete",
            ))
        else:
            self.results.append(CheckResult(
                "Artifacts Built",
                False,
                f"{len(missing)} artifacts missing: {', '.join(missing)}",
                "Run: make all",
            ))
    
    def check_provenance(self):
        """Check provenance is complete and from current HEAD."""
        print("📋 Checking Provenance...")
        
        prov_dir = self.repo_root / "output" / "provenance"
        if not prov_dir.exists():
            self.results.append(CheckResult(
                "Provenance Complete",
                False,
                "Provenance directory not found",
            ))
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
            self.results.append(CheckResult(
                "Provenance Complete",
                False,
                "No provenance files found",
            ))
            return
        
        stale_artifacts = []
        for prov_file in prov_files:
            with open(prov_file) as f:
                data = yaml.safe_load(f)
            
            prov_commit = data.get("git", {}).get("commit", "")
            
            if current_commit and prov_commit != current_commit:
                stale_artifacts.append(prov_file.stem)
        
        if not stale_artifacts:
            self.results.append(CheckResult(
                "Provenance Current",
                True,
                f"All {len(prov_files)} artifacts from current HEAD",
            ))
        else:
            self.results.append(CheckResult(
                "Provenance Current",
                self.strict == False,
                f"{len(stale_artifacts)} artifacts from old commits",
                f"Stale: {', '.join(stale_artifacts)}\nRun: make clean && make all",
            ))
    
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
                filepath = Path(output["path"])
                expected_hash = output.get("sha256")
                
                if not filepath.exists():
                    continue
                
                # Compute actual hash
                h = hashlib.sha256()
                with open(filepath, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        h.update(chunk)
                actual_hash = h.hexdigest()
                
                if actual_hash != expected_hash:
                    mismatches.append(filepath.name)
        
        if not mismatches:
            self.results.append(CheckResult(
                "Output Checksums",
                True,
                "All outputs match provenance checksums",
            ))
        else:
            self.results.append(CheckResult(
                "Output Checksums",
                False,
                f"{len(mismatches)} outputs modified after build",
                f"Modified: {', '.join(mismatches)}",
            ))
    
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
            self.results.append(CheckResult(
                "Documentation Complete",
                True,
                "All required documentation present",
            ))
        else:
            self.results.append(CheckResult(
                "Documentation Complete",
                False,
                f"Missing: {', '.join(missing)}",
            ))
    
    def check_tests(self):
        """Check if tests pass."""
        print("🧪 Checking Tests...")
        
        tests_dir = self.repo_root / "tests"
        if not tests_dir.exists():
            self.results.append(CheckResult(
                "Tests Pass",
                not self.strict,
                "No tests directory (optional)",
            ))
            return
        
        # Try to run pytest
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q"],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=60,
            )
            
            if result.returncode == 0:
                self.results.append(CheckResult(
                    "Tests Pass",
                    True,
                    "All tests passed",
                ))
            else:
                self.results.append(CheckResult(
                    "Tests Pass",
                    False,
                    "Some tests failed",
                    result.stdout[:200],
                ))
        except subprocess.TimeoutExpired:
            self.results.append(CheckResult(
                "Tests Pass",
                False,
                "Tests timed out",
            ))
        except Exception as e:
            self.results.append(CheckResult(
                "Tests Pass",
                not self.strict,
                f"Could not run tests: {e}",
            ))
    
    def print_summary(self):
        """Print summary of all checks."""
        print()
        print("="*60)
        print("SUMMARY")
        print("="*60)
        print()
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        for result in self.results:
            status = "✅" if result.passed else "❌"
            print(f"{status} {result.name:30s} {result.message}")
            if result.details and not result.passed:
                print(f"   {result.details}")
        
        print()
        print("="*60)
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
    args = parser.parse_args()
    
    checker = PreSubmitChecker(args.repo_root, strict=args.strict)
    return checker.run_all_checks()


if __name__ == "__main__":
    sys.exit(main())
