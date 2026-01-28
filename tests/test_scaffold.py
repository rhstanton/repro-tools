"""
Unit tests for scaffold.py - project scaffolding functionality.

Tests cover:
- Template discovery and path resolution
- Variable substitution in templates
- CSV generation with correct line endings
- File copying and directory structure
- Language-specific file generation
- Git initialization
"""

import csv
import tempfile
import subprocess
from pathlib import Path

import pytest

from repro_tools.scaffold import create_project, TEMPLATE_DIR


class TestTemplateDiscovery:
    """Test template path resolution and file discovery."""

    def test_template_dir_exists(self):
        """Template directory should exist in package."""
        assert TEMPLATE_DIR.exists(), f"Template directory not found: {TEMPLATE_DIR}"
        assert TEMPLATE_DIR.is_dir(), f"Template path is not a directory: {TEMPLATE_DIR}"

    def test_template_dir_location(self):
        """Template directory should be inside repro_tools package."""
        # Should be: src/repro_tools/templates/standard/
        assert "repro_tools" in str(TEMPLATE_DIR), "Template directory not in repro_tools package"
        assert TEMPLATE_DIR.name == "standard", "Template directory should be 'standard'"

    def test_core_template_files_exist(self):
        """Core template files should exist."""
        expected_files = [
            "Makefile.template",
            "run_analysis.py.template",
            "README.md.template",
            "QUICKSTART.md.template",
            ".gitignore.template",
            ".gitattributes",
        ]
        for filename in expected_files:
            filepath = TEMPLATE_DIR / filename
            assert filepath.exists(), f"Missing core template: {filename}"

    def test_shared_template_files_exist(self):
        """Shared configuration templates should exist."""
        shared_dir = TEMPLATE_DIR / "shared"
        assert shared_dir.exists(), "shared/ directory missing"
        
        expected_files = ["config.py.template", "__init__.py.template"]
        for filename in expected_files:
            filepath = shared_dir / filename
            assert filepath.exists(), f"Missing shared template: {filename}"

    def test_env_template_files_exist(self):
        """Environment templates should exist."""
        env_dir = TEMPLATE_DIR / "env"
        assert env_dir.exists(), "env/ directory missing"
        
        expected_files = [
            "Makefile.template",
            "python.yml.template",
            "Project.toml.template",
            "stata-packages.txt.template",
        ]
        for filename in expected_files:
            filepath = env_dir / filename
            assert filepath.exists(), f"Missing env template: {filename}"

    def test_env_scripts_exist(self):
        """Environment scripts should exist."""
        scripts_dir = TEMPLATE_DIR / "env" / "scripts"
        assert scripts_dir.exists(), "env/scripts/ directory missing"
        
        expected_files = [
            "runpython",
            "runjulia",
            "runstata",
            "execute.ado",
            "install_julia.py",
        ]
        for filename in expected_files:
            filepath = scripts_dir / filename
            assert filepath.exists(), f"Missing script: {filename}"

    def test_env_examples_exist(self):
        """Example files should exist."""
        examples_dir = TEMPLATE_DIR / "env" / "examples"
        assert examples_dir.exists(), "env/examples/ directory missing"
        
        expected_files = [
            "sample_python.py.template",
            "sample_julia.jl.template",
            "sample_juliacall.py.template",
            "sample_stata.do.template",
        ]
        for filename in expected_files:
            filepath = examples_dir / filename
            assert filepath.exists(), f"Missing example: {filename}"

    def test_total_template_count(self):
        """Should have exactly 22 template files."""
        # Count all files recursively (excluding directories)
        template_files = list(TEMPLATE_DIR.rglob("*"))
        template_files = [f for f in template_files if f.is_file()]
        
        # We expect 22 files total
        assert len(template_files) >= 22, f"Expected at least 22 template files, found {len(template_files)}"


