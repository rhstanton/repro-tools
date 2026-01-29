# Copilot Instructions: repro-tools Package

## Project Overview

**repro-tools** is a lightweight Python package providing reproducibility infrastructure for computational research projects. It handles provenance tracking, publishing workflows, and quality assurance checks.

This package is **teaching-friendly** with a simple API, clear documentation, and minimal dependencies. It's designed to be used across multiple research projects without modification.

---

## Package Architecture

### Directory Structure

```
repro-tools/
├── src/
│   └── repro_tools/
│       ├── __init__.py           # Public API exports
│       ├── core.py               # Provenance tracking core
│       ├── publish.py            # Publishing workflows
│       ├── cli.py                # Command-line interface
│       ├── compare.py            # Output comparison
│       ├── sysinfo.py            # System info logging
│       ├── presubmit.py          # Pre-submission checks
│       └── report.py             # Replication report generation
├── tests/
│   └── test_core.py              # Unit tests
├── examples/
│   └── basic_usage.py            # Simple usage example
├── docs/
│   ├── README.md                 # Detailed documentation
│   └── MIGRATION.md              # Migration guide for old code
├── pyproject.toml                # Package metadata (modern)
├── README.md                     # Quick start guide
└── QUICKSTART.md                 # 5-minute tutorial
```

### Module Responsibilities

#### `core.py` - Provenance Tracking Core

**Purpose**: Capture build metadata (git state, checksums, timestamps)

**Key Functions**:
- `git_state(repo_root)` - Capture git commit, branch, dirty status, ahead/behind
- `sha256_file(path)` - Compute SHA256 checksum
- `write_build_record(...)` - Write YAML provenance record
- `auto_build_record(...)` - Simplified API with auto-detection
- `enable_auto_provenance(__file__)` - Automatic provenance at script exit
- `auto_provenance_from_config(...)` - Config file-based automation

**Output Format**: YAML files with structure:
```yaml
artifact: my_analysis
built_at_utc: '2026-01-18T12:00:00+00:00'
command: [python, build_my_analysis.py, --data, data.csv]
git:
  is_git_repo: true
  commit: abc123...
  branch: main
  dirty: false
  ahead: 0
  behind: 0
inputs:
  - path: /path/to/data.csv
    sha256: 48917387...
    bytes: 325
    mtime: 1768622679.5
outputs:
  - path: /path/to/output/figure.pdf
    sha256: 3855687d...
    bytes: 12482
    mtime: 1768622689.4
```

#### `publish.py` - Publishing Workflows

**Purpose**: Copy outputs from build directory to publication directory with provenance aggregation

**Two Publishing Modes**:

1. **Analysis-based** (`publish_analyses`):
   - Publishes ALL outputs from specified analyses
   - Groups by analysis name (e.g., "price_base" → figures/price_base.pdf, tables/price_base.tex)
   - Use when: Publishing complete analyses to paper

2. **File-based** (`publish_files`):
   - Publishes specific files regardless of analysis
   - Fine-grained control (e.g., 2 figures from analysis that generated 5)
   - Use when: Selective inclusion in final paper

**Key Functions**:
- `publish_analyses(...)` - Analysis-based publishing
- `publish_files(...)` - File-based publishing
- `copy_if_changed(src, dst)` - Copy only if SHA256 differs
- `load_yml(path)` / `save_yml(path, obj)` - YAML utilities

**Git Safety Checks** (configurable):
- `allow_dirty` (default: False) - Refuse dirty working tree
- `require_not_behind` (default: True) - Refuse if behind upstream
- `require_current_head` (default: False) - Require artifacts from current commit

**Output**: Updates `paper/provenance.yml` with:
```yaml
paper_provenance_version: 1
last_updated_utc: '2026-01-18T12:00:00+00:00'
analysis_git:
  commit: abc123...
  branch: main
  dirty: false
artifacts:
  price_base:
    figures:
      published_at_utc: '2026-01-18T12:00:00+00:00'
      copied: true
      src: /path/to/output/figures/price_base.pdf
      dst: /path/to/paper/figures/price_base.pdf
      dst_sha256: 3855687d...
      build_record:
        # Full build provenance embedded here
```

#### `cli.py` - Command-Line Interface

**Purpose**: Provide CLI access to all functionality

**Commands**:
- `repro-record` - Record provenance from command line
- `repro-publish` - Publish analyses or files
- `repro-compare` - Compare current vs. published outputs
- `repro-sysinfo` - Log system information
- `repro-check` - Pre-submission checks and git state validation
- `repro-report` - Generate replication reports

