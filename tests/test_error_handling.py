"""
Test error handling for repro_tools.

Tests malformed configs, missing files, corrupted YAML, etc.
"""

from __future__ import annotations

import pytest
import tempfile
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repro_tools import (
    auto_build_record,
    auto_provenance_from_config,
    publish_analyses,
    publish_files,
)
from repro_tools.core import write_build_record
from repro_tools.publish import load_yml


class TestMalformedAnalysesConfig:
    """Test handling of malformed ANALYSES config dictionaries."""

    def test_missing_inputs_key(self, tmp_path, capfd):
        """Config missing 'inputs' key should print warning."""
        # Create config.py in tmp_path
        config_path = tmp_path / "config.py"
        config_path.write_text(
            "from pathlib import Path\n"
            "REPO_ROOT = Path('.')\n"
            "ANALYSES = {\n"
            "    'test': {\n"
            "        'outputs': {'provenance': Path('out.yml'), 'figure': Path('fig.pdf'), 'table': Path('table.tex')}\n"
            "    }\n"
            "}\n"
        )

        # Add tmp_path to sys.path so config.py can be imported
        with patch("sys.path", [str(tmp_path)] + sys.path):
            # Should warn about missing key
            auto_provenance_from_config("test")

        captured = capfd.readouterr()
        assert "Warning" in captured.err or "Failed" in captured.err

    def test_missing_outputs_key(self, tmp_path, capfd):
        """Config missing 'outputs' key should print warning."""
        config_path = tmp_path / "config.py"
        config_path.write_text(
            "from pathlib import Path\n"
            "REPO_ROOT = Path('.')\n"
            "ANALYSES = {\n"
            "    'test': {\n"
            "        'inputs': [Path('data.csv')]\n"
            "    }\n"
            "}\n"
        )

        with patch("sys.path", [str(tmp_path)] + sys.path):
            auto_provenance_from_config("test")

        captured = capfd.readouterr()
        assert "Warning" in captured.err or "Failed" in captured.err

    def test_missing_provenance_in_outputs(self, tmp_path, capfd):
        """Config outputs missing 'provenance' key should print warning."""
        config_path = tmp_path / "config.py"
        config_path.write_text(
            "from pathlib import Path\n"
            "REPO_ROOT = Path('.')\n"
            "ANALYSES = {\n"
            "    'test': {\n"
            "        'inputs': [Path('data.csv')],\n"
            "        'outputs': {'figure': Path('fig.pdf')}\n"
            "    }\n"
            "}\n"
        )

        with patch("sys.path", [str(tmp_path)] + sys.path):
            auto_provenance_from_config("test")

        captured = capfd.readouterr()
        assert "Warning" in captured.err or "Failed" in captured.err

    def test_nonexistent_analysis_name(self, tmp_path, capfd):
        """Requesting non-existent analysis should print warning."""
        config_path = tmp_path / "config.py"
        config_path.write_text(
            "from pathlib import Path\n"
            "REPO_ROOT = Path('.')\n"
            "ANALYSES = {\n"
            "    'valid_analysis': {\n"
            "        'inputs': [Path('data.csv')],\n"
            "        'outputs': {'provenance': Path('out.yml'), 'figure': Path('fig.pdf'), 'table': Path('table.tex')}\n"
            "    }\n"
            "}\n"
        )

        with patch("sys.path", [str(tmp_path)] + sys.path):
            auto_provenance_from_config("nonexistent")

        captured = capfd.readouterr()
        assert "Unknown analysis" in captured.err
        assert "nonexistent" in captured.err


class TestMissingFiles:
    """Test handling of missing input/output files."""

    def test_missing_input_file_raises_error(self, tmp_path):
        """Missing input file should raise FileNotFoundError."""
        out_meta = tmp_path / "out.yml"
        missing_input = tmp_path / "missing.csv"
        existing_output = tmp_path / "output.txt"
        existing_output.write_text("test")

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            auto_build_record(
                out_meta=out_meta,
                inputs=[missing_input],
                outputs=[existing_output],
            )

    def test_missing_output_file_raises_error(self, tmp_path):
        """Missing output file should raise FileNotFoundError."""
        out_meta = tmp_path / "out.yml"
        missing_output = tmp_path / "missing_output.pdf"

        # Should raise FileNotFoundError when trying to hash missing output
        with pytest.raises(FileNotFoundError):
            auto_build_record(
                out_meta=out_meta,
                inputs=[],
                outputs=[missing_output],
            )

    def test_missing_provenance_file_when_publishing(self, tmp_path):
        """Publishing should raise SystemExit if provenance file missing."""
        # Set up directories
        project_root = tmp_path / "project"
        paper_root = tmp_path / "paper"
        output_dir = project_root / "output"
        (output_dir / "provenance").mkdir(parents=True)

        # Create output file but NO provenance file
        fig = output_dir / "figures" / "test.pdf"
        fig.parent.mkdir(parents=True)
        fig.write_text("fake figure")

        # Should raise SystemExit with clear message
        mock_gitinfo = {"is_git_repo": False, "commit": "", "branch": ""}
        with patch("repro_tools.publish.check_git_policy", return_value=mock_gitinfo):
            with pytest.raises(SystemExit, match="Missing build record"):
                publish_analyses(
                    paper_root=paper_root,
                    project_root=project_root,
                    analysis_names=["test"],
                    kinds=["figures"],
                    allow_dirty=True,
                )


