"""Show which template changes have not been applied to this project.

A project generated from project_template has an unrelated git history -- GitHub's
"Use this template" squashes to a fresh initial commit -- so `git merge upstream`
is not available, and every project drifts as soon as anyone edits it. The
question that matters is therefore not "what changed in the template" but "what
changed in the template that I have not already customized here".

This answers that, and answers it non-destructively. It prints; it never writes.
An auto-merging version of this tool is the dangerous version: template changes
routinely conflict with the project-specific decisions that make the project a
project, and silently resolving that is how a working analysis acquires an
edit nobody reviewed.

The classification is the whole design:

    unmodified  the project's copy is byte-identical to the template at the
                commit it was generated from, so the project never touched it
                and the template's newer version can be taken as-is.
    modified    the project's copy already differs from that baseline, so
                someone customized it. Applying the template change needs a
                human. Both diffs are offered.
    new         the file did not exist at the origin commit. Usually safe, but
                may be a language the project deliberately pruned.
    removed     the template deleted it. Never acted on automatically -- the
                project may depend on it.

Requires template-origin.toml, written by bootstrap.py. Without it there is no
baseline and the question is unanswerable; say so rather than guessing.

    repro-template-diff [--template-ref main] [--verbose]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ORIGIN_FILE = "template-origin.toml"

# Never reported: generated, environment, or per-project content. A template
# change to any of these is not something a project should be asked to adopt.
SKIP_PREFIXES = (
    "output/",
    "data/",
    "paper/",
    ".venv/",
    ".julia/",
    ".stata/",
    "private/",
    "replication-package/",
)
SKIP_NAMES = {
    ORIGIN_FILE,
    "uv.lock",  # follows pyproject.toml, which IS reported
    "_version.py",  # the project's own version, not the template's
    "CHANGELOG.md",
    "CITATION.cff",
}


def run(args: list[str], cwd: Path | None = None, check: bool = True) -> str:
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}... failed: {r.stderr.strip()}")
    return r.stdout


def read_origin(project: Path) -> dict:
    path = project / ORIGIN_FILE
    if not path.is_file():
        raise SystemExit(
            f"No {ORIGIN_FILE} in {project}.\n"
            "\n"
            "This project has no record of which template version it came from,\n"
            "so there is no baseline to compare against. Projects generated\n"
            "before bootstrap.py started writing that file need it created by\n"
            "hand: copy one from the template and set commit = the template\n"
            "commit this project was generated from, as best you can establish."
        )
    with path.open("rb") as f:
        return tomllib.load(f)


def template_clone(url: str, cache: Path) -> Path:
    """Keep one bare mirror of the template, refreshed on each run.

    A bare mirror rather than a working clone: nothing here is ever checked out,
    only diffed, and a mirror makes the fetch cheap on repeat runs.
    """
    cache.mkdir(parents=True, exist_ok=True)
    repo = cache / "template.git"
    if repo.is_dir():
        try:
            run(["git", "--git-dir", str(repo), "fetch", "--quiet", "origin"])
            return repo
        except RuntimeError:
            # A corrupt or half-fetched mirror should not be diagnosed here;
            # discard and re-clone, which is cheap and always correct.
            shutil.rmtree(repo, ignore_errors=True)
    run(["git", "clone", "--quiet", "--mirror", url, str(repo)])
    return repo


def changed_files(repo: Path, old: str, new: str) -> list[tuple[str, str]]:
    """[(status, path)] for the template's own history between two commits."""
    out = run(["git", "--git-dir", str(repo), "diff", "--name-status", f"{old}..{new}"])
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            rows.append((parts[0][:1], parts[-1]))
    return rows


def blob_at(repo: Path, ref: str, path: str) -> bytes | None:
    r = subprocess.run(
        ["git", "--git-dir", str(repo), "show", f"{ref}:{path}"],
        capture_output=True,
    )
    return r.stdout if r.returncode == 0 else None


# Files that exist only because a language does. A project that pruned that
# language should not be nudged to adopt them -- the whole point of pruning was
# to not have them.
LANGUAGE_MARKERS = {
    # env/Manifest.toml and env/Project.toml are Julia's, despite naming no
    # language. Matching on the name alone would also catch a Python project.toml,
    # so they are anchored to env/ where only Julia has them.
    "--remove-julia": (
        "julia",
        "juliacall",
        "juliapkg",
        ".jl",
        "env/manifest.toml",
        "env/project.toml",
    ),
    "--remove-stata": ("stata", ".do", ".ado"),
}


def pruned_language_hint(paths: list[str], flags: list[str]) -> set[str]:
    """Which of these new files belong to a language this project removed."""
    hits: set[str] = set()
    for flag in flags:
        markers = LANGUAGE_MARKERS.get(flag, ())
        for p in paths:
            low = p.lower()
            if any(m in low for m in markers):
                hits.add(p)
    return hits


def interesting(path: str) -> bool:
    if path in SKIP_NAMES:
        return False
    return not any(path.startswith(p) for p in SKIP_PREFIXES)


USAGE = """usage: repro-template-diff [--verbose] [--template-ref REF]

Show what has changed in the template since this project was generated from it.

options:
  --verbose             list every differing file, not just a summary
  --template-ref REF    compare against REF instead of the template's main
  -h, --help            show this message and exit

Reads template-origin.toml in the current directory to learn which template
commit this project came from.
"""


