"""Every declared console script must actually resolve.

WHY THIS EXISTS

`pyproject.toml` declared

    repro-new-project = "repro_tools.cli:new_project"

long after commit 0171333 ("refactor: Archive project scaffolding
functionality") removed `new_project`. The entry point survived the function.
Anyone installing repro-tools got a `repro-new-project` command on their PATH
that failed with an ImportError the moment it was run, and nothing in the test
suite or in CI noticed, because nothing had ever asked whether the advertised
commands exist.

The reverse defect was present at the same time: `template_update.py` implements
the "apply template updates to an existing project" feature, documents its own
invocation in its module docstring, and had **no entry point at all**. The
feature was written, tested, and unreachable.

Both are the same omission -- the manifest and the code were never compared --
and this is the comparison.

Pure import checking: no subprocess, no installed environment, no PATH lookup,
so it tests the source in front of it rather than whatever happens to be
installed nearby.
"""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def declared_scripts() -> dict[str, str]:
    data = tomllib.loads(PYPROJECT.read_text())
    return data["project"].get("scripts", {})


def test_there_are_scripts_to_check():
    """Guard against the check passing because it found nothing."""
    scripts = declared_scripts()
    assert len(scripts) >= 5, f"only {len(scripts)} scripts found; parsing broke?"


@pytest.mark.parametrize("name,target", sorted(declared_scripts().items()))
def test_console_script_target_exists(name: str, target: str):
    """`pkg.mod:func` must import and be callable."""
    assert ":" in target, f"{name}: malformed entry point {target!r}"
    module_name, func_name = target.split(":", 1)

    module = importlib.import_module(module_name)
    func = getattr(module, func_name, None)
    assert func is not None, (
        f"{name} points at {target}, but {func_name!r} does not exist in "
        f"{module_name}. Either restore the function or drop the entry point -- "
        f"a command on PATH that ImportErrors is worse than no command."
    )
    assert callable(func), f"{name} points at {target}, which is not callable"


def test_template_diff_is_reachable():
    """The template-update feature specifically -- it had no entry point."""
    scripts = declared_scripts()
    assert "repro-template-diff" in scripts, (
        "template_update.py implements applying template updates to an existing "
        "project. Without an entry point the feature is unreachable."
    )
    module_name, func_name = scripts["repro-template-diff"].split(":", 1)
    module = importlib.import_module(module_name)
    assert callable(getattr(module, func_name))


def test_docstring_advertises_a_real_command():
    """template_update.py's docstring once named a command that never existed."""
    from repro_tools import template_update

    doc = template_update.__doc__ or ""
    declared = set(declared_scripts())
    # Any repro-* token in the docstring must be a command we actually ship.
    for token in {w.strip(".,`") for w in doc.split() if w.startswith("repro-")}:
        assert token in declared, (
            f"the module docstring advertises {token!r}, which is not a declared "
            f"console script. Declared: {sorted(declared)}"
        )
