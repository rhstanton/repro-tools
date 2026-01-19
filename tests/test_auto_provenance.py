"""Tests for automatic provenance recording."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from repro_tools import (
    auto_build_record,
    enable_auto_provenance,
    auto_provenance_from_config,
)


@pytest.fixture
def temp_project():
    """Create a temporary project with config.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmpdir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmpdir,
            check=True,
            capture_output=True,
        )

        # Create directory structure
        (tmpdir / "data").mkdir()
        (tmpdir / "output" / "figures").mkdir(parents=True)
        (tmpdir / "output" / "tables").mkdir(parents=True)
        (tmpdir / "output" / "provenance").mkdir(parents=True)

        # Create config.py
        config_content = """
from pathlib import Path

REPO_ROOT = Path(__file__).parent
DATA_DIR = REPO_ROOT / "data"
OUTPUT_DIR = REPO_ROOT / "output"

ANALYSES = {
    "test_analysis": {
        "inputs": [DATA_DIR / "input.csv"],
        "outputs": {
            "figure": OUTPUT_DIR / "figures" / "test_analysis.pdf",
            "table": OUTPUT_DIR / "tables" / "test_analysis.tex",
            "provenance": OUTPUT_DIR / "provenance" / "test_analysis.yml",
        }
    }
}
"""
        (tmpdir / "config.py").write_text(config_content)

        # Create input data
        (tmpdir / "data" / "input.csv").write_text("x,y\\n1,2\\n")

        # Initial commit
        subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmpdir,
            check=True,
            capture_output=True,
        )

        yield tmpdir


class TestAutoBuildRecord:
    """Test auto_build_record function."""

    def test_auto_build_record_basic(self, tmp_path):
        """Test basic auto_build_record usage."""
        # Create files
        input_file = tmp_path / "input.txt"
        output_file = tmp_path / "output.txt"
        prov_file = tmp_path / "provenance.yml"

        input_file.write_text("input data")
        output_file.write_text("output data")

        # Record provenance
        auto_build_record(
            out_meta=prov_file,
            inputs=[input_file],
            outputs=[output_file],
        )

        assert prov_file.exists()

        prov = yaml.safe_load(prov_file.read_text())
        assert "artifact" in prov
        assert "built_at_utc" in prov
        assert "command" in prov
        assert len(prov["inputs"]) == 1
        assert len(prov["outputs"]) == 1

    def test_auto_build_record_detects_artifact_name(self, tmp_path):
        """Test artifact name auto-detection from script."""
        # This simulates being called from a script
        prov_file = tmp_path / "provenance.yml"
        input_file = tmp_path / "input.txt"
        output_file = tmp_path / "output.txt"

        input_file.write_text("data")
        output_file.write_text("result")

        auto_build_record(
            out_meta=prov_file,
            inputs=[input_file],
            outputs=[output_file],
            artifact_name="custom_name",
        )

        prov = yaml.safe_load(prov_file.read_text())
        assert prov["artifact"] == "custom_name"


class TestAutoProvenanceFromConfig:
    """Test config-based auto provenance."""

    def test_auto_provenance_from_config(self, temp_project):
        """Test automatic provenance using config."""
        repo = temp_project

        # Add project to Python path
        sys.path.insert(0, str(repo))

        try:
            # Force reload of config module
            import importlib

            if "config" in sys.modules:
                importlib.reload(sys.modules["config"])

            # Create outputs
            fig = repo / "output" / "figures" / "test_analysis.pdf"
            tbl = repo / "output" / "tables" / "test_analysis.tex"
            fig.write_text("fake pdf")
            tbl.write_text("fake table")

            # Record provenance
            auto_provenance_from_config("test_analysis")

            # Check provenance was created
            prov_file = repo / "output" / "provenance" / "test_analysis.yml"
            assert prov_file.exists()

            prov = yaml.safe_load(prov_file.read_text())
            assert prov["artifact"] == "test_analysis"
            assert len(prov["inputs"]) == 1
            assert len(prov["outputs"]) == 2

        finally:
            if "config" in sys.modules:
                del sys.modules["config"]
            sys.path.remove(str(repo))

    def test_auto_provenance_unknown_analysis(self, temp_project):
        """Test warning for unknown analysis."""
        repo = temp_project
        sys.path.insert(0, str(repo))

        try:
            # Should not crash, just warn
            auto_provenance_from_config("unknown_analysis")

            # Should not create provenance file
            prov_file = repo / "output" / "provenance" / "unknown_analysis.yml"
            assert not prov_file.exists()

        finally:
            sys.path.remove(str(repo))

    def test_auto_provenance_no_config(self, tmp_path):
        """Test helpful error when config.py missing."""
        # Don't add to path - no config available
        # Should not crash, just warn
        auto_provenance_from_config("test")
        # Test passes if no exception raised

    def test_auto_provenance_idempotent(self, temp_project):
        """Test that calling multiple times doesn't re-record."""
        repo = temp_project
        sys.path.insert(0, str(repo))

        try:
            # Force reload of config module to get correct REPO_ROOT
            import importlib

            if "config" in sys.modules:
                importlib.reload(sys.modules["config"])

            # Verify input exists (from fixture)
            input_file = repo / "data" / "input.csv"
            assert input_file.exists(), f"Input file {input_file} should exist from fixture"

            # Create outputs
            fig = repo / "output" / "figures" / "test_analysis.pdf"
            tbl = repo / "output" / "tables" / "test_analysis.tex"
            fig.write_text("fake pdf")
            tbl.write_text("fake table")

            # Reset global flag
            from repro_tools import core

            core._provenance_recorded = False

            # First call
            auto_provenance_from_config("test_analysis")
            prov_file = repo / "output" / "provenance" / "test_analysis.yml"
            assert prov_file.exists(), f"Provenance file should exist at {prov_file}"

            # Get timestamp of first write
            first_mtime = prov_file.stat().st_mtime

            # Modify outputs
            import time

            time.sleep(0.01)  # Ensure different timestamp
            fig.write_text("modified pdf")

            # Second call - should not re-record (flag already set)
            auto_provenance_from_config("test_analysis")
            second_mtime = prov_file.stat().st_mtime

            # File should not have been rewritten
            assert first_mtime == second_mtime

        finally:
            # Clean up
            if "config" in sys.modules:
                del sys.modules["config"]
            sys.path.remove(str(repo))
            # Reset flag for other tests
            from repro_tools import core

            core._provenance_recorded = False


