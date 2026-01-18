"""Tests for publishing functionality."""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

from repro_tools import (
    publish_analyses,
    publish_files,
    write_build_record,
    copy_if_changed,
)


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
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
        
        # Create initial commit
        (tmpdir / "README.md").write_text("# Test Repo\n")
        subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmpdir,
            check=True,
            capture_output=True,
        )
        
        yield tmpdir


@pytest.fixture
def analysis_artifacts(temp_git_repo):
    """Create sample analysis artifacts."""
    repo = temp_git_repo
    
    # Create directory structure
    output_dir = repo / "output"
    (output_dir / "figures").mkdir(parents=True)
    (output_dir / "tables").mkdir(parents=True)
    (output_dir / "provenance").mkdir(parents=True)
    
    # Create input file
    data_dir = repo / "data"
    data_dir.mkdir()
    input_file = data_dir / "input.csv"
    input_file.write_text("x,y\n1,2\n3,4\n")
    
    # Create output files
    fig_file = output_dir / "figures" / "test_analysis.pdf"
    fig_file.write_text("fake pdf content")
    
    tbl_file = output_dir / "tables" / "test_analysis.tex"
    tbl_file.write_text("\\begin{table}...\\end{table}")
    
    # Create provenance
    prov_file = output_dir / "provenance" / "test_analysis.yml"
    write_build_record(
        out_meta=prov_file,
        artifact_name="test_analysis",
        command=["python", "build_test.py"],
        repo_root=repo,
        inputs=[input_file],
        outputs=[fig_file, tbl_file],
    )
    
    # Commit everything
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add test analysis"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    
    return {
        "repo": repo,
        "input": input_file,
        "figure": fig_file,
        "table": tbl_file,
        "provenance": prov_file,
    }


class TestCopyIfChanged:
    """Test copy_if_changed utility."""
    
    def test_copy_new_file(self, tmp_path):
        """Test copying when destination doesn't exist."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "subdir" / "dest.txt"
        src.write_text("content")
        
        copied = copy_if_changed(src, dst)
        
        assert copied is True
        assert dst.exists()
        assert dst.read_text() == "content"
    
    def test_skip_identical_file(self, tmp_path):
        """Test skipping when files are identical."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("content")
        dst.write_text("content")
        
        copied = copy_if_changed(src, dst)
        
        assert copied is False
    
    def test_copy_changed_file(self, tmp_path):
        """Test copying when files differ."""
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("new content")
        dst.write_text("old content")
        
        copied = copy_if_changed(src, dst)
        
        assert copied is True
        assert dst.read_text() == "new content"


