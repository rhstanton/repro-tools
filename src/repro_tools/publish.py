"""Publishing functionality for copying outputs to paper directory."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from repro_tools.core import git_state, now_utc_iso, sha256_file


def load_yml(path: Path) -> Dict[str, Any]:
    """Load YAML file."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yml(path: Path, obj: Dict[str, Any]) -> None:
    """Save object to YAML file (atomic write)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False)
    tmp.replace(path)


def copy_if_changed(src: Path, dst: Path) -> bool:
    """
    Copy src -> dst if dst missing or content differs.

    Returns:
        True if file was copied, False if already up-to-date
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and sha256_file(src) == sha256_file(dst):
        return False
    shutil.copy2(src, dst)
    return True


def check_git_policy(
    repo_root: Path,
    *,
    allow_dirty: bool = False,
    require_not_behind: bool = True,
) -> Dict[str, Any]:
    """
    Enforce git safety checks.

    Args:
        repo_root: Git repository root
        allow_dirty: Allow publishing from dirty working tree
        require_not_behind: Require branch not behind upstream

    Returns:
        Git state dictionary

    Raises:
        SystemExit: If policy checks fail
    """
    state = git_state(repo_root)
    if not state.get("is_git_repo", False):
        return state

    if state.get("dirty", False) and not allow_dirty:
        raise SystemExit(
            "Refusing to publish from a dirty working tree. "
            "Commit/stash first, or set allow_dirty=True."
        )

    if require_not_behind:
        behind = state.get("behind", None)
        if behind is not None and behind > 0:
            raise SystemExit(
                f"Refusing to publish: branch is behind upstream by {behind} commit(s). "
                f"Pull/rebase first, or set require_not_behind=False."
            )

    return state


def check_artifacts_from_clean_tree(
    artifact_names: List[str],
    prov_dir: Path,
    *,
    allow_dirty: bool = False,
) -> None:
    """
    Verify artifacts were built from a clean working tree.

    Args:
        artifact_names: List of artifact names to check
        prov_dir: Directory containing provenance files
        allow_dirty: Allow artifacts built from dirty tree

    Raises:
        SystemExit: If artifacts were built dirty and allow_dirty=False
    """
    dirty_artifacts = []
    for name in artifact_names:
        meta_path = prov_dir / f"{name}.yml"
        if meta_path.exists():
            meta = load_yml(meta_path)
            git_info = meta.get("git", {})
            if git_info.get("dirty", False):
                dirty_artifacts.append(name)

    if dirty_artifacts and not allow_dirty:
        msg = "Refusing to publish: artifacts were built from a dirty working tree:\n"
        for name in dirty_artifacts:
            msg += f"  {name}\n"
        msg += (
            "\nRebuild from clean tree: git commit/stash, then make clean && make all\n"
        )
        msg += "Or set allow_dirty=True to allow."
        raise SystemExit(msg)


def check_artifacts_from_current_head(
    artifact_names: List[str],
    prov_dir: Path,
    current_commit: str,
) -> None:
    """
    Verify all artifacts were built from current HEAD commit.

    Args:
        artifact_names: List of artifact names to check
        prov_dir: Directory containing provenance files
        current_commit: Current HEAD commit SHA

    Raises:
        SystemExit: If artifacts not from current HEAD
    """
    stale = []
    for name in artifact_names:
        meta_path = prov_dir / f"{name}.yml"
        if meta_path.exists():
            meta = load_yml(meta_path)
            git_info = meta.get("git", {})
            artifact_commit = git_info.get("commit", "")
            if artifact_commit and artifact_commit != current_commit:
                stale.append((name, artifact_commit[:7], current_commit[:7]))

    if stale:
        msg = "Refusing to publish: artifacts not built from current HEAD:\n"
        for name, old, new in stale:
            msg += f"  {name}: built from {old}, but HEAD is {new}\n"
        msg += "\nRun: make clean && make all"
        raise SystemExit(msg)


