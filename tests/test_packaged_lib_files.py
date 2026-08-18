"""The shared build machinery must survive being packaged.

src/repro_tools/lib/ holds common.mk, stata.mk and env.sh: the make targets and
environment definition consuming projects include and source. They are DATA, not
Python, and setuptools ships only *.py unless told otherwise.

Until 2026-08-18 nobody had told it, and the consequence depended on the
installer -- which is the part worth remembering:

    uv  pip install "repro-tools @ git+...@5fa0b90"   -> NO lib/ directory
    pip wheel .                                        -> lib/ files present

Both measured. Modern setuptools includes package-directory data of its own
accord when building here, so pip produced a correct wheel from the same source
that uv built without the files. Since both fire and project_template use uv,
the explicit stanza is what actually matters, and a test that builds with pip
CANNOT detect its absence.

That is why test_package_data_is_declared exists and is not redundant with the
wheel tests. The wheel tests confirm the files survive packaging; the
declaration test is the one that fails when the stanza goes away.

Found while trying to give fire the shared env.sh: fire pins repro-tools as a
git dependency, and the file simply was not there. project_template could not
have caught it -- it vendors the submodule and reads these files from the source
tree, which is the one consumer for whom packaging is irrelevant.
"""

from __future__ import annotations

import glob
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXPECTED = ["common.mk", "stata.mk", "env.sh"]


class TestSourceTree:
    """Cheap checks; necessary but nowhere near sufficient."""

    def test_lib_files_exist(self):
        for name in EXPECTED:
            assert (REPO / "src" / "repro_tools" / "lib" / name).is_file()

    def test_lib_dir_resolves(self):
        from repro_tools import lib_dir

        assert lib_dir().is_dir()
        for name in EXPECTED:
            assert (lib_dir() / name).is_file()

    def test_package_data_is_declared(self):
        """The primary guard, because the wheel tests cannot catch this.

        Measured 2026-08-18: with this stanza removed, `pip wheel` still
        produced a wheel containing every lib file, while uv installing the same
        source produced a package with no lib/ directory at all. Both projects
        consuming this one use uv, so the stanza is what decides whether the
        shared machinery ships -- and only this test notices when it goes.
        """
        text = (REPO / "pyproject.toml").read_text()
        assert "[tool.setuptools.package-data]" in text
        assert "lib/*.mk" in text and "lib/*.sh" in text


class TestLibPathCommand:
    def test_cli_prints_the_directory(self):
        result = subprocess.run(
            [sys.executable, "-m", "repro_tools.cli", "lib-path"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(REPO / "src"), "PATH": "/usr/bin:/bin"},
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        printed = Path(result.stdout.strip())
        assert printed.is_dir()
        assert (printed / "common.mk").is_file()


@pytest.mark.slow
class TestBuiltWheel:
    """Confirms the files survive packaging -- but see the module docstring:
    pip includes them even without the stanza, so these tests would have passed
    in the broken state. They guard the pipeline, not the declaration."""

    @staticmethod
    def build(tmp_path: Path) -> Path:
        venv = tmp_path / "bld"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        pip = venv / "bin" / "pip"
        subprocess.run(
            [str(pip), "install", "-q", "--upgrade", "pip", "setuptools", "wheel"],
            check=True,
            capture_output=True,
        )
        out = tmp_path / "dist"
        # --no-cache-dir is load-bearing, not hygiene. Without it pip reuses a
        # previously built wheel for the same version, so this test happily
        # inspected a wheel built BEFORE the packaging change. Verified: with
        # the package-data stanza removed, the cached run reported 1 failure
        # instead of 3, and the wheel-contents check -- the one test that exists
        # to catch exactly this -- passed against a stale artifact.
        subprocess.run(
            [
                str(pip),
                "wheel",
                "--no-deps",
                "--no-cache-dir",
                "-w",
                str(out),
                str(REPO),
            ],
            check=True,
            capture_output=True,
            timeout=900,
        )
        wheels = glob.glob(str(out / "*.whl"))
        assert wheels, "no wheel was built"
        return Path(wheels[0])

    def test_wheel_contains_every_lib_file(self, tmp_path):
        names = zipfile.ZipFile(self.build(tmp_path)).namelist()
        for name in EXPECTED:
            assert f"repro_tools/lib/{name}" in names, (
                f"{name} is missing from the wheel, so `pip install repro-tools` "
                f"would deliver an empty lib/ directory"
            )

    def test_installed_package_can_locate_them(self, tmp_path):
        """End to end: install the wheel and ask the installed package."""
        wheel = self.build(tmp_path)
        venv = tmp_path / "run"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run(
            [str(venv / "bin" / "pip"), "install", "-q", str(wheel)],
            check=True,
            capture_output=True,
            timeout=900,
        )
        result = subprocess.run(
            [
                str(venv / "bin" / "python"),
                "-c",
                "from repro_tools import lib_dir;"
                "import pathlib;"
                "d=lib_dir();"
                "print(sorted(p.name for p in pathlib.Path(d).iterdir()))",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        for name in EXPECTED:
            assert name in result.stdout, (
                f"{name} not found in the INSTALLED package: {result.stdout}"
            )
