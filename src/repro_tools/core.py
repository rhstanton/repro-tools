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

# Cap on how many untracked paths a single record will list. The count is
# always exact; only the listing is bounded.
UNTRACKED_LIMIT = 50

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
        out = subprocess.check_output(
            ["git", *args], cwd=str(cwd), stderr=subprocess.DEVNULL
        )
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
        dirty: bool (TRACKED content differs from HEAD; untracked files
               do not count -- see untracked_count)
        untracked_count: int (files git neither tracks nor ignores)
        untracked: list[str] (up to UNTRACKED_LIMIT of them, sorted)
        untracked_truncated: bool (whether that list was cut short)
        upstream: str or None
        ahead: int or None (commits ahead of upstream)
        behind: int or None (commits behind upstream)
    """
    commit = _run_git(["rev-parse", "HEAD"], cwd=repo_root)
    if commit is None:
        return {"is_git_repo": False}

    dirty = False
    # Check for uncommitted changes.
    #
    # `dirty` deliberately means TRACKED content differing from HEAD, and
    # nothing else. It is what publishing gates on, and a gate that fires
    # constantly gets switched off -- which is strictly worse than a narrow one,
    # because ALLOW_DIRTY=1 in a CI config disables the check permanently and
    # silently.
    try:
        subprocess.check_call(["git", "diff", "--quiet"], cwd=str(repo_root))
        subprocess.check_call(
            ["git", "diff", "--cached", "--quiet"], cwd=str(repo_root)
        )
    except Exception:
        dirty = True

    # Untracked files are recorded SEPARATELY rather than folded into `dirty`.
    #
    # The record and the policy are different things, and conflating them into
    # one boolean is why this was hard to decide. An untracked script is a
    # perfectly good candidate for whatever produced the artifact being
    # described, so provenance that says "clean" about such a tree is being
    # generous about something it has not looked at. This is not hypothetical:
    # the numbers in a submitted paper were once produced by code that predated
    # its repository's first commit -- untracked work, published results, and a
    # provenance record would have called that tree clean.
    #
    # So: report it, do not gate on it. A consumer that wants the strict meaning
    # can read `untracked_count`; publishing keeps its current sensitivity.
    #
    # git status --porcelain already excludes gitignored files, so a project
    # that ignores its outputs sees an empty list here. The list is capped
    # because "a project that ignores its outputs" is exactly the kind of
    # assumption that should not be able to produce a 10,000-entry record.
    untracked: List[str] = []
    untracked_count = 0
    untracked_truncated = False
    out = _run_git(["ls-files", "--others", "--exclude-standard"], cwd=repo_root)
    if out:
        entries = [line for line in out.splitlines() if line.strip()]
        untracked_count = len(entries)
        untracked = sorted(entries)[:UNTRACKED_LIMIT]
        untracked_truncated = untracked_count > UNTRACKED_LIMIT

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    upstream = _run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=repo_root
    )

    ahead = behind = None
    if upstream:
        lr = _run_git(
            ["rev-list", "--left-right", "--count", f"HEAD...{upstream}"], cwd=repo_root
        )
        if lr and "\t" in lr:
            left, right = lr.split("\t")
            # left = commits only in HEAD (ahead), right = commits only in upstream (behind)
            ahead, behind = int(left), int(right)

    return {
        "is_git_repo": True,
        "commit": commit,
        "branch": branch,
        "dirty": dirty,
        "untracked_count": untracked_count,
        "untracked": untracked,
        "untracked_truncated": untracked_truncated,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
    }


def now_utc_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _file_record(path: Path, repo_root: Path) -> Dict[str, Any]:
    """Describe one file for a provenance record.

    PATHS ARE RELATIVE TO THE REPOSITORY ROOT, which is recorded once per record
    as `repo_root`. They used to be absolute, and that had two costs:

      * records could not be compared across machines -- every path differed, so
        diffing two byte-identical builds was pure noise;
      * `paper/provenance.yml` IS committed (it lives in the paper repository,
        which is typically synced to Overleaf and can accompany a submission),
        so absolute paths published the author's home directory.

    A file outside the repository -- data on another volume, say -- cannot be
    made relative and is recorded absolute. That is information, not a failure:
    it says the build depended on something outside the repository, which is
    exactly the kind of thing a replicator needs to know.

    `mtime` is deliberately NOT recorded. It changes on every checkout and every
    file copy, so it made two identical builds produce different records while
    saying nothing about content that sha256 does not say better. Records that
    differ for reasons unrelated to their subject do not get compared, and a
    record nobody compares is decoration.
    """
    resolved = path.resolve()
    try:
        recorded = str(resolved.relative_to(repo_root))
    except ValueError:
        recorded = str(resolved)
    return {
        "path": recorded,
        "sha256": sha256_file(resolved),
        "bytes": resolved.stat().st_size,
    }


def resolve_recorded_path(entry: Dict[str, Any], record: Dict[str, Any]) -> Path:
    """Turn a recorded path back into a usable one.

    Handles both conventions, because records written before 2026-08-18 store
    absolute paths and have no `repo_root`. An absolute recorded path is used as
    written; a relative one is joined to the record's `repo_root`, falling back
    to the current directory when a very old record lacks it.
    """
    recorded = Path(entry["path"])
    if recorded.is_absolute():
        return recorded
    root = record.get("repo_root")
    return (Path(root) if root else Path.cwd()) / recorded


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
    root = Path(repo_root).resolve()

    record: Dict[str, Any] = {
        "artifact": artifact_name,
        "built_at_utc": now_utc_iso(),
        "command": command,
        "repo_root": str(root),
        "path_convention": "relative-to-repo-root-where-possible",
        "git": git_state(repo_root),
        "inputs": [_file_record(p, root) for p in inputs],
        "outputs": [_file_record(p, root) for p in outputs],
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
    import sys

    # Look at the caller's frame ONLY for the things we were not told.
    #
    # This used to run unconditionally and index f_globals["__file__"] directly,
    # which raised KeyError in any caller without one -- `python -c`, a REPL, an
    # Emacs inferior shell, a Jupyter cell. Those are exactly the interactive
    # sessions a research project runs analyses from, and the failure landed on
    # the provenance call at the END of a long run, after the expensive work.
    #
    # Provenance is evidence ABOUT a run; it must never be the thing that
    # destroys one. So: only introspect when a value is actually missing, and
    # fall back to the working directory rather than raising when there is no
    # caller file to read.
    caller_file = None
    if artifact_name is None or repo_root is None:
        frame = inspect.currentframe()
        caller_globals = frame.f_back.f_globals if frame and frame.f_back else {}
        caller_path = caller_globals.get("__file__")
        if caller_path:
            caller_file = Path(caller_path).resolve()

    # Auto-detect artifact name if not provided
    if artifact_name is None:
        artifact_name = caller_file.stem if caller_file else out_meta.stem
        if artifact_name.startswith("build_"):
            artifact_name = artifact_name[6:]  # Remove "build_" prefix

    # Auto-detect repo root if not provided
    if repo_root is None:
        repo_root = caller_file.parent if caller_file else Path.cwd()

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
                f"Warning: Unknown analysis '{artifact_name}', skipping provenance",
                file=sys.stderr,
            )
            print(
                f"  Available analyses: {', '.join(config.ANALYSES.keys())}",
                file=sys.stderr,
            )
            return

        analysis_cfg = config.ANALYSES[artifact_name]

        write_build_record(
            out_meta=analysis_cfg["outputs"]["provenance"],
            artifact_name=artifact_name,
            command=sys.argv
            if sys.argv[0].endswith(".py")
            else ["make", artifact_name],
            repo_root=config.REPO_ROOT,
            inputs=analysis_cfg["inputs"],
            outputs=[
                analysis_cfg["outputs"]["figure"],
                analysis_cfg["outputs"]["table"],
            ],
        )

        _provenance_recorded = True

    except ImportError:
        print(
            "Warning: enable_auto_provenance requires config.py with ANALYSES dictionary",
            file=sys.stderr,
        )
        print(
            "  For standalone scripts, use auto_build_record() instead", file=sys.stderr
        )
        print("  See: repro-tools documentation", file=sys.stderr)
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
