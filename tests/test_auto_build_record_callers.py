"""`auto_build_record` must survive callers that have no ``__file__``.

WHY THIS EXISTS

The function inspected its caller's frame unconditionally and indexed
``f_globals["__file__"]`` directly:

    caller_file = Path(frame.f_back.f_globals["__file__"]).resolve()

That raises ``KeyError: '__file__'`` for every caller that has no source file --
``python -c``, a REPL, an Emacs inferior shell, a Jupyter cell. Those are exactly
the interactive sessions research code is run from, and the call sits at the END
of an analysis, so the failure landed after all the expensive work was done.

It also fired even when the caller supplied both ``artifact_name`` and
``repo_root``, i.e. when nothing needed auto-detecting at all.

Found 2026-08-17 while wiring provenance into the fire replication package, whose
``run_did.py`` explicitly supports being run from Emacs and Jupyter.

The principle these tests defend: **provenance is evidence about a run, and must
never be the thing that destroys one.**

A NOTE ON HOW THEY ARE WRITTEN

The first attempt shelled out to ``python -c`` via ``sys.executable``. That is
the obvious way to get a caller with no ``__file__``, and it was wrong here: the
subprocess inherited the surrounding shell's environment and imported a
*different, older* copy of ``repro_tools`` from an unrelated project's virtualenv,
so the test reported the bug as unfixed while the fix was sitting right there.
``exec`` with an explicit globals dict needs no subprocess, no interpreter
lookup, and no environment at all -- it cannot test the wrong code.
"""

from __future__ import annotations

from pathlib import Path

from repro_tools import auto_build_record


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    inp = tmp_path / "input.txt"
    inp.write_text("input contents")
    out = tmp_path / "output.txt"
    out.write_text("output contents")
    return inp, out


def _call_with_no_caller_file(**kwargs) -> None:
    """Invoke auto_build_record from a frame whose globals lack ``__file__``.

    This is precisely the situation inside `python -c`, a REPL and a notebook
    cell, reproduced without leaving the process.
    """
    scope: dict = {"_fn": auto_build_record, "_kwargs": kwargs}
    assert "__file__" not in scope
    exec("_fn(**_kwargs)", scope)  # noqa: S102 - deliberate, see docstring


def test_no_caller_file_with_both_hints(tmp_path):
    """Nothing needs auto-detecting, so nothing should be introspected."""
    inp, out = _fixture(tmp_path)
    meta = tmp_path / "record.yml"
    _call_with_no_caller_file(
        out_meta=meta,
        inputs=[inp],
        outputs=[out],
        artifact_name="given",
        repo_root=tmp_path,
    )
    assert meta.exists()
    assert "artifact: given" in meta.read_text()


def test_no_caller_file_with_no_hints(tmp_path):
    """The auto-detect path must fall back, not raise."""
    inp, out = _fixture(tmp_path)
    meta = tmp_path / "derived.yml"
    _call_with_no_caller_file(out_meta=meta, inputs=[inp], outputs=[out])
    assert meta.exists()
    # Falls back to the out_meta stem when there is no caller file to name it.
    assert "artifact: derived" in meta.read_text()


def test_record_contains_the_evidence(tmp_path):
    """A record without hashes, a timestamp or git state is not provenance."""
    inp, out = _fixture(tmp_path)
    meta = tmp_path / "full.yml"
    auto_build_record(
        out_meta=meta,
        inputs=[inp],
        outputs=[out],
        artifact_name="full",
        repo_root=tmp_path,
    )
    text = meta.read_text()
    for expected in ("artifact:", "built_at_utc:", "git:", "inputs:", "outputs:"):
        assert expected in text, f"missing {expected!r} from the record"
    assert text.count("sha256:") >= 2, "both input and output must be hashed"