class TestCorruptedYAML:
    """Test handling of corrupted/malformed YAML files."""

    def test_corrupted_provenance_yaml(self, tmp_path):
        """Corrupted provenance YAML should raise error."""
        yaml_file = tmp_path / "corrupted.yml"
        yaml_file.write_text("{ malformed: yaml: content:: [")

        with pytest.raises(Exception):  # PyYAML will raise various exceptions
            load_yml(yaml_file)

    def test_empty_provenance_yaml(self, tmp_path):
        """Empty provenance file should be handled."""
        yaml_file = tmp_path / "empty.yml"
        yaml_file.write_text("")

        result = load_yml(yaml_file)
        assert result is None or result == {}


class TestPublishingEdgeCases:
    """Test edge cases in publishing workflows."""

    def test_publish_files_nonexistent_file(self, tmp_path):
        """Publishing non-existent file should raise SystemExit."""
        project_root = tmp_path / "project"
        paper_root = tmp_path / "paper"
        output_dir = project_root / "output"
        output_dir.mkdir(parents=True)

        # Try to publish file that doesn't exist
        nonexistent = output_dir / "figures" / "nonexistent.pdf"

        mock_gitinfo = {"is_git_repo": False, "commit": "", "branch": ""}
        with patch("repro_tools.publish.check_git_policy", return_value=mock_gitinfo):
            with pytest.raises(SystemExit, match="Source file not found"):
                publish_files(
                    paper_root=paper_root,
                    project_root=project_root,
                    file_paths=[nonexistent],
                    allow_dirty=True,
                )

    def test_publish_with_invalid_kind(self, tmp_path, capfd):
        """Publishing with invalid 'kind' should skip gracefully with warning."""
        project_root = tmp_path / "project"
        paper_root = tmp_path / "paper"
        output_dir = project_root / "output"

        # Create provenance
        prov_file = output_dir / "provenance" / "test.yml"
        prov_file.parent.mkdir(parents=True)
        prov_file.write_text(
            "artifact: test\n" "built_at_utc: '2026-01-18T12:00:00+00:00'\n" "outputs: []\n"
        )

        # Try to publish kind that doesn't exist in output structure
        mock_gitinfo = {"is_git_repo": False, "commit": "", "branch": ""}
        with patch("repro_tools.publish.check_git_policy", return_value=mock_gitinfo):
            result = publish_analyses(
                paper_root=paper_root,
                project_root=project_root,
                analysis_names=["test"],
                kinds=["nonexistent_kind"],  # Invalid kind
                allow_dirty=True,
            )

        # Should warn about missing file
        captured = capfd.readouterr()
        assert "not found" in captured.out or "Warning" in captured.out

    def test_publish_to_nonexistent_paper_root(self, tmp_path):
        """Publishing to non-existent paper root should create it."""
        project_root = tmp_path / "project"
        paper_root = tmp_path / "paper"  # Doesn't exist yet
        output_dir = project_root / "output"

        # Create simple provenance and output
        prov_file = output_dir / "provenance" / "test.yml"
        prov_file.parent.mkdir(parents=True)

        fig = output_dir / "figures" / "test.pdf"
        fig.parent.mkdir(parents=True)
        fig.write_text("fake figure")

        # Record provenance
        write_build_record(
            out_meta=prov_file,
            artifact_name="test",
            repo_root=project_root,
            inputs=[],
            outputs=[fig],
            command=["test"],
        )

        # Publish should create paper_root
        mock_gitinfo = {"is_git_repo": False, "commit": "", "branch": ""}
        with patch("repro_tools.publish.check_git_policy", return_value=mock_gitinfo):
            publish_analyses(
                paper_root=paper_root,
                project_root=project_root,
                analysis_names=["test"],
                kinds=["figures"],
                allow_dirty=True,
            )

        # Check paper directory structure was created
        assert (paper_root / "figures" / "test.pdf").exists()
        assert (paper_root / "provenance.yml").exists()


class TestCommandRecording:
    """Test edge cases in command recording."""

    def test_command_recorded_from_write_build_record(self, tmp_path):
        """Commands with special characters should be recorded correctly."""
        out_meta = tmp_path / "out.yml"
        output = tmp_path / "output.txt"
        output.write_text("test")

        write_build_record(
            out_meta=out_meta,
            artifact_name="test",
            repo_root=tmp_path,
            inputs=[],
            outputs=[output],
            command=["python", "script.py", "--arg", "value with spaces", "--flag"],
        )

        prov = load_yml(out_meta)
        assert prov["command"] == ["python", "script.py", "--arg", "value with spaces", "--flag"]

    def test_auto_build_record_uses_sys_argv(self, tmp_path):
        """auto_build_record should use sys.argv for command."""
        out_meta = tmp_path / "out.yml"
        output = tmp_path / "output.txt"
        output.write_text("test")

        # Mock sys.argv
        with patch("sys.argv", ["test_script.py", "--test-arg"]):
            auto_build_record(
                out_meta=out_meta,
                inputs=[],
                outputs=[output],
            )

        prov = load_yml(out_meta)
        assert "test_script.py" in prov["command"]
        assert "--test-arg" in prov["command"]