def publish_analyses(
    *,
    project_root: Path,
    paper_root: Path,
    analysis_names: List[str],
    kinds: Optional[List[str]] = None,
    allow_dirty: bool = False,
    require_not_behind: bool = True,
    require_current_head: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Publish complete analyses (all outputs per analysis).

    Args:
        project_root: Root of analysis repository
        paper_root: Root of paper repository
        analysis_names: List of analyses to publish
        kinds: Output kinds to publish (default: ["figures", "tables"])
        allow_dirty: Allow publishing from dirty tree
        require_not_behind: Require branch not behind upstream
        require_current_head: Require artifacts from current HEAD
        verbose: Print status messages

    Returns:
        Updated provenance dictionary
    """
    if kinds is None:
        kinds = ["figures", "tables"]

    # Check git policy
    gitinfo = check_git_policy(
        project_root,
        allow_dirty=allow_dirty,
        require_not_behind=require_not_behind,
    )

    # Check artifacts
    out_prov_dir = project_root / "output" / "provenance"

    check_artifacts_from_clean_tree(
        analysis_names, out_prov_dir, allow_dirty=allow_dirty
    )

    if require_current_head and gitinfo.get("is_git_repo"):
        current_commit = gitinfo.get("commit", "")
        if current_commit:
            check_artifacts_from_current_head(
                analysis_names, out_prov_dir, current_commit
            )

    # Load or initialize paper provenance
    prov_path = paper_root / "provenance.yml"
    prov = load_yml(prov_path) if prov_path.exists() else {}
    prov.setdefault("paper_provenance_version", 1)
    prov.setdefault("analysis_git", gitinfo)
    prov.setdefault("artifacts", {})

    # Analysis-level publishing: clear file-level tracking
    if "files" in prov:
        del prov["files"]

    # Publish each analysis
    for name in analysis_names:
        meta_path = out_prov_dir / f"{name}.yml"
        if not meta_path.exists():
            raise SystemExit(
                f"Missing build record {meta_path}. Build first: make {name}"
            )
        meta = load_yml(meta_path)

        prov["artifacts"].setdefault(name, {})

        for kind in kinds:
            ext = "pdf" if kind == "figures" else "tex"
            src = project_root / "output" / kind / f"{name}.{ext}"
            dst = paper_root / kind / f"{name}.{ext}"

            if not src.exists():
                if verbose:
                    print(f"  Warning: {src} not found, skipping")
                continue

            copied = copy_if_changed(src, dst)

            if verbose:
                status = "Published" if copied else "Up-to-date"
                rel_path = dst.relative_to(paper_root)
                print(f"  {name:15s}  {status:11s}  {rel_path}")

            prov["artifacts"][name][kind] = {
                "published_at_utc": now_utc_iso(),
                "copied": copied,
                "src": str(src.resolve()),
                "dst": str(dst.resolve()),
                "dst_sha256": sha256_file(dst),
                "build_record": meta,
            }

    prov["last_updated_utc"] = now_utc_iso()
    save_yml(prov_path, prov)

    return prov


def publish_files(
    *,
    project_root: Path,
    paper_root: Path,
    file_paths: List[Path],
    allow_dirty: bool = False,
    require_not_behind: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Publish specific output files.

    Args:
        project_root: Root of analysis repository
        paper_root: Root of paper repository
        file_paths: List of output files to publish
        allow_dirty: Allow publishing from dirty tree
        require_not_behind: Require branch not behind upstream
        verbose: Print status messages

    Returns:
        Updated provenance dictionary
    """
    # Check git policy
    gitinfo = check_git_policy(
        project_root,
        allow_dirty=allow_dirty,
        require_not_behind=require_not_behind,
    )

    # Load or initialize paper provenance
    prov_path = paper_root / "provenance.yml"
    prov = load_yml(prov_path) if prov_path.exists() else {}
    prov.setdefault("paper_provenance_version", 1)
    prov.setdefault("analysis_git", gitinfo)

    # File-level publishing: clear analysis-level tracking
    prov["files"] = {}
    if "artifacts" in prov:
        del prov["artifacts"]

    output_dir = project_root / "output"

    for src in file_paths:
        if not src.is_absolute():
            src = project_root / src

        if not src.exists():
            raise SystemExit(f"Source file not found: {src}")

        # Determine destination
        try:
            rel_path = src.relative_to(output_dir)
        except ValueError as e:
            raise SystemExit(
                f"File {src} is not in output/ directory. "
                "Only output files can be published."
            ) from e

        dst = paper_root / rel_path

        # Try to find associated build record
        analysis_name = _infer_analysis_name(src, project_root)
        build_record = None
        if analysis_name:
            prov_file = project_root / "output" / "provenance" / f"{analysis_name}.yml"
            if prov_file.exists():
                build_record = load_yml(prov_file)

        # Copy file
        copied = copy_if_changed(src, dst)

        if verbose:
            status = "Published" if copied else "Up-to-date"
            rel_dst = dst.relative_to(paper_root)
            print(f"  {rel_dst!s:40s}  {status}")

        # Record in provenance
        file_key = str(rel_path)
        prov["files"][file_key] = {
            "published_at_utc": now_utc_iso(),
            "copied": copied,
            "src": str(src.resolve()),
            "dst": str(dst.resolve()),
            "dst_sha256": sha256_file(dst),
            "analysis_name": analysis_name,
            "build_record": build_record,
        }

    prov["last_updated_utc"] = now_utc_iso()
    save_yml(prov_path, prov)

    return prov


def _infer_analysis_name(output_path: Path, project_root: Path) -> str | None:
    """
    Try to infer analysis name from output path by checking provenance files.
    Returns None if cannot be determined.
    """
    prov_dir = project_root / "output" / "provenance"
    if not prov_dir.exists():
        return None

    # Look for provenance files that list this output
    for prov_file in prov_dir.glob("*.yml"):
        try:
            meta = load_yml(prov_file)
            outputs = meta.get("outputs", [])
            for out_info in outputs:
                if Path(out_info.get("path", "")).resolve() == output_path.resolve():
                    return prov_file.stem  # The analysis name
        except Exception:
            continue

    return None
