"""JULIA_LOAD_PATH is assembled in env.sh, and the GPU env must layer onto it.

WHY THIS FILE EXISTS

`env.sh` sets JULIA_LOAD_PATH with a plain, unconditional assignment. That is
deliberate -- env/local.sh is sourced afterwards and can override anything -- but
it has a consequence that bit us: any JULIA_LOAD_PATH set by a caller before
invoking a wrapper is silently discarded.

Optional GPU support depends on that variable. CUDA.jl is never a dependency of
env/Project.toml (that would force a GPU stack onto every machine); it is
installed into a gitignored `.julia/gpu-env` and must be layered onto the load
path for `using CUDA` to resolve.

Until 2026-08-17 that layering happened only in run_did.py, in Python, after the
wrapper had already run. So GPU support existed through juliacall and was
invisible to `runjulia`:

    $ JULIA_LOAD_PATH="...:.julia/gpu-env" env/scripts/runjulia -e 'using CUDA'
    ERROR: ArgumentError: Package CUDA not found in current path.

with Julia reporting LOAD_PATH as the three entries env.sh had assigned, not the
four that were passed in. One feature, two entry points, different answers.

After moving the layering into env.sh, the same command prints
`functional=true`. These tests pin every branch of that logic, because the
failure mode is silent: a missing gpu-env entry does not error, it just runs on
the CPU while the user believes the GPU is in use.

HOW THESE TESTS WORK

env.sh is sourced in a real bash subprocess against a synthetic project root, so
what is measured is the file's actual behavior rather than a reimplementation of
it. Only the directory layout is faked; no Julia is required.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ENV_SH = Path(__file__).resolve().parents[1] / "src/repro_tools/lib/env.sh"


def source_env(
    root: Path, *, inherited: dict[str, str] | None = None, times: int = 1
) -> dict[str, str]:
    """Source env.sh `times` times against `root` and return the variables set.

    REPRO_PROJECT_ROOT is exported beforehand: env.sh derives it itself when
    unset, which would point at this repository rather than the fixture.
    """
    script = "\n".join(
        [f'export REPRO_PROJECT_ROOT="{root}"']
        + [f'source "{ENV_SH}"' for _ in range(times)]
        + [
            'echo "JULIA_LOAD_PATH=$JULIA_LOAD_PATH"',
            'echo "JULIA_PROJECT=$JULIA_PROJECT"',
            'echo "JULIA_DEPOT_PATH=$JULIA_DEPOT_PATH"',
        ]
    )
    env = os.environ.copy()
    env.pop("JULIA_LOAD_PATH", None)
    if inherited:
        env.update(inherited)
    result = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, env=env, timeout=120
    )
    assert result.returncode == 0, result.stderr
    out = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal project root: env/ and .julia/, no GPU env."""
    (tmp_path / "env").mkdir()
    (tmp_path / ".julia").mkdir()
    return tmp_path


def enable_gpu(root: Path, *, with_project_toml: bool = True) -> Path:
    gpu = root / ".julia" / "gpu-env"
    gpu.mkdir(parents=True, exist_ok=True)
    if with_project_toml:
        (gpu / "Project.toml").write_text(
            '[deps]\nCUDA = "052768ef-5323-5732-b1bb-66c8b64840ba"\n'
        )
    return gpu


def entries(vars: dict[str, str]) -> list[str]:
    return vars["JULIA_LOAD_PATH"].split(":")


# --- the base path, with no GPU env ---------------------------------------


def test_base_load_path_is_project_then_depot_then_stdlib(project):
    """Order matters: the project's own env must win over the juliapkg depot."""
    vars = source_env(project)
    assert entries(vars) == [
        str(project / "env"),
        str(project / ".julia"),
        "@stdlib",
    ]


def test_no_gpu_entry_when_gpu_env_absent(project):
    vars = source_env(project)
    assert "gpu-env" not in vars["JULIA_LOAD_PATH"]


# --- the GPU env ----------------------------------------------------------


def test_gpu_env_is_appended_when_present(project):
    """The regression: `using CUDA` cannot resolve without this entry."""
    gpu = enable_gpu(project)
    vars = source_env(project)
    assert entries(vars)[-1] == str(gpu), (
        "gpu-env is not on JULIA_LOAD_PATH, so `runjulia -e 'using CUDA'` will "
        "fail and the analysis will silently run on the CPU"
    )


def test_gpu_env_is_appended_last(project):
    """Appended, not prepended: the project's pinned env keeps priority.

    Prepending would let the GPU environment's own resolution of a shared
    dependency shadow the version pinned in env/Manifest.toml, which is the
    file the whole pinning story rests on.
    """
    enable_gpu(project)
    assert entries(source_env(project))[:3] == [
        str(project / "env"),
        str(project / ".julia"),
        "@stdlib",
    ]


def test_bare_gpu_directory_without_project_toml_is_ignored(project):
    """A half-created gpu-env is not GPU support.

    `Project.toml` is the marker the installer writes and run_did.py checks, so
    an empty directory -- left by an interrupted install, or by removing the
    file -- must not put an unusable environment on the load path.
    """
    enable_gpu(project, with_project_toml=False)
    assert "gpu-env" not in source_env(project)["JULIA_LOAD_PATH"]


def test_sourcing_twice_does_not_duplicate_the_gpu_entry(project):
    """env.sh documents that it must be safe to source repeatedly.

    It is idempotent here only because the base assignment is unconditional and
    runs before the append. That is easy to break by making the base assignment
    conditional, so it is pinned rather than assumed.
    """
    gpu = enable_gpu(project)
    path = source_env(project, times=3)["JULIA_LOAD_PATH"]
    assert path.split(":").count(str(gpu)) == 1


# --- the clobber, documented rather than discovered -----------------------


def test_inherited_load_path_is_replaced_not_extended(project):
    """env.sh OWNS this variable; a caller cannot contribute to it.

    This is why the GPU layering had to move into env.sh: setting
    JULIA_LOAD_PATH before calling a wrapper looks like it works and does
    nothing. If this behavior is ever changed deliberately, this test should
    change with it -- but it must not change silently.
    """
    vars = source_env(project, inherited={"JULIA_LOAD_PATH": "/somewhere/else"})
    assert "/somewhere/else" not in vars["JULIA_LOAD_PATH"]


def test_gpu_layering_survives_an_inherited_value(project):
    """The clobber must not also discard the GPU entry."""
    gpu = enable_gpu(project)
    vars = source_env(project, inherited={"JULIA_LOAD_PATH": "/somewhere/else"})
    assert entries(vars)[-1] == str(gpu)


# --- related variables, so a regression here is localized -----------------


def test_julia_project_and_depot_are_repo_local(project):
    """Neither may point outside the project; that is the isolation guarantee."""
    vars = source_env(project)
    assert vars["JULIA_PROJECT"] == str(project / "env")
    assert vars["JULIA_DEPOT_PATH"] == str(project / ".julia")
