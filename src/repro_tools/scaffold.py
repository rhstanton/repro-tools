"""Project scaffolding - generate new research projects from template."""

from pathlib import Path
import subprocess
import sys
from typing import Optional


def create_project(
    name: str,
    slug: str,
    output_dir: Path,
    languages: list[str],
    template: str = "standard",
    interactive: bool = False,
) -> None:
    """Create a new research project from template.
    
    Args:
        name: Project display name (e.g., "My Research Project")
        slug: Project directory name (e.g., "my-project")
        output_dir: Parent directory where project will be created
        languages: List of languages to include ["python", "julia", "stata"]
        template: Template type ("standard", "minimal")
        interactive: Whether to prompt for missing values
    """
    project_dir = output_dir / slug
    
    if project_dir.exists():
        print(f"❌ Error: Directory already exists: {project_dir}")
        sys.exit(1)
    
    print(f"Creating new research project: {name}")
    print(f"Location: {project_dir}")
    print(f"Languages: {', '.join(languages)}")
    print()
    
    # Create directory structure
    print("📁 Creating directory structure...")
    dirs = [
        project_dir,
        project_dir / "data",
        project_dir / "env" / "scripts",
        project_dir / "env" / "examples",
        project_dir / "output" / "figures",
        project_dir / "output" / "tables",
        project_dir / "output" / "provenance",
        project_dir / "output" / "logs",
        project_dir / "paper" / "figures",
        project_dir / "paper" / "tables",
        project_dir / "shared",
        project_dir / "tests",
        project_dir / "docs",
        project_dir / "lib",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {d.relative_to(output_dir)}")
    
    # Initialize git repository
    print("\n📦 Initializing git repository...")
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    print("  ✓ Git repository initialized")
    
    # Add repro-tools as submodule
    print("\n📦 Adding repro-tools submodule...")
    subprocess.run(
        ["git", "submodule", "add", "https://github.com/rhstanton/repro-tools.git", "lib/repro-tools"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    print("  ✓ repro-tools submodule added")
    
    # Generate Makefile
    print("\n📄 Generating Makefile...")
    makefile_content = generate_makefile(name, slug, languages)
    (project_dir / "Makefile").write_text(makefile_content)
    print("  ✓ Makefile created (includes common.mk)")
    
    # Generate config.py
    print("\n📄 Generating configuration...")
    config_content = generate_config(slug)
    (project_dir / "shared" / "config.py").write_text(config_content)
    print("  ✓ shared/config.py created")
    
    # Generate __init__.py files
    (project_dir / "shared" / "__init__.py").write_text('"""Shared utilities for analysis."""\n')
    (project_dir / "tests" / "__init__.py").write_text('"""Test suite."""\n')
    
    # Generate sample analysis script
    print("\n📄 Generating sample analysis...")
    analysis_content = generate_analysis_script()
    (project_dir / "run_analysis.py").write_text(analysis_content)
    print("  ✓ run_analysis.py created")
    
    # Generate environment files
    print("\n📄 Generating environment files...")
    generate_environment_files(project_dir, languages)
    print("  ✓ env/python.yml, env/Project.toml, env/Makefile created")
    
    # Generate documentation
    print("\n📄 Generating documentation...")
    readme_content = generate_readme(name, slug)
    (project_dir / "README.md").write_text(readme_content)
    quickstart_content = generate_quickstart(name)
    (project_dir / "QUICKSTART.md").write_text(quickstart_content)
    print("  ✓ README.md, QUICKSTART.md created")
    
    # Generate .gitignore
    print("\n📄 Generating .gitignore...")
    gitignore_content = generate_gitignore()
    (project_dir / ".gitignore").write_text(gitignore_content)
    print("  ✓ .gitignore created")
    
    # Generate sample data
    print("\n📄 Generating sample data...")
    generate_sample_data(project_dir)
    print("  ✓ data/sample.csv created")
    
    # Initial git commit
    print("\n📦 Creating initial commit...")
    subprocess.run(["git", "add", "-A"], cwd=project_dir, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit: Generated from repro-tools scaffold"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    print("  ✓ Initial commit created")
    
    print("\n" + "=" * 60)
    print("✅ Project created successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print(f"  1. cd {project_dir}")
    print("  2. make environment  # Setup Python/Julia environments (~10 min)")
    print("  3. make all          # Run sample analysis")
    print("  4. Customize:")
    print("     - Edit shared/config.py to add your studies")
    print("     - Add data files to data/")
    print("     - Customize run_analysis.py or create new scripts")
    print()


def generate_makefile(name: str, slug: str, languages: list[str]) -> str:
    """Generate minimal Makefile that includes common.mk."""
    # Determine which environment wrappers to set up
    runners = ["PYTHON := env/scripts/runpython"]
    if "julia" in languages:
        runners.append("JULIA  := env/scripts/runjulia")
    if "stata" in languages:
        runners.append("STATA  := env/scripts/runstata")
    
    return f'''# ==============================================================================
# {name} - Makefile
# ==============================================================================

# Delete partial outputs on error
.DELETE_ON_ERROR:

# Default shell with safer options
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# Ensure git submodules are initialized
$(shell git submodule update --init --recursive 2>/dev/null || true)

# ==============================================================================
# Environment Variables
# ==============================================================================

# Julia threading (auto-detect CPU cores)
export JULIA_NUM_THREADS ?= $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)

# ==============================================================================
# Executable Scripts
# ==============================================================================

{chr(10).join(runners)}

# repro-tools CLI commands
REPRO_CHECK   := .env/bin/repro-check
REPRO_PUBLISH := .env/bin/repro-publish
REPRO_COMPARE := .env/bin/repro-compare
REPRO_SYSINFO := .env/bin/repro-sysinfo
REPRO_REPORT  := .env/bin/repro-report

# ==============================================================================
# Analysis Definitions
# ==============================================================================

# All analyses to run
ANALYSES := sample_analysis

# Input data files
DATA := data/sample.csv

# ==============================================================================
# Directory Paths
# ==============================================================================

REPO_ROOT := $(shell pwd)

OUT_FIG_DIR := output/figures
OUT_TBL_DIR := output/tables
OUT_PROV_DIR := output/provenance
OUT_LOG_DIR := output/logs

PAPER_DIR := paper
PAPER_FIG_DIR := $(PAPER_DIR)/figures
PAPER_TBL_DIR := $(PAPER_DIR)/tables

# Default target
.DEFAULT_GOAL := default

# ==============================================================================
# Include Generic Targets from repro-tools
# ==============================================================================

include lib/repro-tools/lib/common.mk

# ==============================================================================
# Main Build Targets
# ==============================================================================

.PHONY: all
all:
\t@rm -f .make_build_marker
\t@$(MAKE) --no-print-directory $(ANALYSES)
\t@if [ -f .make_build_marker ]; then \\
\t\techo ""; \\
\t\techo "✓ All analyses complete!"; \\
\t\techo ""; \\
\t\trm -f .make_build_marker; \\
\telse \\
\t\techo ""; \\
\t\techo "✓ Nothing to do - all outputs up-to-date"; \\
\t\techo ""; \\
\tfi

# ==============================================================================
# Analysis Build Rules
# ==============================================================================

# sample_analysis definition
sample_analysis.script  := run_analysis.py
sample_analysis.runner  := $(PYTHON)
sample_analysis.inputs  := $(DATA)
sample_analysis.outputs := $(OUT_FIG_DIR)/sample_analysis.pdf $(OUT_TBL_DIR)/sample_analysis.tex $(OUT_PROV_DIR)/sample_analysis.yml
sample_analysis.args    := sample_analysis

# Rule generator macro
define make-analysis-rule

$($(1).outputs) &: $($(1).script) $($(1).inputs) | $(OUT_FIG_DIR) $(OUT_TBL_DIR) $(OUT_PROV_DIR) $(OUT_LOG_DIR)
\t@echo "========================================"
\t@echo "Running analysis: $(1)"
\t@echo "========================================"
\t$($(1).runner) $($(1).script) $($(1).args) 2>&1 | tee $(OUT_LOG_DIR)/$(1).log
\t@echo "✓ $(1) complete"
\t@echo "Built: $(1)" >> .make_build_marker

.PHONY: $(1)
$(1): $($(1).outputs)

endef

# Generate rules for all analyses
$(foreach analysis,$(ANALYSES),$(eval $(call make-analysis-rule,$(analysis))))

# Ensure output directories exist
$(OUT_FIG_DIR) $(OUT_TBL_DIR) $(OUT_PROV_DIR) $(OUT_LOG_DIR):
\t@mkdir -p $@

# ==============================================================================
# Publishing
# ==============================================================================

PUBLISH_ANALYSES ?= $(ANALYSES)
PUBLISH_STAMP_DIR := .publish_stamps

.PHONY: publish publish-force
publish:
\t@echo "Publishing to paper/..."
\t@$(MAKE) --no-print-directory -s $(addprefix $(PUBLISH_STAMP_DIR)/,$(addsuffix .stamp,$(PUBLISH_ANALYSES)))
\t@echo "✓ Publishing complete"

publish-force:
\t@rm -rf $(PUBLISH_STAMP_DIR)
\t@$(MAKE) publish

$(PUBLISH_STAMP_DIR)/%.stamp: $(OUT_FIG_DIR)/%.pdf $(OUT_TBL_DIR)/%.tex $(OUT_PROV_DIR)/%.yml
\t@mkdir -p $(PUBLISH_STAMP_DIR) $(PAPER_FIG_DIR) $(PAPER_TBL_DIR)
\t@$(REPRO_PUBLISH) analyses --paper-root $(PAPER_DIR) --project-root . "$*"
\t@touch $@

# ==============================================================================
# Utility Targets
# ==============================================================================

.PHONY: list-analyses
list-analyses:
\t@echo "Available analyses:"
\t@for name in $(ANALYSES); do echo "  - $$name"; done

# ==============================================================================
# Help Targets
# ==============================================================================

.PHONY: default
default:
\t@echo ""
\t@echo "{name}"
\t@echo "{'=' * len(name)}"
\t@echo ""
\t@echo "ESSENTIAL COMMANDS:"
\t@echo "  make environment  Setup environments (~10 min)"
\t@echo "  make all          Run all analyses"
\t@echo "  make verify       Quick environment check"
\t@echo "  make publish      Publish to paper/"
\t@echo "  make clean        Remove outputs"
\t@echo ""
\t@echo "  make help         Show all commands"
\t@echo ""

.PHONY: help
help:
\t@echo "{name} - Available Commands"
\t@echo ""
\t@echo "ENVIRONMENT:"
\t@echo "  make environment  Setup Python/Julia/Stata"
\t@echo "  make verify       Quick verification check"
\t@echo ""
\t@echo "BUILD:"
\t@echo "  make all          Run all analyses"
\t@echo "  make $(word 1,$(ANALYSES))     Run specific analysis"
\t@echo ""
\t@echo "PUBLISH:"
\t@echo "  make publish      Publish to paper/"
\t@echo ""
\t@echo "CLEANUP:"
\t@echo "  make clean        Remove outputs"
\t@echo "  make cleanall     Remove outputs + environments"
\t@echo ""
'''


def generate_config(slug: str) -> str:
    """Generate shared/config.py with sample study."""
    return '''"""Project configuration - centralized paths and study definitions."""

from pathlib import Path

# ==============================================================================
# Directory Paths
# ==============================================================================

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUT_DIR = REPO_ROOT / "output"

# ==============================================================================
# Data Files
# ==============================================================================

DATA_FILES = {
    "sample": DATA_DIR / "sample.csv",
}

# ==============================================================================
# Study Definitions
# ==============================================================================

STUDIES = {
    "sample_analysis": {
        "data": DATA_FILES["sample"],
        "xlabel": "X Variable",
        "ylabel": "Y Variable",
        "title": "Sample Analysis",
        "groupby": None,
        "yvar": "y",
        "xvar": "x",
        "table_agg": "mean",
        "figure": OUTPUT_DIR / "figures" / "sample_analysis.pdf",
        "table": OUTPUT_DIR / "tables" / "sample_analysis.tex",
    },
}
'''


def generate_analysis_script() -> str:
    """Generate run_analysis.py script."""
    return '''#!/usr/bin/env python
"""Unified analysis runner - handles all studies via configuration."""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from docopt import docopt
from repro_tools import auto_build_record, validate_study_config

# Add repo root to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

from shared.config import STUDIES

__doc__ = """
Usage:
  run_analysis.py <study> [options]
  run_analysis.py --list
  run_analysis.py --version

Arguments:
  <study>           Study name from config.STUDIES

Options:
  --list            List available studies
  --version         Show version

Example:
  run_analysis.py sample_analysis
"""


def main():
    args = docopt(__doc__)
    
    if args["--list"]:
        print("Available studies:")
        for name in STUDIES.keys():
            print(f"  - {name}")
        return
    
    if args["--version"]:
        print("run_analysis.py v1.0.0")
        return
    
    study_name = args["<study>"]
    
    if study_name not in STUDIES:
        print(f"❌ Error: Unknown study: {study_name}")
        print(f"Available: {', '.join(STUDIES.keys())}")
        sys.exit(1)
    
    config = STUDIES[study_name]
    
    # Validate configuration
    errors = validate_study_config(config, study_name)
    if errors:
        print(f"❌ Configuration errors in '{study_name}':")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    
    # Run analysis
    print(f"Running: {study_name}")
    
    # Load data
    df = pd.read_csv(config["data"])
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))
    if config.get("groupby"):
        for group in df[config["groupby"]].unique():
            subset = df[df[config["groupby"]] == group]
            ax.plot(subset[config["xvar"]], subset[config["yvar"]], 
                   marker='o', label=str(group))
        ax.legend()
    else:
        ax.plot(df[config["xvar"]], df[config["yvar"]], marker='o')
    
    ax.set_xlabel(config["xlabel"])
    ax.set_ylabel(config["ylabel"])
    ax.set_title(config["title"])
    ax.grid(True, alpha=0.3)
    
    # Save figure
    config["figure"].parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(config["figure"], bbox_inches="tight", dpi=300)
    plt.close(fig)
    
    # Create table
    if config.get("groupby"):
        table = df.groupby(config["groupby"])[config["yvar"]].agg(
            config["table_agg"]
        ).reset_index()
    else:
        table = df[[config["xvar"], config["yvar"]]].describe()
    
    # Save table
    config["table"].parent.mkdir(parents=True, exist_ok=True)
    table.to_latex(config["table"], index=False)
    
    # Generate provenance
    prov_file = config["figure"].parent.parent / "provenance" / f"{study_name}.yml"
    prov_file.parent.mkdir(parents=True, exist_ok=True)
    
    auto_build_record(
        artifact_name=study_name,
        out_meta=prov_file,
        inputs=[config["data"]],
        outputs=[config["figure"], config["table"]],
    )
    
    print(f"✓ {study_name} complete")
    print(f"  Figure: {config['figure']}")
    print(f"  Table: {config['table']}")
    print(f"  Provenance: {prov_file}")


if __name__ == "__main__":
    main()
'''


def generate_environment_files(project_dir: Path, languages: list[str]) -> None:
    """Generate env/ directory files."""
    # Python environment
    python_yml = f'''name: research_env
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pandas
  - matplotlib
  - numpy
  - pyyaml
  - jinja2
  - pytest
  - ruff
  - mypy
  - pip:
    - docopt
    - -e ../lib/repro-tools
'''
    
    if "julia" in languages:
        python_yml += "    - juliacall>=0.9.14\n"
    
    (project_dir / "env" / "python.yml").write_text(python_yml)
    
    # Julia Project.toml
    if "julia" in languages:
        project_toml = '''[deps]
PythonCall = "6099a3de-0909-46bc-b1f4-468b9a2dfc0d"
DataFrames = "a93c6f00-e57d-5684-b7b6-d8193f3e46c0"

[compat]
julia = "1.10, 1.11, 1.12"
PythonCall = "0.9"
DataFrames = "1"
'''
        (project_dir / "env" / "Project.toml").write_text(project_toml)
    
    # env/Makefile
    env_makefile = '''# Environment setup Makefile

ENV_DIR := $(strip $(CURDIR))
REPO_ROOT := $(abspath $(ENV_DIR)/..)

.PHONY: all-env python-env julia-install-via-python

all-env: python-env
'''
    
    if "julia" in languages:
        env_makefile += "\t$(MAKE) julia-install-via-python\n"
    
    env_makefile += '''
python-env:
\t@echo "📦 Installing Python environment..."
\t@if command -v mamba >/dev/null 2>&1; then \\
\t\tmamba env create -f python.yml -p ../.env -y || mamba env update -f python.yml -p ../.env; \\
\telif command -v conda >/dev/null 2>&1; then \\
\t\tconda env create -f python.yml -p ../.env -y || conda env update -f python.yml -p ../.env; \\
\telse \\
\t\techo "❌ conda/mamba not found. Installing micromamba..."; \\
\t\tbash scripts/install_micromamba.sh; \\
\t\tmicromamba env create -f python.yml -p ../.env -y; \\
\tfi
\t@echo "✓ Python environment ready"

'''
    
    if "julia" in languages:
        env_makefile += '''julia-install-via-python:
\t@echo ">> Installing Julia via juliacall..."
\t@cd $(REPO_ROOT) && $(REPO_ROOT)/env/scripts/runpython $(REPO_ROOT)/env/scripts/install_julia.py
'''
    
    (project_dir / "env" / "Makefile").write_text(env_makefile)
    
    # Create runpython wrapper
    runpython = '''#!/usr/bin/env bash
set -euo pipefail
unset CDPATH
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="$REPO_ROOT/.env/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "❌ Python environment not found. Run: make environment"
  exit 1
fi

# Julia/Python bridge configuration
export PYTHON_JULIACALL_HANDLE_SIGNALS=yes
export PYTHON_JULIAPKG_PROJECT="$REPO_ROOT/.julia"
export JULIA_PROJECT="$REPO_ROOT/env"
export JULIA_DEPOT_PATH="$REPO_ROOT/.julia"
export JULIA_LOAD_PATH="$JULIA_PROJECT:$PYTHON_JULIAPKG_PROJECT:@stdlib"
export JULIA_CONDAPKG_BACKEND=Null

export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Prefer bundled Julia; if not present, strip juliaup from PATH to force local install
BUNDLED_JULIA="$REPO_ROOT/.julia/pyjuliapkg/install/bin/julia"
if [[ -x "$BUNDLED_JULIA" ]]; then
  export PYTHON_JULIAPKG_EXE="$BUNDLED_JULIA"
else
  # Strip juliaup from PATH to force juliacall to install Julia locally
  SAFE_PATH=""
  IFS=':' read -r -a PARTS <<< "${PATH:-}"
  for P in "${PARTS[@]}"; do
    if echo "$P" | tr '[:upper:]' '[:lower:]' | grep -q juliaup; then
      continue
    fi
    SAFE_PATH="${SAFE_PATH:+$SAFE_PATH:}$P"
  done
  export PATH="$SAFE_PATH"
fi

exec "$PYTHON_BIN" -u "$@"
'''
    runpython_path = project_dir / "env" / "scripts" / "runpython"
    runpython_path.write_text(runpython)
    runpython_path.chmod(0o755)
    
    if "julia" in languages:
        runjulia = '''#!/usr/bin/env bash
unset CDPATH
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUNDLED_JULIA="$REPO_ROOT/.julia/pyjuliapkg/install/bin/julia"

if [[ ! -x "$BUNDLED_JULIA" ]]; then
  echo "❌ Julia not found. Run: make environment"
  exit 1
fi

export JULIA_PROJECT="$REPO_ROOT/env"
export JULIA_DEPOT_PATH="$REPO_ROOT/.julia"

exec "$BUNDLED_JULIA" --project="$JULIA_PROJECT" "$@"
'''
        runjulia_path = project_dir / "env" / "scripts" / "runjulia"
        runjulia_path.write_text(runjulia)
        runjulia_path.chmod(0o755)
        
        # Generate install_julia.py script
        install_julia = '''#!/usr/bin/env python3
"""
Trigger Julia installation via juliacall.

This script imports juliacall, which automatically downloads and installs
Julia if not already present. This allows 'make environment' to set up
the complete environment in one command.
"""

import os
import shutil
import subprocess
import sys

print("=" * 80)
print("Installing Julia via juliacall...")
print("=" * 80)
print()

# Calculate environment directory FIRST (before importing juliacall)
env_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo_root = os.path.dirname(env_dir)
julia_depot = os.path.join(repo_root, ".julia")

# CRITICAL: Unset JULIA_PROJECT if set by runpython wrapper!
# The runpython wrapper sets JULIA_PROJECT=env/ but fresh projects don't
# have env/Manifest.toml yet. juliacall needs to use .julia/ project first,
# then we'll switch to env/ when running Pkg.instantiate() via subprocess.
if "JULIA_PROJECT" in os.environ:
    del os.environ["JULIA_PROJECT"]

# Configure Julia to use project-local depot (not ~/.julia)
os.environ["JULIA_DEPOT_PATH"] = julia_depot

# Tell juliacall to install Julia binary in .julia/ directory
os.environ["PYTHON_JULIAPKG_PROJECT"] = julia_depot

# Configure PythonCall to use system Python (not CondaPkg)
# This prevents CondaPkg from creating a redundant Python environment
os.environ["JULIA_CONDAPKG_BACKEND"] = "Null"
os.environ["JULIA_PYTHONCALL_EXE"] = sys.executable

# Prefer the bundled Julia in .julia/pyjuliapkg/install/bin/julia
bundled_julia = os.path.join(julia_depot, "pyjuliapkg", "install", "bin", "julia")
if os.path.isfile(bundled_julia):
    os.environ["PYTHON_JULIAPKG_EXE"] = bundled_julia
    print(f"Using bundled Julia at {bundled_julia}")
else:
    # Drop juliaup from PATH so juliacall installs into pyjuliapkg instead of
    # reusing a global juliaup copy.
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    filtered = [p for p in path_parts if "juliaup" not in p.lower()]
    if filtered != path_parts:
        os.environ["PATH"] = os.pathsep.join(filtered)
        print(
            "No bundled Julia found; removing juliaup from PATH to force local install"
        )

# Let juliacall download Julia to project-local location
# This ensures zero prerequisites - no need for system Julia or juliaup!
print("Allowing juliacall to manage Julia installation...")
print("This ensures the project is self-contained with zero prerequisites.")
print()

print(f"Julia depot: {julia_depot}")
print(f"Julia project: {env_dir}")
print(f"Python executable: {sys.executable}")
print("(CondaPkg disabled - Julia will use the conda environment Python)")
print()

want_cuda = os.environ.get("JULIA_ENABLE_CUDA") == "1"
if want_cuda:
    print("GPU support requested (JULIA_ENABLE_CUDA=1)")
    print("Note: CUDA.jl is optional and loaded at runtime when available.")
    print("It will be installed on-demand if you have a CUDA-capable GPU.")
else:
    print("GPU support not requested (JULIA_ENABLE_CUDA unset/0)")
    print("Julia will use CPU-only backends.")

# Import juliacall - this triggers Julia auto-install if needed
try:
    from juliacall import Main as jl

    print("✓ juliacall imported successfully")
    print()

    # Check Julia version
    julia_version = jl.seval("VERSION")
    print(f"✓ Julia version: {julia_version}")
    print()

    # Get Julia executable path from juliacall
    try:
        julia_cmd = jl.seval("Base.julia_cmd()")
        # Extract executable from Cmd object
        julia_exe = (
            julia_cmd.exec[0]
            if hasattr(julia_cmd, "exec")
            else str(julia_cmd).split()[0]
        )
    except Exception:
        # Method 2: Use Sys.BINDIR
        julia_exe = jl.seval('joinpath(Sys.BINDIR, "julia")')

    print(f"Julia executable: {julia_exe}")
    print()

    # Install packages using subprocess (more robust, won't segfault Python)
    print("Installing Julia packages from Project.toml...")
    print()

    # Build Julia command
    julia_env = os.environ.copy()
    julia_env["JULIA_CONDAPKG_BACKEND"] = "Null"
    julia_env["JULIA_PYTHONCALL_EXE"] = sys.executable
    load_path = [
        env_dir,
        os.environ.get("PYTHON_JULIAPKG_PROJECT", julia_depot),
        "@stdlib",
    ]
    julia_env["JULIA_LOAD_PATH"] = ":".join(load_path)

    # Build Julia installation code
    julia_code_parts = [
        """
        using Pkg
        println("Resolving dependencies...")
        Pkg.resolve()
        println()
        println("Installing packages...")
        Pkg.instantiate()
        """
    ]
    
    # Install CUDA.jl if requested (won't add to [deps], uses temporary environment)
    if want_cuda:
        julia_code_parts.append("""
        println()
        println("Installing CUDA.jl for GPU support...")
        # Install without adding to Project.toml [deps]
        Pkg.add("CUDA"; preserve=PRESERVE_ALL)
        """)
    
    julia_code_parts.append("""
        println()
        println("Precompiling packages...")
        Pkg.precompile()
        println()
        println("Verifying key packages...")
        using PythonCall
        println("  ✓ PythonCall")
    """)
    
    if want_cuda:
        julia_code_parts.append("""
        try
            using CUDA
            if CUDA.functional()
                println("  ✓ CUDA.jl (GPU functional)")
            else
                println("  ⚠ CUDA.jl installed but GPU not functional")
            end
        catch e
            println("  ⚠ CUDA.jl install failed: ", e)
        end
        """)
    
    julia_code = "".join(julia_code_parts)

    cmd = [
        julia_exe,
        f"--project={env_dir}",
        "-e",
        julia_code,
    ]

    def run_julia_install():
        return subprocess.run(cmd, env=julia_env).returncode == 0

    if not run_julia_install():
        print()
        print("✗ Julia package installation failed")
        print("Retrying after cleanup (compiled cache + Manifest.toml)...")
        compiled_dir = os.path.join(julia_depot, "compiled")
        manifest_path = os.path.join(env_dir, "Manifest.toml")

        if os.path.isdir(compiled_dir):
            try:
                shutil.rmtree(compiled_dir)
                print(f"  Removed compiled cache: {compiled_dir}")
            except Exception as cleanup_err:
                print(f"  ⚠ Failed to remove compiled cache: {cleanup_err}")

        if os.path.exists(manifest_path):
            try:
                os.remove(manifest_path)
                print(f"  Removed Manifest.toml: {manifest_path}")
            except Exception as cleanup_err:
                print(f"  ⚠ Failed to remove Manifest.toml: {cleanup_err}")

        print("Retrying Julia package installation...")
        if not run_julia_install():
            print()
            print("✗ Julia package installation failed after retry")
            sys.exit(1)

    # Clean up stray pyjuliapkg directory
    stray_pyjuliapkg = os.path.join(env_dir, "pyjuliapkg")
    if os.path.isdir(stray_pyjuliapkg):
        try:
            shutil.rmtree(stray_pyjuliapkg)
            print(f"Removed stray pyjuliapkg metadata dir: {stray_pyjuliapkg}")
        except Exception as cleanup_err:
            print(f"⚠ Failed to remove stray pyjuliapkg dir: {cleanup_err}")

    print()
    print("✓ Julia packages installed successfully")
    print()

    print("=" * 80)
    print("Julia environment setup complete!")
    print("=" * 80)
    sys.exit(0)

except Exception as e:
    print(f"✗ Error: {e}", file=sys.stderr)
    print()
    print("Julia installation failed. This may be due to:")
    print("  - Network connectivity issues")
    print("  - Insufficient disk space")
    print("  - Permission issues")
    print()
    print("You can retry by running:")
    print("  make environment")
    print()
    sys.exit(1)
'''
        install_julia_path = project_dir / "env" / "scripts" / "install_julia.py"
        install_julia_path.write_text(install_julia)
        install_julia_path.chmod(0o755)


def generate_readme(name: str, slug: str) -> str:
    """Generate README.md."""
    return f'''# {name}

Reproducible research project with provenance tracking.

## Quick Start

```bash
# 1. Setup environment (~10 minutes)
make environment

# 2. Run all analyses
make all

# 3. Publish results
make publish
```

## Project Structure

- `data/` - Input datasets
- `run_analysis.py` - Main analysis script
- `shared/config.py` - Study configurations
- `output/` - Build outputs (figures, tables, provenance)
- `paper/` - Published artifacts
- `env/` - Environment specifications

## Documentation

- `QUICKSTART.md` - 5-minute getting started guide
- `Makefile` - See `make help` for all commands

## Workflows

### Build All Analyses

```bash
make all
```

### Build Specific Analysis

```bash
make sample_analysis
```

### Verify Environment

```bash
make verify
```

### Publishing

```bash
make publish                              # Publish all
make publish PUBLISH_ANALYSES="sample_analysis"  # Publish specific
```

## Adding New Analyses

1. Add study configuration to `shared/config.py`:

```python
STUDIES = {{
    "my_analysis": {{
        "data": DATA_FILES["sample"],
        "xlabel": "X",
        "ylabel": "Y",
        # ... other parameters
    }},
}}
```

2. Add to Makefile `ANALYSES` variable:

```makefile
ANALYSES := sample_analysis my_analysis
```

3. Add analysis definition in Makefile:

```makefile
my_analysis.script  := run_analysis.py
my_analysis.runner  := $(PYTHON)
my_analysis.inputs  := $(DATA)
my_analysis.outputs := $(OUT_FIG_DIR)/my_analysis.pdf $(OUT_TBL_DIR)/my_analysis.tex $(OUT_PROV_DIR)/my_analysis.yml
my_analysis.args    := my_analysis
```

4. Build:

```bash
make my_analysis
```

## System Requirements

- Python 3.11
- GNU Make 4.3+
- Git

## License

See LICENSE file.
'''


def generate_quickstart(name: str) -> str:
    """Generate QUICKSTART.md."""
    return f'''# Quick Start Guide - {name}

## TL;DR - Copy-Paste Commands

```bash
# 1. Setup environment (~10 minutes)
make environment

# 2. Verify setup
make verify

# 3. Run all analyses
make all

# 4. Publish to paper/
make publish
```

## What Just Happened?

### `make environment`

Installed:
- Python 3.11 environment (`.env/` directory)
- Julia packages (`.julia/` directory, if enabled)
- Git submodules (repro-tools)

### `make verify`

Checked:
- Python environment
- Key packages (pandas, matplotlib, etc.)
- Data availability

### `make all`

Ran all analyses and generated:
- `output/figures/*.pdf` - Figures
- `output/tables/*.tex` - Tables
- `output/provenance/*.yml` - Build metadata

### `make publish`

Copied artifacts to `paper/` directory with provenance tracking.

## Next Steps

1. **Customize configurations**: Edit `shared/config.py`
2. **Add your data**: Place files in `data/`
3. **Modify analysis**: Edit `run_analysis.py`
4. **Build specific analysis**: `make sample_analysis`

## Common Commands

```bash
make help             # Show all commands
make clean            # Remove outputs
make list-analyses    # List available analyses
make test             # Run test suite
```

## Troubleshooting

**ImportError**: Run `make environment` first

**Build errors**: Check `output/logs/*.log`

**Need help?**: Run `make help`
'''


def generate_gitignore() -> str:
    """Generate .gitignore."""
    return '''# Build outputs
output/

# Environments
.env/
.julia/
.stata/

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Make
.make_build_marker
.publish_stamps/

# Logs
*.log
'''


def generate_sample_data(project_dir: Path) -> None:
    """Generate sample CSV data."""
    import csv
    
    data_file = project_dir / "data" / "sample.csv"
    with open(data_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['x', 'y'])
        for i in range(1, 11):
            writer.writerow([i, i * 2 + (i % 3)])


def main_cli():
    """CLI entry point for new-project command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create a new reproducible research project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  repro-tools new-project
  
  # Non-interactive
  repro-tools new-project \\
    --name "My Research Project" \\
    --slug my-project \\
    --languages python julia
        """
    )
    
    parser.add_argument("--name", help="Project display name")
    parser.add_argument("--slug", help="Project directory name (lowercase, hyphenated)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Parent directory (default: current directory)"
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        choices=["python", "julia", "stata"],
        default=["python"],
        help="Languages to include"
    )
    parser.add_argument(
        "--template",
        choices=["standard", "minimal"],
        default="standard",
        help="Template type"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for missing values"
    )
    
    args = parser.parse_args()
    
    # Interactive mode
    if args.interactive or not (args.name and args.slug):
        if not args.name:
            args.name = input("Project name: ")
        if not args.slug:
            default_slug = args.name.lower().replace(" ", "-")
            slug_input = input(f"Project slug [{default_slug}]: ")
            args.slug = slug_input or default_slug
    
    if not args.name or not args.slug:
        parser.error("--name and --slug are required (or use --interactive)")
    
    create_project(
        name=args.name,
        slug=args.slug,
        output_dir=args.output_dir,
        languages=args.languages,
        template=args.template,
        interactive=args.interactive,
    )


if __name__ == "__main__":
    main_cli()