**Design Philosophy**: CLI mirrors Python API (same arguments, same behavior)

#### `compare.py` - Output Comparison

**Purpose**: Compare current build outputs vs. published artifacts

**Functionality**:
- Shows which files differ (SHA256 comparison)
- Line-by-line diff for text files (tables)
- Checksum comparison for binary files (figures)

#### `sysinfo.py` - System Information

**Purpose**: Log computational environment for reproducibility

**Captured Information**:
- OS, Python version, package versions
- Julia version (if installed)
- Git state of repository
- Hardware info (optional)

#### `presubmit.py` - Pre-Submission Checks

**Purpose**: Comprehensive validation before journal submission

**Checks**:
- Git state (clean, not behind)
- Data checksums match expected
- All analyses have provenance
- Documentation complete
- No uncommitted changes

**Modes**:
- Normal: Warns on issues
- Strict: Fails on any warning

#### `report.py` - Replication Reports

**Purpose**: Generate HTML reports for reviewers/replicators

**Includes**:
- System information
- Provenance records
- Verification commands
- Expected outputs checklist

---

## Public API Design

### Two-Level API

**Level 1: Config-Based (Recommended for Projects)**
```python
from repro_tools import enable_auto_provenance

# Enable at top of script
enable_auto_provenance(__file__)

# Requires config.py with ANALYSES dictionary:
# ANALYSES = {
#     "my_analysis": {
#         "inputs": [Path("data.csv")],
#         "outputs": {
#             "figure": Path("output/figures/my_analysis.pdf"),
#             "table": Path("output/tables/my_analysis.tex"),
#             "provenance": Path("output/provenance/my_analysis.yml"),
#         }
#     }
# }

# Benefits:
# - Central configuration for all analyses
# - Works with command-line args (flexible inputs/outputs)
# - Provenance auto-recorded at exit with actual command used
# - No manual calls needed
```

**Level 2: Explicit (Recommended for Standalone Scripts)**
```python
from repro_tools import auto_build_record

# At end of script, call explicitly
auto_build_record(
    out_meta=Path("output/provenance/my_analysis.yml"),
    inputs=[Path("data.csv")],
    outputs=[Path("output/fig.pdf"), Path("output/table.tex")]
)
# Auto-detects: artifact name, repo root, command
# No config.py needed
```

**When to use each:**
- **Config-based**: Multi-analysis projects with Makefile orchestration
- **Explicit**: Standalone scripts, notebooks, one-off analyses

### Key Design Principles

1. **Two Modes for Two Use Cases**: Config-based for projects, explicit for scripts
2. **Central Configuration**: Config.py defines all analyses in one place (project mode)
3. **Flexible Execution**: Scripts can take command-line args, provenance captures actual usage
4. **Teaching-Friendly**: Clear names, obvious behavior, helpful error messages
5. **Minimal Dependencies**: Only stdlib + PyYAML

---

## Integration Patterns

### How Projects Use repro-tools

