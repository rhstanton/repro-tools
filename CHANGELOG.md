# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Project Scaffolding**: Complete Stata support in `scaffold.py`
  - Generated `env/stata-packages.txt` for package management
  - Generated `env/scripts/runstata` wrapper for executing .do files
  - Generated `env/scripts/execute.ado` helper for proper logging
  - Added Stata installation targets to `env/Makefile` (stata-env, stata-clean, stata-check)
  - Stata packages installed locally to `.stata/ado/plus/`
- **Example Files**: Auto-generate language-specific examples in `env/examples/`
  - `sample_python.py` for Python
  - `sample_julia.jl` for pure Julia
  - `sample_juliacall.py` for Python/Julia interop
  - `sample_stata.do` for Stata
  - `README.md` with usage instructions

### Changed
- **Project Scaffolding**: Enhanced multi-language support
  - All three languages (Python, Julia, Stata) fully integrated
  - Example files generated based on selected languages
  - Environment setup targets properly sequenced

## [0.3.0] - 2026-08-19

Eighty-seven commits since 0.2.0 (January), during which the declared version
never moved. Consumers pin by submodule commit, so nothing broke — but a package
claiming 0.2.0 while shipping substantially different behavior is a false
statement that costs nothing to make and something to believe.

### Added
- `lib/` is split by contract into `tools.mk` ($(PYTHON) only), `repro.mk`
  (+ the package), `git.mk` (git only) and `layout.mk` (project shape).
  `common.mk` includes all four, so existing consumers are unaffected. The split
  is what let a differently-shaped project adopt part of the machinery: `include`
  is all-or-nothing, and twelve of the thirty targets assumed one project shape.
- `list-analyses-names`: bare artifact names, one per line, so `repro-check` can
  ask make instead of regexing a Makefile.
- `lib-path` CLI command, so a Makefile can locate the shared machinery whether
  repro-tools is vendored or installed.

### Fixed
- `cli.py` had no `__main__` dispatcher, so `python -m repro_tools.cli publish`
  ignored its arguments and exited 0. The publish/verify surface was unreachable.
- Shared targets whose command variable was undefined ran the empty string and
  passed. `make pre-submit` in a project that did not define `REPRO_CHECK`
  printed its banner, did nothing, and reported success.
- `$(REPO_ROOT)` was passed to `--repo-root` with no default.
- The artifact check assumed a flat `output/<kind>/<name>` and reported every
  artifact missing in projects that group outputs into subdirectories.
- `init-submodules` swallowed stderr and the exit status; its message now names
  the likeliest cause first (a non-empty path from a copied working tree) rather
  than sending the reader to check working credentials.
- `lib/*.mk` and `lib/*.sh` now ship in the wheel. Without the package-data
  stanza setuptools packaged only `*.py`, so installing repro-tools gave you an
  empty `lib/` — invisible to the one consumer that vendors the submodule.

### Removed
- This repository's own `project_template/` directory: a second scaffold
  duplicating the real template repo, referenced by no code, not packaged, not
  used by `template-diff`, and still being maintained by hand.

## [0.2.0] - 2026-01-18

### Added
- Automatic provenance tracking via `enable_auto_provenance(__file__)`
- Config-based provenance with `auto_provenance_from_config()`
- Two-mode publishing: analysis-based and file-based
- Git safety checks in publishing workflow (dirty, behind, current HEAD)
- Command-line interface via `python -m repro_tools.cli`
- Output comparison tools (`compare.py`)
- System information logging (`sysinfo.py`)
- Pre-submission validation checks (`presubmit.py`)
- Replication report generation (`report.py`)
- Comprehensive test suite
- Documentation (README, QUICKSTART, MIGRATION guide)
- Example scripts

### Changed
- Migrated from inline scripts to installable package
- Switched to modern `pyproject.toml` configuration
- Updated provenance format to include git state and checksums

## [0.1.0] - Initial Development

### Added
- Basic provenance recording functionality
- Initial publishing workflows
- Core git state tracking

[Unreleased]: https://github.com/rhstanton/repro-tools/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/rhstanton/repro-tools/releases/tag/v0.3.0
[0.2.0]: https://github.com/rhstanton/repro-tools/releases/tag/v0.2.0
[0.1.0]: https://github.com/rhstanton/repro-tools/releases/tag/v0.1.0
