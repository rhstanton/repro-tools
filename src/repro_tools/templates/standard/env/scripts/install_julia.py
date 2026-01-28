#!/usr/bin/env python3
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
# Use abspath() to ensure all paths are absolute
env_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
repo_root = os.path.abspath(os.path.dirname(env_dir))
julia_depot = os.path.abspath(os.path.join(repo_root, ".julia"))

# CRITICAL: Unset JULIA_PROJECT and JULIA_LOAD_PATH set by runpython wrapper!
# The runpython wrapper sets these to use env/ but fresh projects don't have
# env/Manifest.toml yet. juliacall needs to use .julia/ project only during
# import, then we'll switch to env/ when running Pkg.instantiate() via subprocess.
if "JULIA_PROJECT" in os.environ:
    del os.environ["JULIA_PROJECT"]
if "JULIA_LOAD_PATH" in os.environ:
    del os.environ["JULIA_LOAD_PATH"]

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
    
    # CRITICAL: Set JULIA_DEPOT_PATH to use local .julia/ directory
    # Without this, Julia may use ~/.julia or other system depots
    julia_env["JULIA_DEPOT_PATH"] = julia_depot
    
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
