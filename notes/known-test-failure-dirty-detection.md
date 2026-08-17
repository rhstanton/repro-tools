# `dirty` means tracked-only, and one test assumed otherwise

**RESOLVED 2026-08-17** for the failing test; the design question below is still
open and is yours to settle.

The test now dirties a **tracked** file (`README.md`) instead of creating an
untracked one, which matches what `git_state` actually measures. Suite: 61 passed.

The rest of this note is the investigation, kept because the design question it
raises has not gone away.

---

## Original writeup: `test_publish_artifacts_built_dirty_allowed` fails locally

Investigated 2026-08-17. **Not fixed** — the obvious fix breaks eight other
tests, and the fix that would work needs a fixture change that should be made
deliberately rather than in passing.

## What the test asserts

`tests/test_publishing.py::TestPublishAnalyses::test_publish_artifacts_built_dirty_allowed`
builds artifacts while the repo is dirty, cleans the repo, and expects
`publish_analyses(..., allow_dirty=False)` to raise `SystemExit` matching
`"artifacts were built from a dirty working tree"`.

Locally it does not raise: `Failed: DID NOT RAISE SystemExit`.

## Why it does not raise

The test makes the repo dirty with

```python
(repo / "dirty.txt").write_text("uncommitted change")
```

and never `git add`s it, so the file is **untracked**.

`core.git_state` detects dirtiness with

```python
subprocess.check_call(["git", "diff", "--quiet"], cwd=str(repo_root))
subprocess.check_call(["git", "diff", "--cached", "--quiet"], cwd=str(repo_root))
```

`git diff` sees tracked modifications; `git diff --cached` sees staged changes.
**Neither sees untracked files.** So the provenance record written while
`dirty.txt` exists says `dirty: false`, `publish_analyses` finds nothing to
object to, and the expected `SystemExit` never happens.

## The obvious fix, and why it was reverted

Replacing both calls with `git status --porcelain` — which reports tracked *and*
untracked — fixes this test and takes the suite from **1 failure to 9**.

The other eight fail because the test fixtures write build artifacts (figures,
tables, provenance YAML) into the temp repo without a `.gitignore`. Under the
stricter check every one of those repos is dirty the moment it has been built in,
so tests asserting a clean tree fail.

That is a fixture problem rather than a reason to keep the weaker check. In a
real project, outputs are gitignored and gitignored files do not appear in
`git status --porcelain`, so the stricter check behaves correctly there.

**The argument for making the change anyway, later:** an untracked script is a
perfectly good candidate for the thing that produced the output being described.
Provenance that reports "clean" about a tree it has not fully inspected is worse
than provenance that reports nothing, because it will be believed.

**What it needs:** give the test fixtures a `.gitignore` covering the artifact
paths, then switch `git_state` to `git status --porcelain`, then confirm all 61
tests pass. Perhaps twenty minutes, and it should be one deliberate commit.

## What was NOT established

**Why CI passes.** The test has existed since `e80dd8a` (2026-01-18) and the
suite was green on the most recent CI run (2026-08-17), on the same commit that
fails here. The mechanism above is deterministic given the repo state, so
something about the environment must differ, and I did not find it.

Ruled out: a global gitignore hiding `dirty.txt`. Checked directly — in a fresh
`git init` on this machine, `git status --porcelain` reports `?? dirty.txt` both
with and without `core.excludesfile`, so the file is visible to git here.

Worth knowing before trusting either result: a test that passes in one
environment and fails in another is not telling you the code is fine in one of
them. It is telling you the test depends on something nobody has named.


## The design question, still open

`git_state` defines `dirty` as **tracked content differing from HEAD**:
`git diff --quiet` plus `git diff --cached --quiet`. Untracked files do not count.

There is a real argument that they should. An untracked script is a perfectly
good candidate for whatever produced the output being described, and provenance
that calls such a tree "clean" is being generous about something it has not
looked at.

The argument against is what the attempt showed: switching to
`git status --porcelain` breaks **thirteen** tests, because these fixtures leave
inputs and built outputs untracked, so every built repo becomes dirty. A real
project gitignores its outputs and would not see this — but "would not see this
if configured correctly" is exactly the kind of assumption that ought to be
stated rather than relied on.

Attempted twice, reverted twice: first with a broad fixture `.gitignore`
(`output/ data/ paper/`), which left `git commit` with nothing to commit and
errored; then with a narrow one covering only built outputs, which still failed
thirteen tests. Instrumenting rather than guessing a third time showed why —
after the fixtures build, `--porcelain` reports `?? data/input.csv` and
`?? output/tables/test_analysis.tex`.

**If you want the stricter meaning**, it is: gitignore the built outputs in the
fixtures, `git add` the inputs, switch `git_state` to `--porcelain`, and re-check
all 61. It is a change to what `dirty` means for every consumer of this library,
so it deserves to be decided rather than absorbed as a bug fix.