def main(argv: list[str]) -> int:
    """Parse argv by hand, but strictly.

    Argparse is avoided here only because this module predates the console
    script and is also imported directly. What is NOT optional is rejecting
    input it does not understand: until 2026-08-17 this parsed with
    `"--verbose" in argv` and silently ignored everything else, so a typo like
    `--verbos` ran a full template diff with verbosity off and reported
    success. There was no --help either, so `repro-template-diff --help`
    fetched the template and diffed it.
    """
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0

    verbose = "--verbose" in argv
    ref = "main"
    if "--template-ref" in argv:
        index = argv.index("--template-ref")
        if index + 1 >= len(argv):
            print("--template-ref needs a value", file=sys.stderr)
            print(USAGE, file=sys.stderr)
            return 2
        ref = argv[index + 1]

    known = {"--verbose", "--template-ref", ref}
    unknown = [a for a in argv if a not in known]
    if unknown:
        print(f"unknown argument(s): {' '.join(unknown)}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    project = Path.cwd()
    origin = read_origin(project)
    url = origin["template"]["url"]
    base = origin["template"]["commit"]
    flags = origin["template"].get("bootstrap_flags", [])

    if not base:
        raise SystemExit(
            f"{ORIGIN_FILE} records no commit, so there is no baseline to diff "
            "against. Fill in template.commit with the template commit this "
            "project was generated from."
        )

    cache = Path.home() / ".cache" / "repro-tools"
    print(f"Template : {url}")
    print(f"Generated from : {base[:12]}  (v{origin['template'].get('version', '?')})")
    if flags:
        print(f"Bootstrap flags: {' '.join(flags)}")
    print("Fetching template ...")
    repo = template_clone(url, cache)

    head = run(["git", "--git-dir", str(repo), "rev-parse", ref]).strip()
    if head == base:
        print(f"\nUp to date: the template's {ref} is still {base[:12]}.")
        return 0

    ahead = run(
        ["git", "--git-dir", str(repo), "rev-list", "--count", f"{base}..{head}"]
    ).strip()
    print(f"Template {ref} is now {head[:12]} ({ahead} commits ahead)\n")

    rows = [(s, p) for s, p in changed_files(repo, base, head) if interesting(p)]
    if not rows:
        print("No changes in files this project tracks.")
        return 0

    unmodified: list[str] = []
    modified: list[str] = []
    added: list[str] = []
    removed: list[str] = []
    current: list[str] = []

    for status, path in rows:
        local = project / path
        if status == "D":
            removed.append(path)
            continue
        # A submodule is a gitlink, not a file. Its "change" is a moved pointer,
        # and a project takes that with `git submodule update --remote`, not by
        # copying anything -- so reporting it beside real files would invite
        # exactly the wrong action.
        if local.is_dir():
            continue
        if status == "A" or not local.exists():
            added.append(path)
            continue
        blob = local.read_bytes()
        baseline = blob_at(repo, base, path)
        latest = blob_at(repo, head, path)
        if blob == latest:
            # Already identical to where the template ended up. Whether it got
            # here by an earlier partial update or by coincidence does not
            # matter: there is nothing left to apply, and calling it "modified"
            # would send someone to review a diff that is empty.
            current.append(path)
        elif baseline is None:
            added.append(path)
        elif blob == baseline:
            unmodified.append(path)
        else:
            modified.append(path)

    def show(title: str, items: list[str], note: str) -> None:
        if not items:
            return
        print(f"{title} ({len(items)})")
        print(f"  {note}")
        for p in sorted(items):
            print(f"    {p}")
        print()

    show(
        "SAFE TO TAKE",
        unmodified,
        "identical here to the version you generated from, so nothing local is lost",
    )
    show(
        "NEEDS A HUMAN",
        modified,
        "you have customized these; the template also changed them",
    )
    pruned = pruned_language_hint(added, flags)
    show(
        "NEW IN TEMPLATE",
        [p for p in added if p not in pruned],
        "absent at your origin commit",
    )
    show(
        "NEW, BUT FOR A LANGUAGE YOU PRUNED",
        sorted(pruned),
        f"bootstrap was run with {' '.join(flags)} -- almost certainly skip these",
    )
    show(
        "ALREADY CURRENT",
        current,
        "the template changed these, but your copy already matches the new version",
    )
    show(
        "DELETED IN TEMPLATE",
        removed,
        "never remove automatically; your project may depend on them",
    )

    if unmodified:
        print("To take the safe ones, from this project's root:")
        print(f"  git --git-dir {repo} show {head}:PATH > PATH")
        print("Then review `git diff` before committing. There is deliberately no")
        print("flag to apply them for you.\n")

    if verbose and modified:
        for path in sorted(modified):
            print("=" * 70)
            print(f"{path}: what the TEMPLATE changed")
            print("=" * 70)
            print(
                run(
                    [
                        "git",
                        "--git-dir",
                        str(repo),
                        "diff",
                        f"{base}..{head}",
                        "--",
                        path,
                    ]
                )
            )

    print(f"After applying, update {ORIGIN_FILE}: commit = {head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
