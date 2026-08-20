"""common.mk is four layers plus an aggregator, and the seams must hold.

Split 2026-08-19. `include` is all-or-nothing, and 12 of the 30 shared targets
assume the template's project SHAPE -- $(DATA) as one input file, $(ANALYSES) as
a flat list at the root, $(OUT_*) directories, an env/ sub-Makefile. A project
shaped differently could therefore adopt none of the other 18: fire collided on
18 of 30 names and had hand-copied the generic ones, so every fix made here
reached project_template and never reached fire.

These tests pin the two properties that make the split safe: including common.mk
still yields every target (so no existing consumer changes), and no target is
defined twice (which make resolves silently, last-definition-wins).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

LIB = Path(__file__).resolve().parents[1] / "src/repro_tools/lib"
LAYERS = ("tools.mk", "repro.mk", "git.mk", "layout.mk")
TARGET = re.compile(r"^([a-zA-Z0-9][a-zA-Z0-9_.-]*):", re.M)


def targets_in(name: str) -> set[str]:
    return set(TARGET.findall((LIB / name).read_text()))


def test_every_layer_exists():
    for name in LAYERS:
        assert (LIB / name).is_file(), f"{name} missing"


def test_common_mk_includes_every_layer():
    text = (LIB / "common.mk").read_text()
    for name in LAYERS:
        assert f"include $(REPRO_LIB_DIR){name}" in text, f"common.mk omits {name}"


def test_common_mk_defines_no_targets_itself():
    """It is an aggregator. A target defined here would be invisible to a
    consumer that includes the layers directly."""
    assert targets_in("common.mk") == set()


def test_no_target_is_defined_in_two_layers():
    """make takes the last definition silently, so a duplicate is a live bug
    whose symptom is a recipe that mysteriously does the wrong thing."""
    seen: dict[str, str] = {}
    dupes = []
    for name in LAYERS:
        for t in targets_in(name):
            if t in seen:
                dupes.append(f"{t} in both {seen[t]} and {name}")
            seen[t] = name
    assert not dupes, "duplicate targets: " + "; ".join(dupes)


def test_the_layers_cover_the_documented_target_count():
    """A target dropped during the split would simply stop existing, and only a
    consumer calling it would find out."""
    total = set()
    for name in LAYERS:
        total |= targets_in(name)
    assert len(total) == 31, (
        f"expected 31 shared targets, found {len(total)}: {sorted(total)}"
    )


@pytest.mark.parametrize(
    "layer,forbidden",
    [
        ("tools.mk", ("$(DATA)", "$(ANALYSES)", "$(OUT_")),
        ("repro.mk", ("$(DATA)", "$(ANALYSES)")),
        ("git.mk", ("$(DATA)", "$(ANALYSES)", "$(OUT_", "$(PYTHON)")),
    ],
)
def test_a_layer_does_not_reach_past_its_contract(layer, forbidden):
    """The split is only useful if the contracts are real.

    tools.mk claiming to need just $(PYTHON) while using $(ANALYSES) would break
    for the very consumers the split exists to serve -- and it would break at
    `make` time in their project, not here.
    """
    text = (LIB / layer).read_text()
    # Ignore comment lines: they discuss the other layers by name.
    body = "\n".join(ln for ln in text.split("\n") if not ln.lstrip().startswith("#"))
    for var in forbidden:
        assert var not in body, f"{layer} uses {var}, which is outside its contract"


def test_packaging_ships_every_layer():
    """setuptools packages only *.py without an explicit stanza, so a new .mk
    would install as an empty gap -- the exact defect that made lib/ unreachable
    for consumers installing repro-tools as a package."""
    text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    assert "lib/*.mk" in text, "package-data does not ship lib/*.mk"


# Paths, not just variables. The first version of the contract test looked only
# for $(DATA)/$(ANALYSES)/$(OUT_*), so tools.mk passed while three of its targets
# hardcoded the template's own filenames -- `pytest tests/`, `mypy
# run_analysis.py shared/*.py`. Measured 2026-08-19: the first of those collects
# 147 tests in fire against the 326 its testpaths select, and prints a tick
# either way. A contract that only checks for variables misses the commonest way
# a shared target becomes project-specific.
HARDCODED = (
    "tests/",
    "run_analysis.py",
    "shared/",
    "output/",
    "paper/",
    "data/",
    "lib/repro-tools",
)


@pytest.mark.parametrize("layer", ["tools.mk", "repro.mk", "git.mk"])
def test_a_portable_layer_hardcodes_no_project_path(layer):
    """Recipe lines only: comments discuss these paths by name, and the header
    of each file explains exactly which ones it used to contain."""
    offenders = []
    for i, line in enumerate((LIB / layer).read_text().split("\n"), 1):
        if not line.startswith("\t"):
            continue
        for frag in HARDCODED:
            if frag in line:
                offenders.append(f"{layer}:{i}: {frag!r} in {line.strip()[:60]}")
    assert not offenders, "hardcoded project paths:\n" + "\n".join(offenders)


def test_the_knobs_have_defaults_that_preserve_template_behavior():
    """Every knob uses ?=, so a project setting it before the include wins and
    a project that does not is unaffected."""
    for layer, knobs in (
        (
            "tools.mk",
            [
                "TEST_PATHS",
                "COV_TARGET",
                "LINT_PATHS",
                "TYPECHECK_PATHS",
                "RUFF_EXCLUDE",
            ],
        ),
        ("repro.mk", ["REPORT_OUTPUT"]),
    ):
        text = (LIB / layer).read_text()
        for knob in knobs:
            assert f"{knob} ?=" in text, f"{layer} does not define {knob} with ?="


def test_the_declared_version_is_ahead_of_every_release_tag():
    """pyproject.toml and the git tags must not disagree about the version.

    Found 2026-08-19: v0.3.0, v0.3.1, v0.3.2 and v0.3.3 were all tagged on
    2026-01-28, and not one of them updated pyproject.toml, which sat at 0.2.0
    throughout. So four releases reported themselves as 0.2.0, the CHANGELOG
    skipped them entirely, and a consumer that recorded "0.3.3" looked wrong
    when it was in fact the only thing telling the truth.

    Tagging succeeds whether or not the declared version was bumped, so nothing
    ever surfaced it. This test is the missing check.
    """
    import re
    import subprocess

    root = Path(__file__).resolve().parents[1]
    m = re.search(r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(), re.M)
    assert m, "pyproject.toml declares no version"
    declared = tuple(int(x) for x in m.group(1).split("."))

    out = subprocess.run(
        ["git", "tag"], cwd=root, capture_output=True, text=True, timeout=60
    )
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    tags = []
    for t in out.stdout.split():
        tm = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", t)
        if tm:
            tags.append(tuple(int(x) for x in tm.groups()))
    if not tags:
        pytest.skip("no release tags yet")
    assert declared > max(tags), (
        f"pyproject declares {m.group(1)} but v{'.'.join(map(str, max(tags)))} is "
        "already tagged; the next release would collide with an existing tag"
    )
