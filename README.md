# repro-tools

**Reproducibility tools for research and teaching**

A lightweight Python package for tracking provenance and publishing outputs in computational research projects. Ensures full reproducibility by tracking git state, input/output checksums, and build metadata.

## Features

- **Provenance Tracking**: Automatically capture git state, input/output checksums, timestamps, and build commands
- **Flexible Publishing**: Two-mode system for publishing complete analyses or specific files
- **Git Safety Checks**: Enforce clean working tree, current HEAD, and upstream sync before publishing
- **Teaching-Friendly**: Simple API, clear documentation, minimal dependencies

## Installation

### Development (Editable Install)

For local development or teaching:

```bash
pip install -e /home/stanton/01_work/infrastructure/40_lib/python/repro-tools
```

Or add to your conda `environment.yml`:

```yaml
dependencies:
  - pip:
    - -e /home/stanton/01_work/infrastructure/40_lib/python/repro-tools
```

### From PyPI (Future)

```bash
pip install repro-tools
```

## Quick Start

### Basic Provenance Tracking

```python
from pathlib import Path
from repro_tools import write_build_record

# In your build script
write_build_record(
    out_meta=Path("output/provenance/my_analysis.yml"),
    artifact_name="my_analysis",
    command=["python", "build_my_analysis.py", "--data", "data.csv"],
    repo_root=Path("."),
    inputs=[Path("data.csv")],
    outputs=[Path("output/figure.pdf"), Path("output/table.tex")],
)
```

### Auto-Detection

```python
from repro_tools import auto_build_record

# Simpler version - auto-detects artifact name, repo root, command
auto_build_record(
    out_meta=Path("output/provenance/my_analysis.yml"),
    inputs=[Path("data.csv")],
    outputs=[Path("output/figure.pdf"), Path("output/table.tex")],
)
```

### Publishing Complete Analyses

```python
from pathlib import Path
from repro_tools import publish_analyses

publish_analyses(
    project_root=Path("."),
    paper_root=Path("paper"),
    analysis_names=["price_base", "remodel_base"],
    kinds=["figures", "tables"],
    require_current_head=True,  # Strict mode
)
```

### Publishing Specific Files

```python
from repro_tools import publish_files

publish_files(
    project_root=Path("."),
    paper_root=Path("paper"),
    file_paths=[
        Path("output/figures/figure1.pdf"),
        Path("output/tables/table1.tex"),
    ],
)
```

## Core Functions

### Provenance Tracking

- `git_state(repo_root)` - Capture git commit, branch, dirty status, ahead/behind counts
- `sha256_file(path)` - Compute SHA256 checksum of a file
- `write_build_record(...)` - Write complete build provenance record
- `auto_build_record(...)` - Simplified version with auto-detection

### Publishing

- `publish_analyses(...)` - Publish all outputs from specified analyses
- `publish_files(...)` - Publish specific output files
- `copy_if_changed(src, dst)` - Copy only if content differs
- `load_yml(path)` / `save_yml(path, obj)` - YAML utilities

## Command-Line Tools

### Create New Project

```bash
# Interactive scaffolding
repro-new-project

# Non-interactive with all languages
repro-new-project my-project --python --julia --stata

# Python-only project
repro-new-project my-project --python

# Custom configuration
repro-new-project my-project \
    --python --julia \
    --gpu \
    --studies "analysis1,analysis2"
```

Creates complete project structure with:
- Environment setup (Python, Julia, Stata)
- Example scripts for selected languages
- Makefile with build targets
- Git submodule for repro-tools
- Documentation and configuration

### Record Provenance

```bash
repro-record \
    --artifact my_analysis \
    --out-meta output/provenance/my_analysis.yml \
    --inputs data.csv \
    --outputs output/figure.pdf output/table.tex
```

### Publish Outputs

```bash
# Publish complete analyses
repro-publish analyses \
    --paper-root paper \
    --names "price_base remodel_base" \
    --require-current-head

# Publish specific files
repro-publish files \
    --paper-root paper \
    --files "output/figures/fig1.pdf output/tables/tab1.tex"
```

## Git Safety Checks

All publishing functions enforce configurable safety checks:

- **`allow_dirty`** (default: `False`) - Refuse to publish from dirty working tree
- **`require_not_behind`** (default: `True`) - Refuse if branch behind upstream
- **`require_current_head`** (default: `False`) - Require artifacts from current HEAD

## Provenance Format

Build records are stored as YAML:

```yaml
artifact: price_base
built_at_utc: '2026-01-18T05:30:00+00:00'
command: [python, build_price_base.py, --data, data.csv]
git:
  is_git_repo: true
  commit: cbb163e7a1b2c3d4...
  branch: main
  dirty: false
  ahead: 0
  behind: 0
inputs:
  - path: /path/to/data.csv
    sha256: 48917387ef250e...
    bytes: 325
    mtime: 1737179400.123
outputs:
  - path: /path/to/output/figure.pdf
    sha256: 3855687dcbeff3...
    bytes: 12482
    mtime: 1737179410.456
```

## Integration with Make

See `examples/makefile_integration/` for complete Makefile templates.

## Examples

See `examples/` directory:
- `basic_usage.py` - Simple build script with provenance
- `makefile_integration/` - Complete Make-based workflow
- `publishing_workflow/` - Two-mode publishing examples

## Development

```bash
# Set up environment (one command)
make env

# Run all tests (including slow Julia tests ~30-40 min)
make test

# Run fast tests only (skip Julia installation, ~2 min)
make test-fast

# Run only slow Julia installation tests
make test-slow

# Run tests with coverage
make coverage

# Format code
make format

# Type checking
make typecheck

# Run all checks (lint + test-fast)
make check
```

### Testing

The test suite includes:
- **Unit tests** (83 tests): Fast tests for core functionality
- **Integration tests** (13 tests): End-to-end workflow validation
  - **Fast** (9 tests, ~2 min): Python-only project generation and environment
  - **Slow** (4 tests, ~30-40 min): Julia installation and multi-language setup

Use pytest markers to run subsets:
```bash
# Fast tests only (recommended for CI)
pytest -v -m "not slow"

# Integration tests only
pytest -v -m integration

# All tests
pytest -v
```

See `tests/README.md` for detailed testing documentation.

## License

MIT License - See LICENSE file

## Contributing

This package is primarily for personal research and teaching. Feel free to use and adapt for your own projects.

## Citation

If you use this package in your research, please cite:

```bibtex
@software{stanton2026reprotools,
  title = {repro-tools: Reproducibility Tools for Research},
  author = {Stanton, Richard},
  year = {2026},
  url = {https://github.com/rhstanton/repro-tools}
}
```