class TestPublishAnalyses:
    """Test publishing complete analyses."""
    
    def test_publish_clean_repo(self, analysis_artifacts):
        """Test publishing from clean repository."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        result = publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["test_analysis"],
            allow_dirty=False,
            verbose=False,
        )
        
        # Check files were published
        assert (paper_dir / "figures" / "test_analysis.pdf").exists()
        assert (paper_dir / "tables" / "test_analysis.tex").exists()
        assert (paper_dir / "provenance.yml").exists()
        
        # Check provenance structure
        prov = yaml.safe_load((paper_dir / "provenance.yml").read_text())
        assert prov["paper_provenance_version"] == 1
        assert "test_analysis" in prov["artifacts"]
        assert "figures" in prov["artifacts"]["test_analysis"]
        assert "tables" in prov["artifacts"]["test_analysis"]
    
    def test_publish_dirty_repo_rejected(self, analysis_artifacts):
        """Test that dirty repo is rejected by default."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        # Make repo dirty by modifying tracked file
        (repo / "README.md").write_text("# Modified\n")
        
        with pytest.raises(SystemExit, match="dirty working tree"):
            publish_analyses(
                project_root=repo,
                paper_root=paper_dir,
                analysis_names=["test_analysis"],
                allow_dirty=False,
                verbose=False,
            )
    
    def test_publish_dirty_repo_allowed(self, analysis_artifacts):
        """Test that dirty repo can be allowed."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        # Make repo dirty
        (repo / "dirty.txt").write_text("uncommitted change")
        
        # Should succeed with allow_dirty=True
        result = publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["test_analysis"],
            allow_dirty=True,
            verbose=False,
        )
        
        assert (paper_dir / "figures" / "test_analysis.pdf").exists()
    
    def test_publish_artifacts_built_dirty_rejected(self, analysis_artifacts):
        """Test that artifacts built from dirty tree are rejected."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        # Make repo dirty by modifying tracked file
        (repo / "README.md").write_text("# Modified\n")
        
        # Rebuild artifact in dirty state
        fig_file = analysis_artifacts["figure"]
        tbl_file = analysis_artifacts["table"]
        prov_file = analysis_artifacts["provenance"]
        
        fig_file.write_text("updated fake pdf")
        tbl_file.write_text("updated table")
        
        write_build_record(
            out_meta=prov_file,
            artifact_name="test_analysis",
            command=["python", "build_test.py"],
            repo_root=repo,
            inputs=[analysis_artifacts["input"]],
            outputs=[fig_file, tbl_file],
        )
        
        # Clean repo now (but artifacts were built dirty)
        (repo / "README.md").write_text("# Test Repo\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        
        # Try to publish - should fail because artifacts were BUILT dirty
        with pytest.raises(SystemExit, match="artifacts were built from a dirty working tree"):
            publish_analyses(
                project_root=repo,
                paper_root=paper_dir,
                analysis_names=["test_analysis"],
                allow_dirty=False,
                verbose=False,
            )
    
    def test_publish_artifacts_built_dirty_allowed(self, analysis_artifacts):
        """Test that artifacts built dirty can be allowed."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        # Make repo dirty and rebuild
        (repo / "dirty.txt").write_text("uncommitted change")
        
        fig_file = analysis_artifacts["figure"]
        tbl_file = analysis_artifacts["table"]
        prov_file = analysis_artifacts["provenance"]
        
        fig_file.write_text("updated fake pdf")
        
        write_build_record(
            out_meta=prov_file,
            artifact_name="test_analysis",
            command=["python", "build_test.py"],
            repo_root=repo,
            inputs=[analysis_artifacts["input"]],
            outputs=[fig_file, tbl_file],
        )
        
        # Clean repo now (but artifacts were built dirty)
        (repo / "dirty.txt").unlink()
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        
        # Should fail unless allow_dirty=True for artifacts
        with pytest.raises(SystemExit, match="artifacts were built from a dirty working tree"):
            publish_analyses(
                project_root=repo,
                paper_root=paper_dir,
                analysis_names=["test_analysis"],
                allow_dirty=False,
                verbose=False,
            )
        
        # Should succeed with allow_dirty=True
        result = publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["test_analysis"],
            allow_dirty=True,  # Allows artifacts built dirty
            verbose=False,
        )
        
        assert (paper_dir / "figures" / "test_analysis.pdf").exists()
    
    def test_publish_missing_provenance(self, analysis_artifacts):
        """Test error when provenance file missing."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        # Delete provenance and commit so repo is clean
        analysis_artifacts["provenance"].unlink()
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Delete provenance"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        
        with pytest.raises(SystemExit, match="Missing build record"):
            publish_analyses(
                project_root=repo,
                paper_root=paper_dir,
                analysis_names=["test_analysis"],
                verbose=False,
            )
    
    def test_publish_multiple_analyses(self, temp_git_repo):
        """Test publishing multiple analyses."""
        repo = temp_git_repo
        
        # Create two analyses
        output_dir = repo / "output"
        for name in ["analysis1", "analysis2"]:
            (output_dir / "figures").mkdir(parents=True, exist_ok=True)
            (output_dir / "tables").mkdir(parents=True, exist_ok=True)
            (output_dir / "provenance").mkdir(parents=True, exist_ok=True)
            
            fig = output_dir / "figures" / f"{name}.pdf"
            tbl = output_dir / "tables" / f"{name}.tex"
            prov = output_dir / "provenance" / f"{name}.yml"
            
            fig.write_text(f"pdf for {name}")
            tbl.write_text(f"table for {name}")
            
            write_build_record(
                out_meta=prov,
                artifact_name=name,
                command=["python", f"build_{name}.py"],
                repo_root=repo,
                inputs=[],
                outputs=[fig, tbl],
            )
        
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add analyses"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        
        # Publish both
        paper_dir = repo / "paper"
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["analysis1", "analysis2"],
            verbose=False,
        )
        
        # Check both published
        assert (paper_dir / "figures" / "analysis1.pdf").exists()
        assert (paper_dir / "figures" / "analysis2.pdf").exists()
        
        prov = yaml.safe_load((paper_dir / "provenance.yml").read_text())
        assert "analysis1" in prov["artifacts"]
        assert "analysis2" in prov["artifacts"]
    
    def test_publish_idempotent(self, analysis_artifacts):
        """Test that publishing twice doesn't change anything."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        # First publish
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["test_analysis"],
            verbose=False,
        )
        
        first_mtime = (paper_dir / "figures" / "test_analysis.pdf").stat().st_mtime
        
        # Second publish
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["test_analysis"],
            verbose=False,
        )
        
        second_mtime = (paper_dir / "figures" / "test_analysis.pdf").stat().st_mtime
        
        # File shouldn't be recopied (mtime unchanged)
        assert first_mtime == second_mtime


class TestPublishFiles:
    """Test publishing specific files."""
    
    def test_publish_specific_files(self, analysis_artifacts):
        """Test publishing individual files."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        publish_files(
            project_root=repo,
            paper_root=paper_dir,
            file_paths=[analysis_artifacts["figure"]],
            verbose=False,
        )
        
        assert (paper_dir / "figures" / "test_analysis.pdf").exists()
        assert not (paper_dir / "tables" / "test_analysis.tex").exists()
        
        prov = yaml.safe_load((paper_dir / "provenance.yml").read_text())
        assert "files" in prov
        assert "figures/test_analysis.pdf" in prov["files"]
    
    def test_publish_file_outside_output_dir(self, analysis_artifacts):
        """Test error when publishing file outside output/."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        random_file = repo / "data" / "input.csv"
        
        with pytest.raises(SystemExit, match="not in output"):
            publish_files(
                project_root=repo,
                paper_root=paper_dir,
                file_paths=[random_file],
                verbose=False,
            )
    
    def test_publish_missing_file(self, analysis_artifacts):
        """Test error when file doesn't exist."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        missing_file = repo / "output" / "figures" / "missing.pdf"
        
        with pytest.raises(SystemExit, match="not found"):
            publish_files(
                project_root=repo,
                paper_root=paper_dir,
                file_paths=[missing_file],
                verbose=False,
            )


