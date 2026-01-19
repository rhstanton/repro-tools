"""Core provenance tracking functionality."""

from __future__ import annotations

import atexit
import hashlib
import inspect
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# Global flag to track if provenance should be recorded
_should_record_provenance = True
_provenance_recorded = False


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA256 checksum of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _run_git(args: List[str], cwd: Path) -> Optional[str]:
    """Run git command and return output, or None if failed."""
    try:
        out = subprocess.check_output(["git", *args], cwd=str(cwd), stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return None


def git_state(repo_root: Path) -> Dict[str, Any]:
    """
    Capture current git repository state.

    Returns dictionary with:
        is_git_repo: bool
        commit: str (full SHA) or None
        branch: str or None
        dirty: bool (uncommitted changes)
        upstream: str or None
        ahead: int or None (commits ahead of upstream)
        behind: int or None (commits behind upstream)
    """
    commit = _run_git(["rev-parse", "HEAD"], cwd=repo_root)
    if commit is None:
        return {"is_git_repo": False}

    dirty = False
    # Check for uncommitted changes
    try:
        subprocess.check_call(["git", "diff", "--quiet"], cwd=str(repo_root))
        subprocess.check_call(["git", "diff", "--cached", "--quiet"], cwd=str(repo_root))
    except Exception:
        dirty = True

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    upstream = _run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=repo_root
    )

    ahead = behind = None
    if upstream:
        lr = _run_git(["rev-list", "--left-right", "--count", f"HEAD...{upstream}"], cwd=repo_root)
        if lr and "\t" in lr:
            left, right = lr.split("\t")
            # left = commits only in HEAD (ahead), right = commits only in upstream (behind)
            ahead, behind = int(left), int(right)

    return {
        "is_git_repo": True,
        "commit": commit,
        "branch": branch,
        "dirty": dirty,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
    }


def now_utc_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_build_record(
    *,
    out_meta: Path,
    artifact_name: str,
    command: List[str],
    repo_root: Path,
    inputs: List[Path],
    outputs: List[Path],
) -> None:
    """
    Write a per-artifact YAML build record.

    Records:
    - What was built (artifact_name)
    - When it was built (UTC timestamp)
    - How it was built (command)
    - Git state at build time
    - Input files with SHA256 checksums
    - Output files with SHA256 checksums

    Args:
        out_meta: Path to write provenance YAML
        artifact_name: Name of the artifact being built
        command: Command that produced the outputs (e.g., sys.argv)
        repo_root: Git repository root
        inputs: List of input file paths
        outputs: List of output file paths
    """
    out_meta.parent.mkdir(parents=True, exist_ok=True)

    input_records: List[Dict[str, Any]] = []
    for p in inputs:
        p = p.resolve()
        input_records.append(
            {
                "path": str(p),
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
                "mtime": p.stat().st_mtime,
            }
        )

    output_records: List[Dict[str, Any]] = []
    for p in outputs:
        p = p.resolve()
        output_records.append(
            {
                "path": str(p),
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
                "mtime": p.stat().st_mtime,
            }
        )

    record: Dict[str, Any] = {
        "artifact": artifact_name,
        "built_at_utc": now_utc_iso(),
        "command": command,
        "git": git_state(repo_root),
        "inputs": input_records,
        "outputs": output_records,
    }

    tmp = out_meta.with_suffix(out_meta.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(record, f, sort_keys=False)
    tmp.replace(out_meta)


def auto_build_record(
    out_meta: Path,
    inputs: List[Path],
    outputs: List[Path],
    *,
    artifact_name: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> None:
    """
    Simplified wrapper that auto-detects parameters.

    Auto-detects:
    - artifact_name from calling script filename (removes "build_" prefix)
    - repo_root from calling script's parent directory
    - command from sys.argv

    Args:
        out_meta: Path to write provenance YAML
        inputs: List of input file paths
        outputs: List of output file paths
        artifact_name: Override auto-detected name (optional)
        repo_root: Override auto-detected repo root (optional)
    """
    import inspect
    import sys

    # Get the calling script's file path
    frame = inspect.currentframe()
    if frame is None or frame.f_back is None:
        raise RuntimeError("Cannot determine calling script")

    caller_file = Path(frame.f_back.f_globals["__file__"]).resolve()

    # Auto-detect artifact name if not provided
    if artifact_name is None:
        artifact_name = caller_file.stem
        if artifact_name.startswith("build_"):
            artifact_name = artifact_name[6:]  # Remove "build_" prefix

    # Auto-detect repo root if not provided
    if repo_root is None:
        repo_root = caller_file.parent

    # Use sys.argv for command (exact command that was run)
    command = sys.argv.copy()

    # Call the full function
    write_build_record(
        out_meta=out_meta,
        artifact_name=artifact_name,
        command=command,
        repo_root=repo_root,
        inputs=inputs,
        outputs=outputs,
    )


def auto_provenance_from_config(artifact_name: str) -> None:
    """
    Automatically record provenance using config.py definitions.

    This can be called from build scripts OR from Makefile - it's safe either way.
    If called multiple times, only the first call records provenance.

    Usage in build script:
        from repro_tools import auto_provenance_from_config
        # ... do analysis ...
        auto_provenance_from_config("price_base")  # or auto-detect from __file__

    Or call from atexit handler to run automatically at script exit.
    """
    global _provenance_recorded

    if _provenance_recorded or not _should_record_provenance:
        return

    try:
        # Import config here to avoid circular imports
        import config

        if artifact_name not in config.ANALYSES:
            print(
                f"Warning: Unknown analysis '{artifact_name}', skipping provenance", file=sys.stderr
            )
            print(f"  Available analyses: {', '.join(config.ANALYSES.keys())}", file=sys.stderr)
            return

        analysis_cfg = config.ANALYSES[artifact_name]

        write_build_record(
            out_meta=analysis_cfg["outputs"]["provenance"],
            artifact_name=artifact_name,
            command=sys.argv if sys.argv[0].endswith(".py") else ["make", artifact_name],
            repo_root=config.REPO_ROOT,
            inputs=analysis_cfg["inputs"],
            outputs=[analysis_cfg["outputs"]["figure"], analysis_cfg["outputs"]["table"]],
        )

        _provenance_recorded = True

    except ImportError as e:
        print(
            f"Warning: enable_auto_provenance requires config.py with ANALYSES dictionary",
            file=sys.stderr,
        )
        print(f"  For standalone scripts, use auto_build_record() instead", file=sys.stderr)
        print(f"  See: repro-tools documentation", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Failed to record provenance: {e}", file=sys.stderr)


def enable_auto_provenance(script_file: str) -> None:
    """
    Enable automatic provenance recording at script exit.

    Call this at the top of your build script:
        from repro_tools import enable_auto_provenance
        enable_auto_provenance(__file__)

    Provenance will be recorded automatically when the script exits successfully.
    """
    script_path = Path(script_file)
    artifact_name = script_path.stem
    if artifact_name.startswith("build_"):
        artifact_name = artifact_name[6:]

    # Register atexit handler to record provenance when script completes
    atexit.register(auto_provenance_from_config, artifact_name)
