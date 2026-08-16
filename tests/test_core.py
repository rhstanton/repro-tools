"""Tests for core provenance functionality."""

import tempfile
from pathlib import Path

import pytest

from repro_tools import git_state, sha256_file, write_build_record


def test_sha256_file():
    """Test file checksumming."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content\n")
        path = Path(f.name)

    try:
        checksum = sha256_file(path)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 is 64 hex chars

        # Same content = same checksum
        checksum2 = sha256_file(path)
        assert checksum == checksum2
    finally:
        path.unlink()


def test_git_state_no_repo():
    """Test git_state in non-repo directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        state = git_state(Path(tmpdir))
        assert state["is_git_repo"] is False


def test_write_build_record():
    """Test writing build provenance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create input file
        input_file = tmpdir / "input.txt"
        input_file.write_text("input data\n")

        # Create output file
        output_file = tmpdir / "output.txt"
        output_file.write_text("output data\n")

        # Create provenance file
        prov_file = tmpdir / "provenance.yml"

        write_build_record(
            out_meta=prov_file,
            artifact_name="test_artifact",
            command=["python", "test.py"],
            repo_root=tmpdir,
            inputs=[input_file],
            outputs=[output_file],
        )

        assert prov_file.exists()

        # Check provenance contains expected fields
        import yaml

        with prov_file.open() as f:
            prov = yaml.safe_load(f)

        assert prov["artifact"] == "test_artifact"
        assert prov["command"] == ["python", "test.py"]
        assert "built_at_utc" in prov
        assert "git" in prov
        assert len(prov["inputs"]) == 1
        assert len(prov["outputs"]) == 1
        assert "sha256" in prov["inputs"][0]
        assert "sha256" in prov["outputs"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
