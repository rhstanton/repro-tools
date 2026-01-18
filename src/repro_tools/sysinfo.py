#!/usr/bin/env python3
"""
log_system_info.py

Captures computational environment details for reproducibility.
Creates system_info.yml with OS, Python, Julia, package versions, etc.
"""
import argparse
import platform
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("Warning: PyYAML not available, outputting raw text instead", file=sys.stderr)
    yaml = None


def get_git_info(repo_path):
    """Get git repository information."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        
        is_dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip())
        
        return {
            "commit": commit,
            "branch": branch,
            "dirty": is_dirty,
        }
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"error": "Not a git repository or git not available"}


def get_python_packages():
    """Get installed Python packages."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            packages = {}
            for line in result.stdout.splitlines():
                if "==" in line:
                    name, version = line.split("==", 1)
                    packages[name] = version
            return packages
        else:
            return {"error": "Could not list packages"}
    except Exception as e:
        return {"error": str(e)}


def get_julia_info(repo_path):
    """Get Julia version and package information."""
    julia_exe = repo_path / ".julia" / "pyjuliapkg" / "install" / "bin" / "julia"
    
    if not julia_exe.exists():
        return {"error": "Julia not installed"}
    
    try:
        # Get Julia version
        version_result = subprocess.run(
            [str(julia_exe), "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        version = version_result.stdout.strip() if version_result.returncode == 0 else "unknown"
        
        # Get package status
        env_project = repo_path / "env" / "Project.toml"
        if env_project.exists():
            pkg_cmd = f'using Pkg; Pkg.activate("{env_project}"); Pkg.status()'
            pkg_result = subprocess.run(
                [str(julia_exe), "--project=" + str(env_project.parent), "-e", pkg_cmd],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            packages = pkg_result.stdout if pkg_result.returncode == 0 else "Could not get package list"
        else:
            packages = "No Project.toml found"
        
        return {
            "version": version,
            "packages": packages,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Julia command timed out"}
    except Exception as e:
        return {"error": str(e)}


def get_system_info(repo_path):
    """Gather all system information."""
    info = {
        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        "system": {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_executable": sys.executable,
        },
        "git": get_git_info(repo_path),
        "python_packages": get_python_packages(),
        "julia": get_julia_info(repo_path),
    }
    
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/system_info.yml"),
        help="Output file path (default: output/system_info.yml)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory (default: current directory)",
    )
    args = parser.parse_args()
    
    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Gather information
    print(f"Gathering system information...")
    info = get_system_info(args.repo_root.resolve())
    
    # Write to file
    print(f"Writing to {args.output}...")
    if yaml:
        with open(args.output, "w") as f:
            yaml.dump(info, f, default_flow_style=False, sort_keys=False)
        print(f"✅ System information saved to {args.output}")
    else:
        # Fallback if yaml not available
        with open(args.output.with_suffix(".txt"), "w") as f:
            for key, value in info.items():
                f.write(f"{key}: {value}\n")
        print(f"✅ System information saved to {args.output.with_suffix('.txt')} (PyYAML not available)")


if __name__ == "__main__":
    main()
