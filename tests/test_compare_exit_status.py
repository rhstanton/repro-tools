"""`repro-compare` must report its answer in its exit status.

WHY THIS EXISTS

`cli.compare()` computed whether the outputs matched and then threw the answer
away:

    all_identical, report = compare_outputs(...)
    print(report)
    sys.exit(0)          # regardless

So `make diff-outputs` -- announced as "Comparing current outputs with published
outputs" -- passed whether or not they matched. A comparison that always
succeeds is not a comparison, and anything reading the exit code, CI included,
was being told the outputs agreed without anyone having checked.

Three paths, all of which must hold:

    identical            -> 0
    genuinely different  -> 1
    no reference at all  -> 0, because a project has no published outputs until
                            it publishes, and exiting 1 there would make
                            `make diff-outputs` red on arrival in every fresh
                            project

The third is the one that makes the second safe to enable.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def _invoke(reference: Path, current: Path) -> int:
    """Call cli.compare() in-process with argv set, capturing SystemExit."""
    import repro_tools.cli as cli

    argv = sys.argv
    sys.argv = [
        "repro-compare",
        "--reference",
        str(reference),
        "--current-dir",
        str(current),
    ]
    try:
        cli.compare()
    except SystemExit as e:
        return int(e.code or 0)
    finally:
        sys.argv = argv
    return 0


def _make_tree(root: Path, table_text: str) -> Path:
    (root / "figures").mkdir(parents=True, exist_ok=True)
    (root / "tables").mkdir(parents=True, exist_ok=True)
    (root / "figures" / "a.pdf").write_bytes(b"%PDF-1.4\nfake\n")
    (root / "tables" / "a.tex").write_text(table_text)
    return root


def test_missing_reference_is_not_a_failure(capsys):
    d = Path(tempfile.mkdtemp())
    current = _make_tree(d / "output", "x & 1\n")
    assert _invoke(d / "nonexistent", current) == 0
    assert "nothing to compare" in capsys.readouterr().out


def test_identical_outputs_exit_zero(capsys):
    d = Path(tempfile.mkdtemp())
    text = "x & 1\n"
    current = _make_tree(d / "output", text)
    reference = _make_tree(d / "paper", text)
    (reference / "figures" / "a.pdf").write_bytes(
        (current / "figures" / "a.pdf").read_bytes()
    )
    assert _invoke(reference, current) == 0


def test_different_outputs_exit_nonzero(capsys):
    """THE REGRESSION. This returned 0 before the fix."""
    d = Path(tempfile.mkdtemp())
    current = _make_tree(d / "output", "x & 1\n")
    reference = _make_tree(d / "paper", "x & 999\n")
    (reference / "figures" / "a.pdf").write_bytes(
        (current / "figures" / "a.pdf").read_bytes()
    )
    assert _invoke(reference, current) == 1, (
        "differing outputs exited 0 -- `make diff-outputs` would pass while the "
        "numbers disagree"
    )
