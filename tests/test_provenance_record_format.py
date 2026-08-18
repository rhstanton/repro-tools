"""What a provenance record contains, and why each choice was made.

Three changes on 2026-08-18, each answering a question that had been left open:

1. UNTRACKED FILES ARE RECORDED, BUT DO NOT MAKE A TREE "DIRTY".

   `dirty` is what publishing gates on, and a gate that fires constantly gets
   switched off -- ALLOW_DIRTY=1 in a CI config disables it permanently and
   silently. So `dirty` stays tracked-only. But an untracked script is a
   perfectly good candidate for whatever produced the artifact, and a record
   calling such a tree clean is generous about something it never looked at.
   The numbers in a submitted paper were once produced by code predating its
   repository's first commit; provenance would have called that tree clean.
   Record it, do not gate on it.

2. PATHS ARE RELATIVE TO THE REPOSITORY ROOT.

   Absolute paths meant records could not be compared across machines -- every
   path differed, so diffing two byte-identical builds was noise -- and
   paper/provenance.yml, which IS committed and can accompany a submission,
   published the author's home directory.

3. mtime IS NOT RECORDED.

   It changes on every checkout and copy, so it made two identical builds
   produce different records while saying nothing sha256 does not say better.

Old records (absolute paths, no repo_root) must keep working, so
resolve_recorded_path handles both conventions.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from repro_tools.core import (
    UNTRACKED_LIMIT,
    git_state,
    resolve_recorded_path,
    write_build_record,
)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A committed git repo with one tracked input and a gitignored output dir."""
    repo = tmp_path / "proj"
    (repo / "data").mkdir(parents=True)
    (repo / "output").mkdir()
    git(repo, "init", "-q", ".")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "T")
    (repo / ".gitignore").write_text("output/\n")
    (repo / "data" / "input.csv").write_text("a,b\n1,2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    return repo


def build(repo: Path, extra_inputs=None, out_meta=None) -> dict:
    (repo / "output" / "fig.pdf").write_text("pdf\n")
    write_build_record(
        out_meta=out_meta or (repo / "output" / "rec.yml"),
        artifact_name="demo",
        command=["make", "demo"],
        repo_root=repo,
        inputs=[repo / "data" / "input.csv", *(extra_inputs or [])],
        outputs=[repo / "output" / "fig.pdf"],
    )
    return yaml.safe_load((out_meta or (repo / "output" / "rec.yml")).read_text())


# --- untracked files -------------------------------------------------------


class TestUntrackedFiles:
    def test_clean_repo_reports_none(self, repo):
        state = git_state(repo)
        assert state["untracked_count"] == 0
        assert state["untracked"] == []
        assert state["untracked_truncated"] is False

    def test_untracked_file_is_recorded(self, repo):
        (repo / "analysis.py").write_text("# the script that made the numbers\n")
        state = git_state(repo)
        assert state["untracked_count"] == 1
        assert state["untracked"] == ["analysis.py"]

    def test_untracked_file_does_not_set_dirty(self, repo):
        """The decision: report it, do not gate on it."""
        (repo / "analysis.py").write_text("x\n")
        assert git_state(repo)["dirty"] is False

    def test_modified_tracked_file_still_sets_dirty(self, repo):
        """The other half: the existing meaning of `dirty` is unchanged."""
        (repo / "data" / "input.csv").write_text("changed\n")
        assert git_state(repo)["dirty"] is True

    def test_gitignored_files_are_not_untracked(self, repo):
        """A project that ignores its outputs sees an empty list.

        This is the whole reason the stricter definition looked unusable: every
        built fixture repo became dirty. Ignored files are invisible to
        `git ls-files --others --exclude-standard`, so a correctly configured
        project is quiet.
        """
        (repo / "output" / "fig.pdf").write_text("built\n")
        assert git_state(repo)["untracked_count"] == 0

    def test_listing_is_capped_but_the_count_is_exact(self, repo):
        for i in range(UNTRACKED_LIMIT + 7):
            (repo / f"scratch{i:03d}.txt").write_text("x\n")
        state = git_state(repo)
        assert state["untracked_count"] == UNTRACKED_LIMIT + 7
        assert len(state["untracked"]) == UNTRACKED_LIMIT
        assert state["untracked_truncated"] is True

    def test_listing_is_sorted_so_records_are_comparable(self, repo):
        for name in ("zeta.py", "alpha.py", "mu.py"):
            (repo / name).write_text("x\n")
        assert git_state(repo)["untracked"] == ["alpha.py", "mu.py", "zeta.py"]

    def test_untracked_appears_in_a_written_record(self, repo):
        (repo / "analysis.py").write_text("x\n")
        record = build(repo)
        assert record["git"]["untracked_count"] == 1
        assert "analysis.py" in record["git"]["untracked"]


# --- paths -----------------------------------------------------------------


class TestPaths:
    def test_inputs_and_outputs_are_repo_relative(self, repo):
        record = build(repo)
        assert record["inputs"][0]["path"] == "data/input.csv"
        assert record["outputs"][0]["path"] == "output/fig.pdf"

    def test_repo_root_is_recorded_once(self, repo):
        record = build(repo)
        assert record["repo_root"] == str(repo.resolve())

    def test_no_absolute_home_directory_leaks_into_the_record(self, repo, tmp_path):
        """The concrete harm: paper/provenance.yml is committed and shipped."""
        build(repo)
        text = (repo / "output" / "rec.yml").read_text()
        # repo_root is the one place an absolute path legitimately appears.
        for line in text.splitlines():
            if line.startswith("repo_root:"):
                continue
            assert str(tmp_path) not in line, f"absolute path leaked: {line}"

    def test_a_file_outside_the_repo_stays_absolute(self, repo, tmp_path):
        """Not a failure -- it says the build depended on something outside.

        A replicator needs to know that, and there is no relative path that
        could express it honestly.
        """
        outside = tmp_path / "elsewhere.csv"
        outside.write_text("x\n")
        record = build(repo, extra_inputs=[outside])
        recorded = [i["path"] for i in record["inputs"]]
        assert str(outside.resolve()) in recorded

    def test_mtime_is_not_recorded(self, repo):
        """It differs on every checkout, so it made identical builds differ."""
        record = build(repo)
        for entry in record["inputs"] + record["outputs"]:
            assert "mtime" not in entry

    def test_hash_and_size_are_still_recorded(self, repo):
        record = build(repo)
        entry = record["inputs"][0]
        assert len(entry["sha256"]) == 64
        assert entry["bytes"] == len("a,b\n1,2\n")

    def test_two_builds_of_identical_content_agree_except_for_time(self, repo):
        """The point of dropping mtime and absolutising nothing.

        Everything that is not a genuine record of *when* must match, so a diff
        between two records is about the artifacts rather than the filesystem.
        """
        first = build(repo, out_meta=repo / "output" / "a.yml")
        second = build(repo, out_meta=repo / "output" / "b.yml")
        for record in (first, second):
            record.pop("built_at_utc")
        assert first == second


class TestResolveRecordedPath:
    def test_resolves_a_relative_path_against_repo_root(self, repo):
        record = build(repo)
        resolved = resolve_recorded_path(record["inputs"][0], record)
        assert resolved == (repo / "data" / "input.csv").resolve()
        assert resolved.is_file()

    def test_an_absolute_recorded_path_is_used_as_written(self):
        """Records written before 2026-08-18 stored absolute paths."""
        entry = {"path": "/somewhere/data.csv"}
        assert resolve_recorded_path(entry, {}) == Path("/somewhere/data.csv")

    def test_a_relative_path_without_repo_root_falls_back_to_cwd(
        self, monkeypatch, tmp_path
    ):
        """Very old records have neither convention; do something defined."""
        monkeypatch.chdir(tmp_path)
        assert resolve_recorded_path({"path": "x.csv"}, {}) == tmp_path / "x.csv"

    def test_old_and_new_records_resolve_to_the_same_file(self, repo):
        """A project with a mix of old and new records keeps working."""
        record = build(repo)
        new_entry = record["inputs"][0]
        old_entry = {"path": str((repo / "data" / "input.csv").resolve())}
        assert resolve_recorded_path(new_entry, record) == resolve_recorded_path(
            old_entry, {}
        )


class TestPublishedRecordGitState:
    """`analysis_git` in paper/provenance.yml must describe THIS publish.

    It was written with `prov.setdefault(...)`, so it was set once and frozen
    forever while `last_updated_utc` kept refreshing beside it. Measured on
    project_template 2026-08-18: republishing moved the timestamp to
    07:03:10 and left `is_git_repo: false`, inherited from January. That file is
    committed to the paper repository and can accompany a submission, so the
    record made a false statement about published results, with a fresh date on
    it.
    """

    def test_analysis_git_is_refreshed_on_republish(self, repo, tmp_path):
        from repro_tools import publish_analyses

        paper = tmp_path / "paper"
        paper.mkdir()
        prov = paper / "provenance.yml"

        # A pre-existing record carrying a stale, wrong claim.
        prov.write_text(
            yaml.safe_dump(
                {
                    "paper_provenance_version": 1,
                    "analysis_git": {"is_git_repo": False},
                    "artifacts": {},
                }
            )
        )

        (repo / "output" / "figures").mkdir(parents=True, exist_ok=True)
        (repo / "output" / "tables").mkdir(parents=True, exist_ok=True)
        (repo / "output" / "provenance").mkdir(parents=True, exist_ok=True)
        (repo / "output" / "figures" / "demo.pdf").write_text("pdf\n")
        (repo / "output" / "tables" / "demo.tex").write_text("tex\n")
        write_build_record(
            out_meta=repo / "output" / "provenance" / "demo.yml",
            artifact_name="demo",
            command=["make", "demo"],
            repo_root=repo,
            inputs=[repo / "data" / "input.csv"],
            outputs=[
                repo / "output" / "figures" / "demo.pdf",
                repo / "output" / "tables" / "demo.tex",
            ],
        )

        publish_analyses(
            project_root=repo,
            paper_root=paper,
            analysis_names=["demo"],
            allow_dirty=True,
            require_not_behind=False,
            verbose=False,
        )

        published = yaml.safe_load(prov.read_text())
        assert published["analysis_git"]["is_git_repo"] is True, (
            "analysis_git was not refreshed; the published record still claims "
            "the analysis is not a git repository"
        )
        assert published["analysis_git"]["commit"], "no commit recorded"

    def test_schema_version_is_still_only_set_once(self, repo, tmp_path):
        """The contrast: some fields SHOULD be defaulted rather than assigned.

        A schema version describes the file's format, not this publish, so
        `setdefault` is right there. Pinned so a future sweep of setdefault
        calls does not "fix" it too.
        """
        from repro_tools import publish_analyses

        paper = tmp_path / "paper"
        paper.mkdir()
        (paper / "provenance.yml").write_text(
            yaml.safe_dump({"paper_provenance_version": 99, "artifacts": {}})
        )
        (repo / "output" / "figures").mkdir(parents=True, exist_ok=True)
        (repo / "output" / "provenance").mkdir(parents=True, exist_ok=True)
        (repo / "output" / "figures" / "demo.pdf").write_text("pdf\n")
        write_build_record(
            out_meta=repo / "output" / "provenance" / "demo.yml",
            artifact_name="demo",
            command=["make", "demo"],
            repo_root=repo,
            inputs=[repo / "data" / "input.csv"],
            outputs=[repo / "output" / "figures" / "demo.pdf"],
        )
        publish_analyses(
            project_root=repo,
            paper_root=paper,
            analysis_names=["demo"],
            allow_dirty=True,
            require_not_behind=False,
            verbose=False,
        )
        published = yaml.safe_load((paper / "provenance.yml").read_text())
        assert published["paper_provenance_version"] == 99


class TestDocumentedSchemaMatchesReality:
    """The README's example record must have the same shape as a real one.

    This is a public archive, and the record format is the part people read
    before deciding whether to trust the tool. It has been wrong before: the
    README documented `mtime` and absolute paths for as long as those existed,
    and project_template's README documented RELATIVE paths years before
    anything produced them -- a convention that was aspirational rather than
    real, which is worse than an out-of-date example because it looks correct.
    """

    @staticmethod
    def documented_record() -> dict:
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text()
        block = readme.split("## Provenance Format", 1)[1]
        block = block.split("```yaml", 1)[1].split("```", 1)[0]
        return yaml.safe_load(block)

    def test_documented_top_level_keys_match_a_real_record(self, repo):
        documented = set(self.documented_record())
        actual = set(build(repo))
        assert documented == actual, (
            f"README documents {sorted(documented - actual)} which a record does "
            f"not have, and omits {sorted(actual - documented)}"
        )

    def test_documented_git_keys_match(self, repo):
        documented = set(self.documented_record()["git"])
        actual = set(build(repo)["git"])
        assert documented == actual, (
            f"README's git block documents {sorted(documented - actual)} and "
            f"omits {sorted(actual - documented)}"
        )

    def test_documented_file_entry_keys_match(self, repo):
        documented = set(self.documented_record()["inputs"][0])
        actual = set(build(repo)["inputs"][0])
        assert documented == actual, (
            f"README's input entry documents {sorted(documented - actual)} and "
            f"omits {sorted(actual - documented)}"
        )

    def test_documented_paths_are_relative(self):
        """A published example showing absolute paths teaches the wrong thing."""
        record = self.documented_record()
        for entry in record["inputs"] + record["outputs"]:
            assert not Path(entry["path"]).is_absolute(), (
                f"README documents an absolute path: {entry['path']}"
            )
