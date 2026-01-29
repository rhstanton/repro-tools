# repro-tools Quick Start

**5-minute guide to using repro-tools in your research project**

> **Starting a new project?** Clone [project_template](https://github.com/rhstanton/project_template) instead - it includes repro-tools pre-configured. This guide is for adding repro-tools to existing projects.

## Installation

```bash
pip install -e /home/stanton/01_work/infrastructure/40_lib/python/repro-tools
```

## Basic Usage

### 1. Track Provenance in Build Script

```python
#!/usr/bin/env python
from pathlib import Path
from repro_tools import auto_build_record

# ... your analysis code ...
# Creates output/figure.pdf and output/table.tex

# Record provenance at end of script
auto_build_record(
    out_meta=Path("output/provenance/my_analysis.yml"),
    inputs=[Path("data/input.csv")],
    outputs=[
        Path("output/figure.pdf"),
        Path("output/table.tex"),
    ],
)
```

### 2. Publish to Paper Directory

```python
from pathlib import Path
from repro_tools import publish_analyses

# Publish complete analyses
publish_analyses(
    project_root=Path("."),
    paper_root=Path("paper"),
    analysis_names=["my_analysis"],
    require_current_head=True,  # Strict mode
)
```

Or publish specific files:

```python
from repro_tools import publish_files

publish_files(
    project_root=Path("."),
    paper_root=Path("paper"),
    file_paths=[Path("output/figures/figure1.pdf")],
)
```

### 3. Command-Line Usage

```bash
# Record provenance
repro-record \
    --artifact my_analysis \
    --out-meta output/provenance/my_analysis.yml \
    --inputs data.csv \
    --outputs output/figure.pdf output/table.tex

# Publish
repro-publish analyses \
    --paper-root paper \
    --names "my_analysis" \
    --require-current-head
```

## Makefile Integration

```makefile
# Build with provenance
output/figures/%.pdf output/tables/%.tex output/provenance/%.yml: build_%.py data/*.csv
python $< \
--data $(DATA) \
--out-fig output/figures/$*.pdf \
--out-table output/tables/$*.tex \
--out-meta output/provenance/$*.yml

# Publish using repro-tools
publish:
repro-publish analyses \
--paper-root paper \
--names "$(ANALYSES)" \
--require-current-head
```

## What Gets Tracked

The provenance file captures:

- **Git state**: commit, branch, dirty status
- **Input files**: paths + SHA256 checksums
- **Output files**: paths + SHA256 checksums
- **Build command**: exact command that created outputs
- **Timestamp**: UTC time of build

## Git Safety Checks

All publishing enforces:

- ✅ Clean working tree (no uncommitted changes)
- ✅ Branch not behind upstream
- ✅ Optionally: artifacts from current HEAD

Override with `allow_dirty=True`, etc.

## Documentation

- Full API: See `README.md`
- Examples: See `examples/` directory
- Tests: Run `pytest` in package directory

## Next Steps

1. Add `repro-tools` to your project's `environment.yml`
2. Import functions in your build scripts
3. Run tests: `pytest`
4. See `examples/basic_usage.py` for complete example

**Location**: `/home/stanton/01_work/infrastructure/40_lib/python/repro-tools/`
