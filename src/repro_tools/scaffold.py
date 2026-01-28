"""Project scaffolding - generate new research projects from template."""

from pathlib import Path
import subprocess
import sys
import shutil
import csv
from typing import Optional


# Get path to templates directory
TEMPLATE_DIR = Path(__file__).parent / "templates" / "standard"


def copy_template(src: Path, dst: Path, substitutions: dict[str, str] = None) -> None:
    """Copy a template file, optionally performing string substitution.
    
    Args:
        src: Source template file path
        dst: Destination file path
        substitutions: Optional dict of {placeholder: replacement} for .template files
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    if src.name.endswith('.template'):
        # Read template, perform substitutions, write to destination (without .template suffix)
        content = src.read_text()
        if substitutions:
            for key, value in substitutions.items():
                content = content.replace(f"{{{key}}}", value)
        dst.write_text(content)
        # If source was executable, make destination executable
        if src.stat().st_mode & 0o111:
            dst.chmod(0o755)
    else:
        # Direct copy for non-template files
        shutil.copy2(src, dst)


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
    
    # Prepare substitutions for templates
    runners = ["PYTHON := env/scripts/runpython"]
    if "julia" in languages:
        runners.append("JULIA  := env/scripts/runjulia")
    if "stata" in languages:
        runners.append("STATA  := env/scripts/runstata")
    
    subs = {
        "name": name,
        "slug": slug,
        "runners": "\n".join(runners),
        "name_underline": "=" * len(name),
        "julia_deps": "\n    - juliacall>=0.9.14" if "julia" in languages else "",
    }
    
    # Create directory structure
    print("📁 Creating directory structure...")
    dirs = [
        project_dir,
        project_dir / "data",
        project_dir / "output" / "figures",
        project_dir / "output" / "tables",
        project_dir / "output" / "provenance",
        project_dir / "output" / "logs",
        project_dir / "paper" / "figures",
        project_dir / "paper" / "tables",
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
    
    # Copy core template files
    print("\n📄 Copying core files from templates...")
    copy_template(TEMPLATE_DIR / "Makefile.template", project_dir / "Makefile", subs)
    copy_template(TEMPLATE_DIR / "run_analysis.py.template", project_dir / "run_analysis.py", subs)
    copy_template(TEMPLATE_DIR / "README.md.template", project_dir / "README.md", subs)
    copy_template(TEMPLATE_DIR / "QUICKSTART.md.template", project_dir / "QUICKSTART.md", subs)
    copy_template(TEMPLATE_DIR / ".gitignore.template", project_dir / ".gitignore", subs)
    copy_template(TEMPLATE_DIR / ".gitattributes", project_dir / ".gitattributes", subs)
    print("  ✓ Core files created")
    
    # Copy shared/ files
    print("\n📄 Copying shared configuration...")
    copy_template(TEMPLATE_DIR / "shared" / "config.py.template", project_dir / "shared" / "config.py", subs)
    copy_template(TEMPLATE_DIR / "shared" / "__init__.py.template", project_dir / "shared" / "__init__.py", subs)
    (project_dir / "tests" / "__init__.py").write_text('"""Test suite."""\n')
    print("  ✓ shared/config.py created")
    
    # Copy environment files
    print("\n📄 Copying environment files...")
    copy_template(TEMPLATE_DIR / "env" / "python.yml.template", project_dir / "env" / "python.yml", subs)
    
    # Generate env/Makefile with conditional sections
    env_makefile_subs = subs.copy()
    if "julia" in languages:
        env_makefile_subs["julia_target"] = " julia-install-via-python"
        env_makefile_subs["julia_dep"] = "\n\t$(MAKE) julia-install-via-python"
        env_makefile_subs["julia_section"] = '''julia-install-via-python:
\t@echo ">> Installing Julia via juliacall..."
\t@cd $(REPO_ROOT) && $(REPO_ROOT)/env/scripts/runpython $(REPO_ROOT)/env/scripts/install_julia.py
'''
    else:
        env_makefile_subs["julia_target"] = ""
        env_makefile_subs["julia_dep"] = ""
        env_makefile_subs["julia_section"] = ""
    
    if "stata" in languages:
        env_makefile_subs["stata_target"] = " stata-env"
        env_makefile_subs["stata_dep"] = "\n\t$(MAKE) stata-env"
        env_makefile_subs["stata_section"] = '''# ---------- Stata ----------
STATA_LOCAL := ../.stata/ado/plus

# Read package list - only take first word of each line
STATA_PACKAGES := $(shell awk '{print $$1}' stata-packages.txt 2>/dev/null)

# Create a stamp file for each package
STATA_STAMPS := $(addprefix ../.stata/., $(addsuffix .stamp, $(STATA_PACKAGES)))

stata-env: $(STATA_STAMPS)
\t@echo "All Stata packages installed in $(STATA_LOCAL)"
\t@echo "Use env/scripts/runstata to run your .do files"

# Rule to install each package
../.stata/.%.stamp: stata-packages.txt | $(STATA_LOCAL)
\t@mkdir -p ../.stata
\t@echo "Installing Stata package: $*"
\t@VERSION=$$(awk '$$1 == "$*" {print $$2}' stata-packages.txt); \\
\techo 'sysdir set PLUS "$(CURDIR)/../.stata/ado/plus"' > /tmp/stata_install_$*.do; \\
\tif [ -n "$$VERSION" ]; then \\
\t\techo "  with version $$VERSION"; \\
\t\techo "cap noi ssc install $* $$VERSION, replace all" >> /tmp/stata_install_$*.do; \\
\telse \\
\t\techo "cap noi ssc install $*, replace all" >> /tmp/stata_install_$*.do; \\
\tfi; \\
\techo 'exit, clear STATA' >> /tmp/stata_install_$*.do; \\
\t(cd /tmp && stata-mp -b do /tmp/stata_install_$*.do > /dev/null 2>&1) || true; \\
\trm -f /tmp/stata_install_$*.do /tmp/stata_install_$*.do.log
\t@touch $@

# Create the local Stata directory structure
$(STATA_LOCAL):
\t@mkdir -p $(STATA_LOCAL)

stata-clean:
\trm -rf ../.stata
\trm -f /tmp/stata_install_*.do /tmp/stata_install_*.do.log

stata-check:
\t@echo "Installed Stata packages:"
\t@find ../.stata/ado/plus -name "*.ado" -exec basename {} \\; 2>/dev/null | sort | uniq || echo "No packages installed"
'''
    else:
        env_makefile_subs["stata_target"] = ""
        env_makefile_subs["stata_dep"] = ""
        env_makefile_subs["stata_section"] = ""
    
    copy_template(TEMPLATE_DIR / "env" / "Makefile.template", project_dir / "env" / "Makefile", env_makefile_subs)
    
    if "julia" in languages:
        copy_template(TEMPLATE_DIR / "env" / "Project.toml.template", project_dir / "env" / "Project.toml", subs)
    
    if "stata" in languages:
        copy_template(TEMPLATE_DIR / "env" / "stata-packages.txt.template", project_dir / "env" / "stata-packages.txt", subs)
    
    print("  ✓ Environment files created")
    
    # Copy environment scripts
    print("\n📄 Copying environment scripts...")
    scripts_dir = project_dir / "env" / "scripts"
    copy_template(TEMPLATE_DIR / "env" / "scripts" / "runpython", scripts_dir / "runpython", subs)
    
    if "julia" in languages:
        copy_template(TEMPLATE_DIR / "env" / "scripts" / "runjulia", scripts_dir / "runjulia", subs)
        copy_template(TEMPLATE_DIR / "env" / "scripts" / "install_julia.py", scripts_dir / "install_julia.py", subs)
    
    if "stata" in languages:
        copy_template(TEMPLATE_DIR / "env" / "scripts" / "runstata", scripts_dir / "runstata", subs)
        copy_template(TEMPLATE_DIR / "env" / "scripts" / "execute.ado", scripts_dir / "execute.ado", subs)
    
    print("  ✓ Environment scripts created")
    
    # Copy example files
    print("\n📄 Copying example files...")
    examples_dir = project_dir / "env" / "examples"
    copy_template(TEMPLATE_DIR / "env" / "examples" / "sample_python.py.template", examples_dir / "sample_python.py", subs)
    
    if "julia" in languages:
        copy_template(TEMPLATE_DIR / "env" / "examples" / "sample_julia.jl.template", examples_dir / "sample_julia.jl", subs)
        copy_template(TEMPLATE_DIR / "env" / "examples" / "sample_juliacall.py.template", examples_dir / "sample_juliacall.py", subs)
    
    if "stata" in languages:
        copy_template(TEMPLATE_DIR / "env" / "examples" / "sample_stata.do.template", examples_dir / "sample_stata.do", subs)
    
    print("  ✓ Example files created")
    
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


def generate_sample_data(project_dir: Path) -> None:
    """Generate sample CSV data with LF line endings (Unix-style)."""
    data_file = project_dir / "data" / "sample.csv"
    with open(data_file, 'w', newline='\n') as f:
        writer = csv.writer(f, lineterminator='\n')
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
