#!/usr/bin/env python
"""
bump_version.py — set this project's version everywhere it appears, at once.

Works for this template AND for any project derived from it: the current
version and the package name are read from pyproject.toml (the source of
truth), so the tool adapts to your renamed project. Every other file is updated
only if its pattern is actually present, and skipped (not errored) otherwise —
so a derived project that has edited or removed the template's docs still bumps
cleanly.

Updated when present:
  • pyproject.toml   [project] version                 (required)
  • uv.lock          this project's package entry        (matched by name)
  • _version.py      __version__
  • CITATION.cff     version:  +  date-released: <today>
  • README.md        **Current version: X**
  • QUICKSTART.md    template vX
  • CHANGELOG.md     ## [Unreleased]  ->  ## [X] - <today>  (+ fresh Unreleased)

Usage:
    python scripts/bump_version.py <version>            # dry run: show the plan
    python scripts/bump_version.py <version> --apply    # write the changes
    python scripts/bump_version.py <version> --apply --date 2026-05-27

Or via Make:
    make bump-version VERSION=2.1.0

Stdlib-only, so it runs from anywhere (even before `make environment`). It does
NOT git-commit, tag, or publish — that stays a deliberate, reviewable step.

It DOES refuse a version that is not strictly ahead of every existing release
tag, and that check exists because of a real failure. repro-tools was tagged
v0.3.0, v0.3.1, v0.3.2 and v0.3.3 on 2026-01-28 without any of them updating
pyproject.toml, which sat at 0.2.0 throughout — so four releases reported
themselves as 0.2.0, the CHANGELOG skipped them, and the only record anywhere
with the right number was a hand-copied constant in a different repository.

`git tag` succeeds whether or not anything was bumped, so nothing surfaced it.
Refusing here is the missing half of that loop; `--force` overrides for the
genuine case of re-cutting a tag that was never pushed.

This script lives in repro-tools so every consuming project has it. Projects
that had no bump helper are exactly the ones that drifted.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("REPRO_BUMP_ROOT", Path.cwd()))
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def release_tags(root: Path) -> list:
    """Every vX.Y.Z tag in this repository, newest-sorting last."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "tag"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    tags = []
    for t in out.stdout.split():
        m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", t)
        if m:
            tags.append(tuple(int(x) for x in m.groups()))
    return sorted(tags)


def check_ahead_of_tags(root: Path, new: str, force: bool) -> int:
    """Refuse a version that collides with or precedes an existing tag."""
    tags = release_tags(root)
    if not tags:
        return 0
    highest = max(tags)
    want = tuple(int(x) for x in new.split("."))
    if want > highest:
        return 0
    latest = "v" + ".".join(str(x) for x in highest)
    print(
        f"ERROR: {new} is not ahead of the highest release tag {latest}.",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    print(
        "  Tagging succeeds whether or not the declared version was bumped, so a",
        file=sys.stderr,
    )
    print(
        "  repository can accumulate tags its pyproject.toml never knew about.",
        file=sys.stderr,
    )
    print(
        "  That is what happened to repro-tools between v0.3.0 and v0.3.3.",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    nxt = (highest[0], highest[1] + 1, 0)
    print(f"  Next unused version: {'.'.join(str(x) for x in nxt)}", file=sys.stderr)
    print("  Use --force only to re-cut a tag that was never pushed.", file=sys.stderr)
    return 0 if force else 1


def project_field(pyproject: str, key: str) -> str | None:
    """Read `key = "..."` from the [project] table of pyproject.toml."""
    table = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[)", pyproject)
    body = table.group(1) if table else pyproject
    match = re.search(rf'(?m)^{key}\s*=\s*"([^"]+)"', body)
    return match.group(1) if match else None


def normalize(name: str) -> str:
    """PEP 503 package-name normalization (matches how uv.lock spells it)."""
    return re.sub(r"[-_.]+", "-", name).lower()


class Edit:
    """One find/replace against a file. Optional files are skipped silently."""

    def __init__(self, rel, find, replace, *, required=False, regex=False):
        self.rel = rel
        self.find = find
        self.replace = replace
        self.required = required
        self.regex = regex

    def run(self, write: bool) -> int:
        path = REPO_ROOT / self.rel
        if not path.exists():
            return 0
        text = path.read_text()
        if self.regex:
            new_text, count = re.subn(self.find, self.replace, text, count=1)
        else:
            count = 1 if self.find in text else 0
            new_text = text.replace(self.find, self.replace, 1)
        if count and write:
            path.write_text(new_text)
        return count


def plan(current: str, new: str, name: str, date: str) -> list[Edit]:
    norm = normalize(name)
    return [
        Edit(
            "pyproject.toml",
            f'version = "{current}"',
            f'version = "{new}"',
            required=True,
        ),
        Edit(
            "uv.lock",
            f'name = "{norm}"\nversion = "{current}"',
            f'name = "{norm}"\nversion = "{new}"',
        ),
        Edit("_version.py", f'__version__ = "{current}"', f'__version__ = "{new}"'),
        Edit("CITATION.cff", f"version: {current}", f"version: {new}"),
        Edit(
            "CITATION.cff",
            r"(?m)^date-released: .*",
            f"date-released: {date}",
            regex=True,
        ),
        Edit(
            "README.md",
            f"**Current version: {current}**",
            f"**Current version: {new}**",
        ),
        Edit("QUICKSTART.md", f"template v{current}", f"template v{new}"),
        Edit(
            "CHANGELOG.md",
            "## [Unreleased]\n",
            f"## [Unreleased]\n\n## [{new}] - {date}\n",
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Bump this project's version everywhere.")
    ap.add_argument("version", help="new version, e.g. 2.1.0")
    ap.add_argument(
        "--apply", action="store_true", help="write changes (default: dry run)"
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="bump even if the version is not ahead of every release tag",
    )
    ap.add_argument(
        "--date",
        default=datetime.date.today().isoformat(),
        help="release date for CITATION.cff / CHANGELOG (default: today)",
    )
    args = ap.parse_args()

    new = args.version
    if not SEMVER_RE.match(new):
        sys.exit(f"error: '{new}' is not a valid X.Y.Z version")

    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    current = project_field(pyproject, "version")
    name = project_field(pyproject, "name")
    if not current or not name:
        sys.exit("error: could not read name/version from pyproject.toml [project]")
    if new == current:
        sys.exit(f"error: version is already {current}")

    # Before touching anything: the declared version and the tags must agree.
    if check_ahead_of_tags(REPO_ROOT, new, args.force):
        return 1

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"{name}: {current} -> {new}  (date {args.date})  [{mode}]\n")

    failed_required = False
    for edit in plan(current, new, name, args.date):
        if edit.run(args.apply):
            print(f"  ✓ {edit.rel}")
        elif edit.required:
            print(f"  ✗ {edit.rel}: REQUIRED pattern not found")
            failed_required = True
        else:
            print(f"  · {edit.rel}: no match — skipped")

    print()
    if not args.apply:
        print(
            "Dry run — nothing written. "
            "Re-run with --apply (or: make bump-version VERSION=...)."
        )
    else:
        print(f"Done. Review `git diff`, then commit and tag v{new} when ready.")
    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
