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

[Unreleased]: https://github.com/rhstanton/repro-tools/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/rhstanton/repro-tools/releases/tag/v0.2.0
[0.1.0]: https://github.com/rhstanton/repro-tools/releases/tag/v0.1.0
