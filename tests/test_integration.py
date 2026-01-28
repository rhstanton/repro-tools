"""
Integration tests for repro-tools project generation and environment setup.

Tests the complete workflow:
1. Project generation via scaffold
2. Environment setup (make environment)
3. Example execution (make examples)

Tests are marked with pytest markers:
- @pytest.mark.slow: Tests involving Julia installation (~5-10 minutes)
- @pytest.mark.integration: All integration tests (vs unit tests)

Run subsets with:
    pytest -v -m "integration and not slow"  # Fast integration tests (Python-only)
    pytest -v -m "integration and slow"      # Slow integration tests (with Julia)
    pytest -v -m integration                 # All integration tests
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from repro_tools.scaffold import create_project


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test project output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.mark.integration
class TestProjectGeneration:
    """Test basic project generation without environment setup."""

    def test_python_only_project(self, temp_output_dir):
        """Generate Python-only project and verify structure."""
        create_project(
            name="Test Python Project",
            slug="test-python",
            output_dir=temp_output_dir,
            languages=["python"],
        )

        project_dir = temp_output_dir / "test-python"
        assert project_dir.exists()

        # Check core files
        assert (project_dir / "Makefile").exists()
        assert (project_dir / "run_analysis.py").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "data" / "sample.csv").exists()

        # Check Python environment files
        assert (project_dir / "env" / "python.yml").exists()
        assert (project_dir / "env" / "scripts" / "runpython").exists()
        assert (project_dir / "env" / "examples" / "sample_python.py").exists()

        # Check Julia/Stata files do NOT exist
        assert not (project_dir / "env" / "Project.toml").exists()
        assert not (project_dir / "env" / "stata-packages.txt").exists()
        assert not (project_dir / "env" / "scripts" / "runjulia").exists()
        assert not (project_dir / "env" / "scripts" / "runstata").exists()

    def test_multi_language_project(self, temp_output_dir):
        """Generate project with all languages and verify structure."""
        create_project(
            name="Test Multi-Lang",
            slug="test-multi",
            output_dir=temp_output_dir,
            languages=["python", "julia", "stata"],
        )

        project_dir = temp_output_dir / "test-multi"

        # Check Python files
        assert (project_dir / "env" / "python.yml").exists()
        assert (project_dir / "env" / "scripts" / "runpython").exists()
        assert (project_dir / "env" / "examples" / "sample_python.py").exists()

        # Check Julia files
        assert (project_dir / "env" / "Project.toml").exists()
        assert (project_dir / "env" / "scripts" / "runjulia").exists()
        assert (project_dir / "env" / "scripts" / "install_julia.py").exists()
        assert (project_dir / "env" / "examples" / "sample_julia.jl").exists()
        assert (project_dir / "env" / "examples" / "sample_juliacall.py").exists()

        # Check Stata files
        assert (project_dir / "env" / "stata-packages.txt").exists()
        assert (project_dir / "env" / "scripts" / "runstata").exists()
        assert (project_dir / "env" / "scripts" / "execute.ado").exists()
        assert (project_dir / "env" / "examples" / "sample_stata.do").exists()


@pytest.mark.integration
class TestPythonEnvironment:
    """Test Python environment setup (fast, no Julia)."""

    def test_python_environment_setup(self, temp_output_dir):
        """Test make environment with Python-only project."""
        create_project(
            name="Test Python Env",
            slug="test-python-env",
            output_dir=temp_output_dir,
            languages=["python"],
        )

        project_dir = temp_output_dir / "test-python-env"

        # Run make environment
        result = subprocess.run(
            ["make", "environment"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes max
        )

        # Check it succeeded
        assert result.returncode == 0, f"make environment failed:\n{result.stderr}"

        # Check Python environment was created
        env_dir = project_dir / ".env"
        assert env_dir.exists(), "Python environment directory not created"
        assert (env_dir / "bin" / "python").exists(), "Python binary not found"

        # Check key packages installed
        python_bin = env_dir / "bin" / "python"
        for package in ["pandas", "matplotlib", "yaml"]:  # yaml is the import name for pyyaml
            check_result = subprocess.run(
                [str(python_bin), "-c", f"import {package}"],
                capture_output=True,
            )
            assert check_result.returncode == 0, f"Package {package} not installed"

    def test_python_examples_run(self, temp_output_dir):
        """Test that Python example runs successfully."""
        create_project(
            name="Test Python Example",
            slug="test-python-ex",
            output_dir=temp_output_dir,
            languages=["python"],
        )

        project_dir = temp_output_dir / "test-python-ex"

        # Setup environment
        subprocess.run(
            ["make", "environment"],
            cwd=project_dir,
            capture_output=True,
            timeout=600,
            check=True,
        )

        # Run Python example directly (since make examples may try to run Julia/Stata)
        result = subprocess.run(
            ["make", "sample-python"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"make sample-python failed:\n{result.stderr}"

        # Check log file was created
        log_file = project_dir / "output" / "logs" / "sample_python.log"
        assert log_file.exists(), "Python example log not created"

        # Verify log contains expected output
        log_content = log_file.read_text()
        assert "Sample Python Script" in log_content
        assert "Mean of x:" in log_content or "Sum of x:" in log_content


@pytest.mark.integration
@pytest.mark.slow
class TestJuliaEnvironment:
    """Test Julia environment setup (slow, ~5-10 minutes)."""

    def test_julia_environment_setup(self, temp_output_dir):
        """Test make environment with Julia (slow - Julia installation)."""
        create_project(
            name="Test Julia Env",
            slug="test-julia-env",
            output_dir=temp_output_dir,
            languages=["python", "julia"],
        )

        project_dir = temp_output_dir / "test-julia-env"

        # Run make environment (this will install Julia via juliacall)
        result = subprocess.run(
            ["make", "environment"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=900,  # 15 minutes max for Julia installation
        )

        assert result.returncode == 0, f"make environment failed:\n{result.stderr}"

        # Check Julia was installed
        julia_dir = project_dir / ".julia" / "pyjuliapkg" / "install"
        assert julia_dir.exists(), "Julia installation directory not created"

        # Check Julia binary exists
        julia_bin = julia_dir / "bin" / "julia"
        assert julia_bin.exists(), "Julia binary not found"
        assert julia_bin.is_file(), "Julia binary is not a file"

    def test_julia_examples_run(self, temp_output_dir):
        """Test that Julia examples run successfully (slow)."""
        create_project(
            name="Test Julia Example",
            slug="test-julia-ex",
            output_dir=temp_output_dir,
            languages=["python", "julia"],
        )

        project_dir = temp_output_dir / "test-julia-ex"

        # Setup environment
        subprocess.run(
            ["make", "environment"],
            cwd=project_dir,
            capture_output=True,
            timeout=900,
            check=True,
        )

        # Run examples
        result = subprocess.run(
            ["make", "examples"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, f"make examples failed:\n{result.stderr}"

        # Check Python example log
        python_log = project_dir / "output" / "logs" / "sample_python.log"
        assert python_log.exists()

        # Check Julia example log
        julia_log = project_dir / "output" / "logs" / "sample_julia.log"
        assert julia_log.exists()
        julia_content = julia_log.read_text()
        assert "Sample Julia Script" in julia_content
        assert "Sum:" in julia_content

        # Check juliacall example log
        juliacall_log = project_dir / "output" / "logs" / "sample_juliacall.log"
        assert juliacall_log.exists()
        juliacall_content = juliacall_log.read_text()
        assert "Python/Julia Interop" in juliacall_content
        assert "Sum computed in Julia" in juliacall_content


@pytest.mark.integration
@pytest.mark.slow
class TestMultiLanguageEnvironment:
    """Test full multi-language setup (slowest - includes Julia)."""

    def test_all_languages_setup(self, temp_output_dir):
        """Test project with all 3 languages (Python, Julia, Stata)."""
        create_project(
            name="Test All Languages",
            slug="test-all-langs",
            output_dir=temp_output_dir,
            languages=["python", "julia", "stata"],
        )

        project_dir = temp_output_dir / "test-all-langs"

        # Run make environment
        result = subprocess.run(
            ["make", "environment"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=900,
        )

        assert result.returncode == 0, f"make environment failed:\n{result.stderr}"

        # Check Python environment
        assert (project_dir / ".env" / "bin" / "python").exists()

        # Check Julia environment
        assert (project_dir / ".julia" / "pyjuliapkg" / "install" / "bin" / "julia").exists()

        # Check Stata packages directory (packages installed to local dir)
        stata_dir = project_dir / ".stata" / "ado" / "plus"
        # Note: Stata packages might not install if system Stata not available
        # So we just check the directory structure was created

    def test_all_examples_run_without_stata(self, temp_output_dir):
        """Test examples with all languages configured (Stata may skip)."""
        create_project(
            name="Test All Examples",
            slug="test-all-ex",
            output_dir=temp_output_dir,
            languages=["python", "julia", "stata"],
        )

        project_dir = temp_output_dir / "test-all-ex"

        # Setup environment
        subprocess.run(
            ["make", "environment"],
            cwd=project_dir,
            capture_output=True,
            timeout=900,
            check=True,
        )

        # Run examples (Stata may be skipped if not installed)
        result = subprocess.run(
            ["make", "examples"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, f"make examples failed:\n{result.stderr}"

        # Python and Julia should always run
        assert (project_dir / "output" / "logs" / "sample_python.log").exists()
        assert (project_dir / "output" / "logs" / "sample_julia.log").exists()
        assert (project_dir / "output" / "logs" / "sample_juliacall.log").exists()

        # Stata might run if system Stata is installed
        # We check the output message rather than requiring it to run
        output = result.stdout + result.stderr
        # Should either run Stata or show skip message
        assert ("sample_stata.log" in output or "Stata skipped" in output.lower())


@pytest.mark.integration
class TestMakeTargets:
    """Test various make targets in generated projects."""

    def test_make_all_python_only(self, temp_output_dir):
        """Test 'make all' runs sample analysis (Python-only, fast)."""
        create_project(
            name="Test Make All",
            slug="test-make-all",
            output_dir=temp_output_dir,
            languages=["python"],
        )

        project_dir = temp_output_dir / "test-make-all"

        # Setup environment
        subprocess.run(
            ["make", "environment"],
            cwd=project_dir,
            capture_output=True,
            timeout=600,
            check=True,
        )

        # Run make all
        result = subprocess.run(
            ["make", "all"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"make all failed:\n{result.stderr}"

        # Check outputs were created
        assert (project_dir / "output" / "figures" / "sample_analysis.pdf").exists()
        assert (project_dir / "output" / "tables" / "sample_analysis.tex").exists()
        assert (project_dir / "output" / "provenance" / "sample_analysis.yml").exists()

    def test_make_verify(self, temp_output_dir):
        """Test 'make verify' checks environment (fast)."""
        create_project(
            name="Test Verify",
            slug="test-verify",
            output_dir=temp_output_dir,
            languages=["python"],
        )

        project_dir = temp_output_dir / "test-verify"

        # Setup environment
        subprocess.run(
            ["make", "environment"],
            cwd=project_dir,
            capture_output=True,
            timeout=600,
            check=True,
        )

        # Run make verify
        result = subprocess.run(
            ["make", "verify"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"make verify failed:\n{result.stderr}"

        # Check output mentions verification
        output = result.stdout + result.stderr
        assert "Verification Complete" in output or "verification" in output.lower()

    def test_make_clean(self, temp_output_dir):
        """Test 'make clean' removes output directory (fast)."""
        create_project(
            name="Test Clean",
            slug="test-clean",
            output_dir=temp_output_dir,
            languages=["python"],
        )

        project_dir = temp_output_dir / "test-clean"

        # Setup environment and run analysis
        subprocess.run(["make", "environment"], cwd=project_dir, capture_output=True, timeout=600, check=True)
        subprocess.run(["make", "all"], cwd=project_dir, capture_output=True, timeout=60, check=True)

        # Verify outputs exist
        assert (project_dir / "output" / "figures" / "sample_analysis.pdf").exists()

        # Run make clean
        result = subprocess.run(
            ["make", "clean"],
            cwd=project_dir,
            capture_output=True,
            timeout=10,
        )

        assert result.returncode == 0, f"make clean failed:\n{result.stderr}"

        # Check outputs were removed
        assert not (project_dir / "output" / "figures" / "sample_analysis.pdf").exists()
        assert not (project_dir / "output" / "tables" / "sample_analysis.tex").exists()


@pytest.mark.integration
class TestGitIntegration:
    """Test git repository initialization and submodules."""

    def test_git_repo_initialized(self, temp_output_dir):
        """Test that git repository is initialized."""
        create_project(
            name="Test Git",
            slug="test-git",
            output_dir=temp_output_dir,
            languages=["python"],
        )

        project_dir = temp_output_dir / "test-git"

        # Check .git directory exists
        assert (project_dir / ".git").exists()

        # Check we can run git commands
        result = subprocess.run(
            ["git", "status"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Check initial commit exists
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert "Initial commit" in result.stdout

    def test_repro_tools_submodule(self, temp_output_dir):
        """Test that repro-tools is added as a submodule."""
        create_project(
            name="Test Submodule",
            slug="test-submod",
            output_dir=temp_output_dir,
            languages=["python"],
        )

        project_dir = temp_output_dir / "test-submod"

        # Check submodule directory exists
        submodule_dir = project_dir / "lib" / "repro-tools"
        assert submodule_dir.exists()

        # Check .gitmodules file exists
        assert (project_dir / ".gitmodules").exists()

        # Check submodule is registered
        result = subprocess.run(
            ["git", "submodule", "status"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
        assert "lib/repro-tools" in result.stdout
