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
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=repro_tools --cov-report=html

# Format code
black src/ tests/

# Type checking
mypy src/
```

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
