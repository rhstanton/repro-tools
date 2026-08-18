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
# Publish complete analyses (names are positional, not --names)
repro-publish analyses price_base remodel_base \
    --paper-root paper \
    --project-root . \
    --require-current-head 1

# Restrict to one kind of artifact (repeatable; default is all kinds)
repro-publish analyses price_base \
    --paper-root paper \
    --project-root . \
    --kind figures

# Publish specific files (also positional)
repro-publish files output/figures/fig1.pdf output/tables/tab1.tex \
    --paper-root paper \
    --project-root .

# The same commands, run as a module so the interpreter is the project's own
# .venv rather than whatever `repro-publish` is first on PATH. This is the form
# Makefiles should use:
python -m repro_tools.cli publish analyses price_base --paper-root paper --project-root .
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
built_at_utc: '2026-08-18T05:30:00+00:00'
command: [python, build_price_base.py, --data, data.csv]
repo_root: /home/you/projects/housing
path_convention: relative-to-repo-root-where-possible
git:
  is_git_repo: true
  commit: cbb163e7a1b2c3d4...
  branch: main
  dirty: false
  untracked_count: 0
  untracked: []
  untracked_truncated: false
  upstream: origin/main
  ahead: 0
  behind: 0
inputs:
  - path: data/data.csv
    sha256: 48917387ef250e...
    bytes: 325
outputs:
  - path: output/figures/figure.pdf
    sha256: 3855687dcbeff3...
    bytes: 12482
```

### Field notes

**`path`** is relative to `repo_root`, which is recorded once. A file outside
the repository — data on another volume, say — cannot be made relative and is
recorded absolute; that is information rather than a failure, since it tells a
replicator the build depended on something the repository does not contain.

Paths were absolute before 2026-08-18. That meant records could not be compared
across machines (every path differed, so diffing two byte-identical builds was
pure noise), and because `paper/provenance.yml` is committed to the paper
repository and can accompany a submission, it published the author's home
directory. `resolve_recorded_path(entry, record)` reads both conventions, so
older records keep working.

**`mtime` is not recorded.** It changes on every checkout and every file copy,
so it made two identical builds produce different records while saying nothing
about content that `sha256` does not say better. Records that differ for
reasons unrelated to their subject do not get compared, and a record nobody
compares is decoration.

**`dirty` means tracked content differs from HEAD** — staged or unstaged.
Untracked files do **not** set it. They are reported separately in
`untracked_count` / `untracked` instead.

That split is deliberate. `dirty` is what publishing gates on, and a gate that
fires constantly gets switched off; `ALLOW_DIRTY=1` in a CI config disables it
permanently and silently. But an untracked script is a perfectly good candidate
for whatever produced the artifact being described, so a record calling such a
tree clean is being generous about something it never looked at. The numbers in
one submitted paper turned out to come from code that predated its repository's
first commit — untracked work, published results. Reporting it without gating on
it keeps the record honest and the gate usable; a consumer wanting the strict
meaning reads `untracked_count`.

Gitignored files are not untracked, so a project that ignores its outputs sees
an empty list. The listing is capped at `core.UNTRACKED_LIMIT` (50) with
`untracked_truncated` set; `untracked_count` is always exact.

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

# Run tests
make test

# Run tests with coverage
make coverage

# Format code
make format

# Type checking
make typecheck

# Run all checks (lint + test)
make check
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