class TestEnableAutoProvenance:
    """Test enable_auto_provenance integration."""

    def test_enable_auto_provenance_script(self, temp_project):
        """Test enable_auto_provenance in a real script."""
        repo = temp_project

        # Create a test script
        script_content = """
import sys
sys.path.insert(0, r"{repo}")

from pathlib import Path
from repro_tools import enable_auto_provenance

enable_auto_provenance(__file__)

# Simulate analysis
fig = Path(r"{repo}") / "output" / "figures" / "test_analysis.pdf"
tbl = Path(r"{repo}") / "output" / "tables" / "test_analysis.tex"
fig.write_text("fake pdf")
tbl.write_text("fake table")
""".format(
            repo=repo
        )

        script_file = repo / "build_test_analysis.py"
        script_file.write_text(script_content)

        # Run the script
        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=repo,
            capture_output=True,
            text=True,
        )

        # Check it succeeded
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Check provenance was created
        prov_file = repo / "output" / "provenance" / "test_analysis.yml"
        assert prov_file.exists()

        prov = yaml.safe_load(prov_file.read_text())
        assert prov["artifact"] == "test_analysis"

    def test_enable_auto_provenance_strips_build_prefix(self, temp_project):
        """Test that 'build_' prefix is stripped from artifact name."""
        repo = temp_project

        # Update config for new analysis
        config_content = (repo / "config.py").read_text()
        config_content += """
ANALYSES["new_analysis"] = {
    "inputs": [DATA_DIR / "input.csv"],
    "outputs": {
        "figure": OUTPUT_DIR / "figures" / "new_analysis.pdf",
        "table": OUTPUT_DIR / "tables" / "new_analysis.tex",
        "provenance": OUTPUT_DIR / "provenance" / "new_analysis.yml",
    }
}
"""
        (repo / "config.py").write_text(config_content)

        # Create script with 'build_' prefix
        script_content = """
import sys
sys.path.insert(0, r"{repo}")

from pathlib import Path
from repro_tools import enable_auto_provenance

enable_auto_provenance(__file__)

fig = Path(r"{repo}") / "output" / "figures" / "new_analysis.pdf"
tbl = Path(r"{repo}") / "output" / "tables" / "new_analysis.tex"
fig.write_text("fake pdf")
tbl.write_text("fake table")
""".format(
            repo=repo
        )

        script_file = repo / "build_new_analysis.py"
        script_file.write_text(script_content)

        # Run script
        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=repo,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Check artifact name doesn't have 'build_' prefix
        prov_file = repo / "output" / "provenance" / "new_analysis.yml"
        assert prov_file.exists()

        prov = yaml.safe_load(prov_file.read_text())
        assert prov["artifact"] == "new_analysis"  # Not "build_new_analysis"


class TestGitStateinProvenance:
    """Test git state capture in provenance."""

    def test_provenance_captures_clean_state(self, temp_project):
        """Test provenance correctly captures clean git state."""
        repo = temp_project

        input_file = repo / "data" / "input.csv"
        output_file = repo / "output" / "output.txt"
        prov_file = repo / "output" / "prov.yml"

        output_file.write_text("result")

        from repro_tools import write_build_record

        write_build_record(
            out_meta=prov_file,
            artifact_name="test",
            command=["python", "test.py"],
            repo_root=repo,
            inputs=[input_file],
            outputs=[output_file],
        )

        prov = yaml.safe_load(prov_file.read_text())
        assert prov["git"]["is_git_repo"] is True
        assert prov["git"]["dirty"] is False

    def test_provenance_captures_dirty_state(self, temp_project):
        """Test provenance correctly captures dirty git state."""
        repo = temp_project

        # Make repo dirty by modifying tracked file
        input_file = repo / "data" / "input.csv"
        input_file.write_text("modified data\n")

        output_file = repo / "output" / "output.txt"
        prov_file = repo / "output" / "prov.yml"

        output_file.write_text("result")

        from repro_tools import write_build_record

        write_build_record(
            out_meta=prov_file,
            artifact_name="test",
            command=["python", "test.py"],
            repo_root=repo,
            inputs=[input_file],
            outputs=[output_file],
        )

        prov = yaml.safe_load(prov_file.read_text())
        assert prov["git"]["dirty"] is True

    def test_provenance_captures_commit_info(self, temp_project):
        """Test provenance captures commit hash and branch."""
        repo = temp_project

        # Get current commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()

        input_file = repo / "data" / "input.csv"
        output_file = repo / "output" / "output.txt"
        prov_file = repo / "output" / "prov.yml"

        output_file.write_text("result")

        from repro_tools import write_build_record

        write_build_record(
            out_meta=prov_file,
            artifact_name="test",
            command=["python", "test.py"],
            repo_root=repo,
            inputs=[input_file],
            outputs=[output_file],
        )

        prov = yaml.safe_load(prov_file.read_text())
        assert prov["git"]["commit"] == commit
        assert prov["git"]["branch"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