class TestGitSafetyChecks:
    """Test git safety enforcement."""
    
    def test_require_current_head(self, analysis_artifacts):
        """Test require_current_head enforcement."""
        repo = analysis_artifacts["repo"]
        paper_dir = repo / "paper"
        
        # Get current commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        current_commit = result.stdout.strip()
        
        # Make a new commit (so artifacts are from old HEAD)
        (repo / "new_file.txt").write_text("new content")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "New commit"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        
        # Publishing with require_current_head should fail
        with pytest.raises(SystemExit, match="not built from current HEAD"):
            publish_analyses(
                project_root=repo,
                paper_root=paper_dir,
                analysis_names=["test_analysis"],
                require_current_head=True,
                verbose=False,
            )
        
        # Should work without require_current_head
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["test_analysis"],
            require_current_head=False,
            verbose=False,
        )
        
        assert (paper_dir / "figures" / "test_analysis.pdf").exists()


class TestIncrementalPublishing:
    """Test incremental and selective publishing scenarios."""
    
    def test_publish_subset_of_analyses(self, temp_git_repo):
        """Test publishing only selected analyses, not all."""
        repo = temp_git_repo
        
        # Create three analyses
        output_dir = repo / "output"
        for name in ["analysis1", "analysis2", "analysis3"]:
            (output_dir / "figures").mkdir(parents=True, exist_ok=True)
            (output_dir / "tables").mkdir(parents=True, exist_ok=True)
            (output_dir / "provenance").mkdir(parents=True, exist_ok=True)
            
            fig = output_dir / "figures" / f"{name}.pdf"
            tbl = output_dir / "tables" / f"{name}.tex"
            prov = output_dir / "provenance" / f"{name}.yml"
            
            fig.write_text(f"pdf for {name}")
            tbl.write_text(f"table for {name}")
            
            write_build_record(
                out_meta=prov,
                artifact_name=name,
                command=["python", f"build_{name}.py"],
                repo_root=repo,
                inputs=[],
                outputs=[fig, tbl],
            )
        
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add all analyses"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        
        # Publish only analysis1 and analysis3 (skip analysis2)
        paper_dir = repo / "paper"
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["analysis1", "analysis3"],
            verbose=False,
        )
        
        # Check only selected analyses published
        assert (paper_dir / "figures" / "analysis1.pdf").exists()
        assert not (paper_dir / "figures" / "analysis2.pdf").exists()
        assert (paper_dir / "figures" / "analysis3.pdf").exists()
        
        prov = yaml.safe_load((paper_dir / "provenance.yml").read_text())
        assert "analysis1" in prov["artifacts"]
        assert "analysis2" not in prov["artifacts"]
        assert "analysis3" in prov["artifacts"]
    
    def test_incremental_publishing(self, temp_git_repo):
        """Test publishing analyses one at a time incrementally."""
        repo = temp_git_repo
        output_dir = repo / "output"
        paper_dir = repo / "paper"
        
        # Create and publish first analysis
        for name in ["analysis1"]:
            (output_dir / "figures").mkdir(parents=True, exist_ok=True)
            (output_dir / "tables").mkdir(parents=True, exist_ok=True)
            (output_dir / "provenance").mkdir(parents=True, exist_ok=True)
            
            fig = output_dir / "figures" / f"{name}.pdf"
            tbl = output_dir / "tables" / f"{name}.tex"
            prov = output_dir / "provenance" / f"{name}.yml"
            
            fig.write_text(f"pdf for {name}")
            tbl.write_text(f"table for {name}")
            
            write_build_record(
                out_meta=prov,
                artifact_name=name,
                command=["python", f"build_{name}.py"],
                repo_root=repo,
                inputs=[],
                outputs=[fig, tbl],
            )
        
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add analysis1"], cwd=repo, check=True, capture_output=True)
        
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["analysis1"],
            verbose=False,
        )
        
        assert (paper_dir / "figures" / "analysis1.pdf").exists()
        
        # Now create and publish second analysis
        for name in ["analysis2"]:
            fig = output_dir / "figures" / f"{name}.pdf"
            tbl = output_dir / "tables" / f"{name}.tex"
            prov = output_dir / "provenance" / f"{name}.yml"
            
            fig.write_text(f"pdf for {name}")
            tbl.write_text(f"table for {name}")
            
            write_build_record(
                out_meta=prov,
                artifact_name=name,
                command=["python", f"build_{name}.py"],
                repo_root=repo,
                inputs=[],
                outputs=[fig, tbl],
            )
        
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add analysis2"], cwd=repo, check=True, capture_output=True)
        
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["analysis1", "analysis2"],  # Publish both
            verbose=False,
        )
        
        # Both should exist
        assert (paper_dir / "figures" / "analysis1.pdf").exists()
        assert (paper_dir / "figures" / "analysis2.pdf").exists()
        
        # Provenance should have both
        prov = yaml.safe_load((paper_dir / "provenance.yml").read_text())
        assert "analysis1" in prov["artifacts"]
        assert "analysis2" in prov["artifacts"]
    
    def test_publish_to_directory_with_existing_files(self, temp_git_repo):
        """Test publishing when paper directory already has files."""
        repo = temp_git_repo
        output_dir = repo / "output"
        paper_dir = repo / "paper"
        
        # Create paper directory with existing files (not from analyses)
        (paper_dir / "figures").mkdir(parents=True)
        (paper_dir / "tables").mkdir(parents=True)
        
        # Manually created files
        manual_fig = paper_dir / "figures" / "manual_figure.pdf"
        manual_tbl = paper_dir / "tables" / "manual_table.tex"
        manual_fig.write_text("manually created figure")
        manual_tbl.write_text("manually created table")
        
        # Now create an analysis
        (output_dir / "figures").mkdir(parents=True)
        (output_dir / "tables").mkdir(parents=True)
        (output_dir / "provenance").mkdir(parents=True)
        
        fig = output_dir / "figures" / "analysis1.pdf"
        tbl = output_dir / "tables" / "analysis1.tex"
        prov = output_dir / "provenance" / "analysis1.yml"
        
        fig.write_text("analysis figure")
        tbl.write_text("analysis table")
        
        write_build_record(
            out_meta=prov,
            artifact_name="analysis1",
            command=["python", "build_analysis1.py"],
            repo_root=repo,
            inputs=[],
            outputs=[fig, tbl],
        )
        
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add analysis"], cwd=repo, check=True, capture_output=True)
        
        # Publish analysis
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["analysis1"],
            verbose=False,
        )
        
        # Manual files should still exist
        assert manual_fig.exists()
        assert manual_tbl.exists()
        assert manual_fig.read_text() == "manually created figure"
        assert manual_tbl.read_text() == "manually created table"
        
        # Analysis files should exist
        assert (paper_dir / "figures" / "analysis1.pdf").exists()
        assert (paper_dir / "tables" / "analysis1.tex").exists()
        assert (paper_dir / "figures" / "analysis1.pdf").read_text() == "analysis figure"
    
    def test_republish_after_rebuild(self, temp_git_repo):
        """Test republishing after rebuilding an analysis with changes."""
        repo = temp_git_repo
        output_dir = repo / "output"
        paper_dir = repo / "paper"
        
        # Create initial analysis
        (output_dir / "figures").mkdir(parents=True)
        (output_dir / "tables").mkdir(parents=True)
        (output_dir / "provenance").mkdir(parents=True)
        
        fig = output_dir / "figures" / "analysis1.pdf"
        tbl = output_dir / "tables" / "analysis1.tex"
        prov = output_dir / "provenance" / "analysis1.yml"
        
        fig.write_text("version 1 figure")
        tbl.write_text("version 1 table")
        
        write_build_record(
            out_meta=prov,
            artifact_name="analysis1",
            command=["python", "build_analysis1.py"],
            repo_root=repo,
            inputs=[],
            outputs=[fig, tbl],
        )
        
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Version 1"], cwd=repo, check=True, capture_output=True)
        
        # First publish
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["analysis1"],
            verbose=False,
        )
        
        assert (paper_dir / "figures" / "analysis1.pdf").read_text() == "version 1 figure"
        
        # Rebuild with changes
        fig.write_text("version 2 figure - updated!")
        tbl.write_text("version 2 table - updated!")
        
        # Commit changes first so repo is clean
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Modify outputs"], cwd=repo, check=True, capture_output=True)
        
        write_build_record(
            out_meta=prov,
            artifact_name="analysis1",
            command=["python", "build_analysis1.py"],
            repo_root=repo,
            inputs=[],
            outputs=[fig, tbl],
        )
        
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Version 2"], cwd=repo, check=True, capture_output=True)
        
        # Republish
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["analysis1"],
            verbose=False,
        )
        
        # Should have new content
        assert (paper_dir / "figures" / "analysis1.pdf").read_text() == "version 2 figure - updated!"
        assert (paper_dir / "tables" / "analysis1.tex").read_text() == "version 2 table - updated!"
    
    def test_publish_analysis_with_missing_output_kind(self, temp_git_repo):
        """Test publishing when analysis only has some output types."""
        repo = temp_git_repo
        output_dir = repo / "output"
        paper_dir = repo / "paper"
        
        # Create analysis with only a figure (no table)
        (output_dir / "figures").mkdir(parents=True)
        (output_dir / "provenance").mkdir(parents=True)
        
        fig = output_dir / "figures" / "fig_only.pdf"
        prov = output_dir / "provenance" / "fig_only.yml"
        
        fig.write_text("only a figure")
        
        write_build_record(
            out_meta=prov,
            artifact_name="fig_only",
            command=["python", "build_fig_only.py"],
            repo_root=repo,
            inputs=[],
            outputs=[fig],
        )
        
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add fig_only"], cwd=repo, check=True, capture_output=True)
        
        # Publish - should handle missing table gracefully
        publish_analyses(
            project_root=repo,
            paper_root=paper_dir,
            analysis_names=["fig_only"],
            verbose=False,
        )
        
        # Figure should exist
        assert (paper_dir / "figures" / "fig_only.pdf").exists()
        # Table should not exist (and that's OK)
        assert not (paper_dir / "tables" / "fig_only.tex").exists()
        
        # Provenance should only record the figure
        prov_data = yaml.safe_load((paper_dir / "provenance.yml").read_text())
        assert "figures" in prov_data["artifacts"]["fig_only"]
        assert "tables" not in prov_data["artifacts"]["fig_only"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
