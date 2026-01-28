# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Integration Test Suite**: Comprehensive testing for project generation and environment setup
  - 96 total tests (83 unit + 13 integration)
  - Tests for project creation, `make environment`, and `make examples`
  - Pytest markers: `@pytest.mark.slow` for Julia installation tests (~5-10 min each)
  - Pytest markers: `@pytest.mark.integration` for integration vs unit tests
  - Makefile targets: `make test-fast` (skip Julia), `make test-slow` (Julia only)
  - `tests/README.md` documenting test organization and usage
  - All fast tests passing (92/92) in ~2 minutes

- **Conditional Example Execution**: Julia and Stata examples now auto-detect
  - `make examples` checks if Julia files exist before running Julia examples
  - `make examples` checks if Stata files exist and runstata is executable before running Stata
  - Python-only projects no longer fail when Julia/Stata examples aren't installed
  - Fixes issue where `make examples` would fail in single-language projects

### Fixed
- **Package Import Bug**: Fixed `pyyaml` → `yaml` import name in integration tests
  - Package name is `pyyaml` but imports as `import yaml`
  - Integration tests now correctly check for PyYAML installation

- **Stata Example Auto-Run**: `make examples` now automatically runs Stata example if Stata files exist
  - Checks if `env/examples/sample_stata.do` exists and `env/scripts/runstata` is executable
  - Runs `sample-stata` target automatically when both conditions met
  - Previously always skipped Stata even when installed

## [0.3.0] - 2026-01-28

### Added
- **3-Level Defaults System**: DRY principle for multi-study projects
  - `DEFAULTS` dictionary in `config.py.template` with common study parameters
  - Studies inherit from DEFAULTS, only specify differences
  - Reduces duplication by 50-80% in projects with multiple analyses
  - Three priority levels: DEFAULTS → STUDIES[study] → command-line args
  
- **10 CLI Override Flags**: Runtime parameter customization in `run_analysis.py.template`
  - `--data=PATH` - Override input data file
  - `--yvar=NAME` - Override Y-axis variable
  - `--xvar=NAME` - Override X-axis variable
  - `--groupby=NAME` - Override grouping variable
  - `--xlabel=TEXT` - Override X-axis label
  - `--ylabel=TEXT` - Override Y-axis label
  - `--title=TEXT` - Override plot title
  - `--table-agg=FUNC` - Override table aggregation function
  - `--figure=PATH` - Override output figure path
  - `--table=PATH` - Override output table path
  
- **EXTRA_ARGS System**: Makefile-level parameter passing
  - Global `EXTRA_ARGS` variable applies to all analyses
  - Per-analysis `<analysis>_EXTRA_ARGS` for specific overrides
  - Five priority levels: Docopt defaults → DEFAULTS → STUDIES → EXTRA_ARGS → analysis_EXTRA_ARGS
  - Usage: `make sample_analysis EXTRA_ARGS="--ylabel='Custom Label'"`
  
- **Enhanced CLI Tools**: Improved user experience in `run_analysis.py.template`
  - `friendly_docopt()` with typo suggestions for invalid options
  - `setup_environment()` auto-detects Jupyter, IPython, Emacs, terminal
  - `print_config()` for transparent configuration display
  - `build_config()` function merges 3-level defaults system
  - `--list` option to display available studies
  - Better error messages with configuration validation
  
- **Line Ending Enforcement**: `.gitattributes` template prevents cross-platform issues
  - Force LF for all scripts (.sh, .py, .jl, .do, .ado)
  - Force LF for Makefiles (critical - tabs require LF)
  - Force LF for configs (.yml, .yaml, .toml)
  - Binary marking for data files (.pdf, .png, .dta, .sav, etc.)
  - Prevents Windows CRLF issues in multi-platform workflows
  
- **Integration Testing**: Comprehensive `test-integration.sh` script
  - 17 end-to-end test scenarios
  - Validates scaffolding, DEFAULTS, override flags, EXTRA_ARGS
  - Tests environment setup, builds, provenance, publishing
  - Color-coded output with automatic cleanup
  - Fail-fast behavior (set -e)

### Changed
- **config.py.template**: Simplified STUDIES definitions
  - Added DEFAULTS dictionary (7 common fields)
  - Studies now only specify differences (5 fields vs previous 10+)
  - DRY principle: eliminates 50-80% duplication
  - Enhanced documentation with 3-level system explanation
  
- **run_analysis.py.template**: Major enhancements (123 → 231 lines)
  - Enhanced docstring documenting all override flags
  - New imports: `friendly_docopt`, `setup_environment`, `print_config`, `print_validation_errors`
  - Added `list_studies()` function for cleaner study listing
  - Added `build_config(study_name, args)` - 40 line function merging 3 levels
  - Enhanced `main()` with better error handling and transparency
  - Changed from `docopt` to `friendly_docopt` for typo suggestions
  
- **Makefile.template**: Added EXTRA_ARGS support
  - 18 lines of documentation with usage examples
  - EXTRA_ARGS variable declaration (defaults to empty)
  - Updated build command to pass both global and per-analysis EXTRA_ARGS
  - Supports runtime parameter tuning without code changes

### Fixed
- **scaffold.py**: Added missing `.gitattributes` file copy
  - `.gitattributes` template now properly copied during project scaffolding
  - Prevents CRLF line ending issues on Windows
  - Ensures consistent line endings across platforms

### Improved
- **Developer Experience**: Templates now teaching-friendly
  - Self-documenting configuration with inline comments
  - Clear examples in DEFAULTS and STUDIES
  - Helpful error messages guide users to solutions
  - Transparency features show what's being used at runtime
  
- **Maintenance**: DRY principle reduces technical debt
  - Central DEFAULTS eliminates duplicate parameter definitions
  - Changes to common parameters update all studies automatically
  - Override system allows exceptions without breaking DRY
  
- **Flexibility**: Multi-level override system
  - Sensible defaults for quick starts
  - Study-specific customization when needed
  - Runtime overrides for experimentation
  - No code changes required for parameter tuning

### Technical Notes
- All enhancements upstreamed from `repro_template` battle-tested patterns
- Maintains backward compatibility - existing projects work unchanged
- Integration tests validate all features work together
- Templates follow established conventions from fire/housing-analysis project

### Added (from previous Unreleased)
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