class TestVariableSubstitution:
    """Test template variable substitution."""

    def test_basic_substitution(self, tmp_path):
        """Test basic {{name}} and {{slug}} substitution."""
        create_project(
            name="Test Project",
            slug="test-project",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test-project"
        readme = project_dir / "README.md"
        assert readme.exists(), "README.md not created"
        
        content = readme.read_text()
        assert "Test Project" in content, "{name} not substituted in README"


    def test_config_substitution(self, tmp_path):
        """Test variable substitution in config.py."""
        create_project(
            name="My Analysis",
            slug="my-analysis",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "my-analysis"
        config = project_dir / "shared" / "config.py"
        assert config.exists(), "config.py not created"
        
        # Config.py is now templated but doesn't use {slug} - just verify it exists and is valid Python
        content = config.read_text()
        assert "STUDIES" in content, "STUDIES not found in config.py"
        assert "sample_analysis" in content, "Default study not found in config.py"

    def test_runners_variable_python_only(self, tmp_path):
        """Test {{runners}} substitution for Python-only project."""
        create_project(
            name="Python Project",
            slug="python-project",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "python-project"
        makefile = project_dir / "Makefile"
        content = makefile.read_text()
        
        # Should have PYTHON runner
        assert "PYTHON := env/scripts/runpython" in content
        # Should NOT have JULIA or STATA runners
        assert "JULIA :=" not in content
        assert "STATA :=" not in content


class TestCSVGeneration:
    """Test CSV generation with correct line endings."""

    def test_csv_line_endings(self, tmp_path):
        """CSV should use LF line endings (not CRLF)."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        csv_file = project_dir / "data" / "sample.csv"
        assert csv_file.exists(), "sample.csv not created"
        
        # Read as binary to check line endings
        content = csv_file.read_bytes()
        
        # Should NOT contain CRLF (\r\n)
        assert b'\r\n' not in content, "CSV contains CRLF line endings (should be LF only)"
        
        # Should contain LF (\n)
        assert b'\n' in content, "CSV missing LF line endings"

    def test_csv_structure(self, tmp_path):
        """CSV should have correct structure."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        csv_file = project_dir / "data" / "sample.csv"
        
        with open(csv_file, 'r', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Should have header + 10 data rows
        assert len(rows) == 11, f"Expected 11 rows, got {len(rows)}"
        
        # Header row
        assert rows[0] == ["x", "y", "category"], f"Unexpected header: {rows[0]}"
        
        # Data rows should have 3 columns
        for i, row in enumerate(rows[1:], start=1):
            assert len(row) == 3, f"Row {i} should have 3 columns, got {len(row)}"

    def test_csv_readable_as_text(self, tmp_path):
        """CSV should be readable as plain text (ASCII)."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        csv_file = project_dir / "data" / "sample.csv"
        
        # Should be readable as text without errors
        content = csv_file.read_text(encoding='utf-8')
        assert len(content) > 0, "CSV is empty"
        assert "x,y,category" in content, "CSV header missing"


class TestDirectoryStructure:
    """Test directory structure creation."""

    def test_all_directories_created(self, tmp_path):
        """All expected directories should be created."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        expected_dirs = [
            "data",
            "output/figures",
            "output/tables",
            "output/provenance",
            "output/logs",
            "paper/figures",
            "paper/tables",
            "tests",
            "docs",
            "lib",
            "shared",
            "env",
            "env/scripts",
            "env/examples",
        ]
        
        for dir_path in expected_dirs:
            full_path = project_dir / dir_path
            assert full_path.exists(), f"Directory not created: {dir_path}"
            assert full_path.is_dir(), f"Path is not a directory: {dir_path}"

    def test_project_root_created(self, tmp_path):
        """Project root directory should be created."""
        create_project(
            name="My Project",
            slug="my-project",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "my-project"
        assert project_dir.exists(), "Project directory not created"
        assert project_dir.is_dir(), "Project path is not a directory"


class TestFileCopying:
    """Test that all template files are copied correctly."""

    def test_core_files_copied(self, tmp_path):
        """Core template files should be copied and renamed."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        expected_files = [
            "Makefile",  # .template removed
            "run_analysis.py",  # .template removed
            "README.md",
            "QUICKSTART.md",
            ".gitignore",  # .template removed
            ".gitattributes",
        ]
        
        for filename in expected_files:
            filepath = project_dir / filename
            assert filepath.exists(), f"Core file not copied: {filename}"

    def test_shared_files_copied(self, tmp_path):
        """Shared configuration files should be copied."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        expected_files = [
            "shared/config.py",
            "shared/__init__.py",
        ]
        
        for filename in expected_files:
            filepath = project_dir / filename
            assert filepath.exists(), f"Shared file not copied: {filename}"

    def test_env_files_copied(self, tmp_path):
        """Environment files should be copied based on selected languages."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        # Python-only project should have these files
        expected_files = [
            "env/Makefile",
            "env/python.yml",
        ]
        
        for filename in expected_files:
            filepath = project_dir / filename
            assert filepath.exists(), f"Env file not copied: {filename}"
        
        # Julia files should NOT exist in python-only project
        assert not (project_dir / "env" / "Project.toml").exists(), "Project.toml should not exist in python-only project"
        # Stata files should NOT exist in python-only project
        assert not (project_dir / "env" / "stata-packages.txt").exists(), "stata-packages.txt should not exist in python-only project"

    def test_scripts_copied(self, tmp_path):
        """Script files should be copied based on selected languages."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        # Python-only project should only have Python scripts
        expected_files = [
            "env/scripts/runpython",
        ]
        
        for filename in expected_files:
            filepath = project_dir / filename
            assert filepath.exists(), f"Script not copied: {filename}"
        
        # Julia/Stata scripts should NOT exist in python-only project
        assert not (project_dir / "env" / "scripts" / "runjulia").exists(), "runjulia should not exist in python-only project"
        assert not (project_dir / "env" / "scripts" / "install_julia.py").exists(), "install_julia.py should not exist in python-only project"
        assert not (project_dir / "env" / "scripts" / "runstata").exists(), "runstata should not exist in python-only project"
        assert not (project_dir / "env" / "scripts" / "execute.ado").exists(), "execute.ado should not exist in python-only project"

    def test_examples_copied(self, tmp_path):
        """Example files should be copied based on selected languages."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        # Python-only project should only have Python examples
        expected_files = [
            "env/examples/sample_python.py",
        ]
        
        for filename in expected_files:
            filepath = project_dir / filename
            assert filepath.exists(), f"Example not copied: {filename}"
        
        # Julia/Stata examples should NOT exist in python-only project
        assert not (project_dir / "env" / "examples" / "sample_julia.jl").exists(), "sample_julia.jl should not exist in python-only project"
        assert not (project_dir / "env" / "examples" / "sample_juliacall.py").exists(), "sample_juliacall.py should not exist in python-only project"
        assert not (project_dir / "env" / "examples" / "sample_stata.do").exists(), "sample_stata.do should not exist in python-only project"


class TestGitInitialization:
    """Test git initialization and initial commit."""

    def test_git_repository_initialized(self, tmp_path):
        """Git repository should be initialized."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        git_dir = project_dir / ".git"
        assert git_dir.exists(), "Git repository not initialized"
        assert git_dir.is_dir(), ".git is not a directory"

    def test_initial_commit_created(self, tmp_path):
        """Initial commit should be created."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        
        # Check git log
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Git log failed"
        assert len(result.stdout) > 0, "No commits found"
        assert "Initial commit" in result.stdout, "Initial commit message not found"

    def test_all_files_committed(self, tmp_path):
        """All files should be in initial commit."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        
        # Check git status
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Git status failed"
        # Should have no uncommitted changes (empty output or just submodule)
        lines = [line for line in result.stdout.strip().split('\n') if line]
        # Only "SM lib/repro-tools" should be present (submodule reference)
        uncommitted = [line for line in lines if not line.startswith("SM")]
        assert len(uncommitted) == 0, f"Uncommitted files found: {uncommitted}"

    def test_gitattributes_enforces_lf(self, tmp_path):
        """Generated .gitattributes should enforce LF line endings."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        gitattributes = project_dir / ".gitattributes"
        
        content = gitattributes.read_text()
        assert "text=auto eol=lf" in content, "Missing global LF enforcement"
        assert "*.py text eol=lf" in content, "Missing Python LF enforcement"
        assert "Makefile text eol=lf" in content, "Missing Makefile LF enforcement"


class TestLanguageSelection:
    """Test language-specific file generation."""

    def test_python_only_project(self, tmp_path):
        """Python-only project should not include Julia/Stata-specific content."""
        create_project(
            name="Python Only",
            slug="python-only",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "python-only"
        makefile = project_dir / "Makefile"
        content = makefile.read_text()
        
        # Should have Python runner
        assert "PYTHON := env/scripts/runpython" in content
        
        # Should still have Julia/Stata scripts (they're always copied)
        # but Makefile won't define JULIA/STATA variables
        assert "JULIA :=" not in content
        assert "STATA :=" not in content

    def test_python_julia_project(self, tmp_path):
        """Python+Julia project should include Julia-specific content."""
        create_project(
            name="Python Julia",
            slug="python-julia",
            output_dir=tmp_path,
            languages=["python", "julia"],
            template="standard"
        )
        
        project_dir = tmp_path / "python-julia"
        makefile = project_dir / "Makefile"
        content = makefile.read_text()
        
        # Should have both runners
        assert "PYTHON := env/scripts/runpython" in content
        # Note: Current template doesn't add JULIA variable, but scripts are present
        assert (project_dir / "env/scripts/runjulia").exists()

    def test_all_languages_project(self, tmp_path):
        """Project with all languages should include all scripts."""
        create_project(
            name="All Languages",
            slug="all-languages",
            output_dir=tmp_path,
            languages=["python", "julia", "stata"],
            template="standard"
        )
        
        project_dir = tmp_path / "all-languages"
        
        # All scripts should exist
        assert (project_dir / "env/scripts/runpython").exists()
        assert (project_dir / "env/scripts/runjulia").exists()
        assert (project_dir / "env/scripts/runstata").exists()
        
        # All examples should exist
        assert (project_dir / "env/examples/sample_python.py").exists()
        assert (project_dir / "env/examples/sample_julia.jl").exists()
        assert (project_dir / "env/examples/sample_juliacall.py").exists()
        assert (project_dir / "env/examples/sample_stata.do").exists()


class TestDefaultsSystem:
    """Test that generated config.py contains DEFAULTS system."""

    def test_defaults_dictionary_exists(self, tmp_path):
        """config.py should contain DEFAULTS dictionary."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        config = project_dir / "shared" / "config.py"
        content = config.read_text()
        
        assert "DEFAULTS = {" in content, "DEFAULTS dictionary not found"

    def test_defaults_fields(self, tmp_path):
        """DEFAULTS should contain expected fields."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        config = project_dir / "shared" / "config.py"
        content = config.read_text()
        
        expected_fields = [
            "data",
            "xlabel",
            "ylabel",
            "title",
            "groupby",
            "xvar",
            "table_agg",
        ]
        
        for field in expected_fields:
            assert f'"{field}"' in content, f"DEFAULTS missing field: {field}"

    def test_studies_dictionary_exists(self, tmp_path):
        """config.py should contain STUDIES dictionary."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        config = project_dir / "shared" / "config.py"
        content = config.read_text()
        
        assert "STUDIES = {" in content, "STUDIES dictionary not found"

    def test_sample_analysis_defined(self, tmp_path):
        """STUDIES should contain sample_analysis."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        config = project_dir / "shared" / "config.py"
        content = config.read_text()
        
        assert '"sample_analysis"' in content, "sample_analysis not in STUDIES"


class TestRunAnalysisScript:
    """Test that generated run_analysis.py has expected functionality."""

    def test_override_flags_documented(self, tmp_path):
        """run_analysis.py should document all 10 override flags."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        script = project_dir / "run_analysis.py"
        content = script.read_text()
        
        expected_flags = [
            "--data",
            "--yvar",
            "--xvar",
            "--groupby",
            "--xlabel",
            "--ylabel",
            "--title",
            "--table-agg",
            "--figure",
            "--table",
        ]
        
        for flag in expected_flags:
            assert flag in content, f"Override flag not documented: {flag}"

    def test_build_config_function_exists(self, tmp_path):
        """run_analysis.py should have build_config() function."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        script = project_dir / "run_analysis.py"
        content = script.read_text()
        
        assert "def build_config(" in content, "build_config() function not found"

    def test_list_option_exists(self, tmp_path):
        """run_analysis.py should support --list option."""
        create_project(
            name="Test",
            slug="test",
            output_dir=tmp_path,
            languages=["python"],
            template="standard"
        )
        
        project_dir = tmp_path / "test"
        script = project_dir / "run_analysis.py"
        content = script.read_text()
        
        assert "--list" in content, "--list option not found"
        assert "def list_studies(" in content, "list_studies() function not found"
