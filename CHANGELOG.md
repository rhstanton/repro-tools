# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