**Installation** (in project's `env/python.yml`):
```yaml
dependencies:
  - pip:
    # Editable install (development)
    - -e /path/to/repro-tools
    # OR from PyPI (when published)
    # - repro-tools>=0.2.0
```

**In Analysis Scripts** (`build_*.py`):
```python
from repro_tools import enable_auto_provenance

enable_auto_provenance(__file__)

def main():
    # Analysis code here
    pass

if __name__ == "__main__":
    main()
```

**In Makefiles**:
```makefile
# Define CLI command variables
PYTHON := env/scripts/runpython

# Publishing target
publish:
	@$(PYTHON) -m repro_tools.cli publish analyses $(PUBLISH_ANALYSES) \
		--paper-root paper --project-root . \
		--allow-dirty 0 --require-not-behind 1 --require-current-head 0
```

**Why `$(PYTHON) -m repro_tools.cli` not direct CLI?**
- ✅ Works regardless of PATH configuration
- ✅ Uses same Python environment as project
- ✅ No need to activate virtualenv before make
- ✅ More portable across setups

---

## Development Workflow

### Adding New Features

**Checklist**:
1. Add function to appropriate module (`core.py`, `publish.py`, etc.)
2. Export in `__init__.py` if public API
3. Add CLI command in `cli.py` if appropriate
4. Write unit test in `tests/test_*.py`
5. Update `README.md` with example
6. Update `QUICKSTART.md` if beginner-facing
7. Update version in `pyproject.toml`

**Example**: Adding new comparison feature

```python
# 1. Add to compare.py
def compare_figures_visually(current_dir, reference_dir):
    """Compare figures pixel-by-pixel."""
    # Implementation here
    pass

# 2. Export in __init__.py
from repro_tools.compare import compare_figures_visually

# 3. Add CLI command in cli.py
@cli.command()
def compare_visual(...):
    from repro_tools import compare_figures_visually
    compare_figures_visually(...)

# 4. Add test
def test_compare_figures_visually():
    # Test implementation
    pass
```

### Testing Strategy

**Unit Tests** (`tests/test_core.py`):
- Test each function in isolation
- Mock git commands for reproducibility
- Test edge cases (missing files, corrupt YAML, etc.)

**Integration Tests** (in consuming projects):
- Test full workflow (build → publish → verify)
- Test Makefile integration
- Test with real git repositories

**Manual Testing**:
- Run example scripts in `examples/`
- Test CLI commands manually
- Verify output formats

### Code Style

**Python Version**: 3.9+ (uses `from __future__ import annotations` for compatibility)

**Type Hints**: Use extensively
```python
def git_state(repo_root: Path) -> Dict[str, Any]:
    """Capture git repository state."""
    ...
```

**Imports**: Use `from __future__ import annotations` for forward references

**Docstrings**: Google style
```python
def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute SHA256 checksum of a file.
    
    Args:
        path: Path to file
        chunk_size: Bytes to read at once (default 1MB)
        
    Returns:
        Hexadecimal SHA256 digest
    """
```

**Error Handling**: Explicit, informative messages
```python
if not path.exists():
    raise FileNotFoundError(f"Input file not found: {path}")
```

---

## Common Workflows

### Scenario 1: User Wants to Track Provenance

**Step 1**: Install repro-tools in their environment
**Step 2**: Add two lines to their script:
```python
from repro_tools import enable_auto_provenance
enable_auto_provenance(__file__)
```
**Step 3**: Run script normally - provenance recorded automatically

### Scenario 2: User Wants to Publish Outputs

**Step 1**: Build analyses (provenance auto-recorded)
**Step 2**: Add Makefile targets using `$(PYTHON) -m repro_tools.cli publish`
**Step 3**: Run `make publish`

### Scenario 3: User Migrating from Old Code

**See `docs/MIGRATION.md` for step-by-step guide**

Old code (inline):
```python
from scripts.provenance import write_build_record
write_build_record(...)
```

New code (package):
```python
from repro_tools import enable_auto_provenance
enable_auto_provenance(__file__)
```

---

## Design Decisions

### Why Automatic Provenance?

**Problem**: Users forget to call `write_build_record()`

**Solution**: `enable_auto_provenance(__file__)` registers atexit handler

**Benefits**:
- ✅ Impossible to forget
- ✅ Works even if script raises exception
- ✅ No changes to existing code structure

**Tradeoffs**:
- ⚠️ Uses global state (`atexit`)
- ⚠️ Less explicit than manual calls
- ✅ But: massive convenience gain for 99% of use cases

### Why Two Publishing Modes?

**Analysis-based**: Natural for papers where each analysis → one figure/table

**File-based**: Needed when:
- Analysis generates 5 figures, paper uses 2
- Supplementary materials in different directories
- Aggregated tables combining multiple analyses

**Alternative considered**: One unified mode
**Rejected because**: Use cases too different, would complicate API

### Why YAML not JSON?

**Advantages**:
- ✅ Comments allowed (useful for manual edits)
- ✅ More readable for humans
- ✅ Standard in research workflows
- ✅ Git-friendly (meaningful diffs)

**Disadvantages**:
- ⚠️ Requires PyYAML dependency
- ✅ But: PyYAML is ubiquitous, stable, lightweight

### Why CLI via `python -m repro_tools.cli`?

**Problem**: Direct CLI commands (`repro-publish`) require:
- Installing scripts to PATH
- Activated virtualenv
- Platform-specific setup

**Solution**: Module invocation works anywhere Python works

**Benefits**:
- ✅ No PATH configuration needed
- ✅ Works in Makefiles without activation
- ✅ Consistent with how projects run Python code
- ✅ Same Python interpreter as rest of project

---

## Extension Points

### Adding New CLI Commands

Pattern:
```python
# In cli.py
@cli.command()
@click.option("--arg1", help="Description")
def new_command(arg1):
    """Command description."""
    from repro_tools.new_module import new_function
    new_function(arg1)
```

### Adding New Provenance Fields

Add to `write_build_record()` return dictionary:
```python
def write_build_record(...):
    obj = {
        "artifact": artifact_name,
        "built_at_utc": now_utc_iso(),
        # Add new field:
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
        },
        ...
    }
```

**Important**: Update version in `paper_provenance_version` if schema changes

### Supporting New Output Types

Currently: figures (PDF) and tables (TEX)

To add (e.g., data files):
```python
# In publish.py
def publish_analyses(..., kinds=["figures", "tables", "data"]):
    for kind in kinds:
        # Publish files from output/{kind}/ to paper/{kind}/
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'repro_tools'"

**Cause**: Package not installed

**Solution**: Add to `env/python.yml` and run `make environment`

### "Provenance file not found"

**Cause**: Script didn't call `enable_auto_provenance()` or `write_build_record()`

**Solution**: Add provenance recording to script

### "Git state shows dirty: true"

**Cause**: Uncommitted changes in working tree

**Solution**: Commit changes before building:
```bash
git status
git add .
git commit -m "Description"
```

### "Publishing refuses: artifacts not from current HEAD"

**Cause**: Using `require_current_head=True` but artifacts stale

**Solution**: Rebuild from clean state:
```bash
make clean
make all
make publish
```

---

## Best Practices for Contributors

### Code Organization

**Do**:
- ✅ Keep modules focused (core.py = provenance, publish.py = publishing)
- ✅ Use type hints for all public functions
- ✅ Write docstrings for public API
- ✅ Add unit tests for new features

**Don't**:
- ❌ Add dependencies without strong justification
- ❌ Break backward compatibility without major version bump
- ❌ Add teaching-unfriendly complexity
- ❌ Duplicate functionality across modules

### Documentation

**Every new feature needs**:
1. Docstring in code
2. Example in README.md
3. CLI help text (if CLI command)
4. Unit test demonstrating usage
5. Update to CHANGELOG (if releasing)

### Versioning

**Semantic Versioning** (MAJOR.MINOR.PATCH):
- MAJOR: Backward-incompatible changes
- MINOR: New features, backward-compatible
- PATCH: Bug fixes

**Current**: v0.2.0 (pre-1.0, API may change)

### Release Checklist

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run tests: `pytest tests/`
4. Build: `python -m build`
5. Test install: `pip install dist/repro_tools-X.Y.Z.tar.gz`
6. Tag release: `git tag v0.2.0`
7. (Future) Upload to PyPI: `twine upload dist/*`

---

## Future Enhancements

### Under Consideration

1. **Config file support**: Read analysis definitions from `config.py`
2. **Web dashboard**: Interactive provenance browser
3. **Cloud storage integration**: Publish to S3/GCS/Dataverse
4. **Docker integration**: Generate Dockerfile from environment
5. **Notebook support**: Jupyter notebook provenance
6. **Incremental builds**: Only rebuild changed analyses
7. **Parallel builds**: Run independent analyses concurrently

### Explicitly Deferred

- **GUI**: Keep CLI-focused for teaching
- **Database backend**: YAML files sufficient for research scale
- **Plugin system**: Avoid complexity until proven need

---

## Quick Reference

### Most Common User Patterns

**In analysis script**:
```python
from repro_tools import enable_auto_provenance
enable_auto_provenance(__file__)
```

**In Makefile**:
```makefile
REPRO_PUBLISH := $(PYTHON) -m repro_tools.cli publish
publish:
	@$(REPRO_PUBLISH) --paper-root paper --analyses "$(ANALYSES)"
```

### Most Common Development Tasks

**Add new function**:
1. Write in appropriate module
2. Add to `__init__.py`
3. Write test
4. Update README.md

**Fix bug**:
1. Write failing test
2. Fix code
3. Verify test passes
4. Update CHANGELOG

**Release**:
1. Update version in pyproject.toml
2. Update CHANGELOG.md
3. Commit, tag, push

---

## Contact & Contribution

**Maintainer**: Research Infrastructure Team

**Contributing**: See individual project repositories for contribution guidelines

**License**: MIT (permissive, teaching-friendly)

---

**Last Updated**: January 18, 2026  
**Package Version**: 0.2.0  
**Python Version**: 3.9+
