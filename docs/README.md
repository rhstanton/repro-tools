# repro-tools Package

Created: January 18, 2026  
Location: `/home/stanton/01_work/infrastructure/40_lib/python/repro-tools/`

## Overview

**repro-tools is a library package** that provides provenance tracking and publishing infrastructure for computational research. It contains **only library code** - no project creation or scaffolding.

**For creating new projects**: Use [project_template](https://github.com/rhstanton/project_template), which provides a complete reference implementation that uses repro-tools.

This library is suitable for:
- Adding reproducibility to existing research projects
- Teaching computational reproducibility
- Sharing infrastructure across multiple projects

## Package Structure

```
repro-tools/
├── src/repro_tools/
│   ├── __init__.py          # Package interface
│   ├── core.py              # Provenance tracking (git_state, write_build_record)
│   ├── publish.py           # Publishing (publish_analyses, publish_files)
│   └── cli.py               # Command-line tools
├── tests/
│   └── test_core.py         # pytest tests
├── examples/
│   └── basic_usage.py       # Example usage
├── docs/                    # Documentation
├── pyproject.toml           # Package metadata & dependencies
├── README.md                # User guide
└── LICENSE                  # MIT License
```

## Installation

### Editable Install (Development/Teaching)

```bash
pip install -e /home/stanton/01_work/infrastructure/40_lib/python/repro-tools
```

Or add to conda `environment.yml`:

```yaml
dependencies:
  - pip:
    - -e /home/stanton/01_work/infrastructure/40_lib/python/repro-tools
```

Changes to the package propagate immediately to all projects using it.

### Regular Install (Future)

When published to PyPI:

```bash
pip install repro-tools
```

## Usage

### In Python Scripts

```python
from repro_tools import auto_build_record

auto_build_record(
    out_meta=Path("output/provenance/my_analysis.yml"),
    inputs=[Path("data.csv")],
    outputs=[Path("output/figure.pdf"), Path("output/table.tex")],
)
```

### Command Line

```bash
# Record provenance
repro-record \
    --artifact my_analysis \
    --out-meta output/provenance/my_analysis.yml \
    --inputs data.csv \
    --outputs output/figure.pdf output/table.tex

# Publish analyses (names are positional; --project-root is required)
repro-publish analyses price_base remodel_base \
    --paper-root paper \
    --project-root . \
    --require-current-head 1

# Publish specific files (also positional)
repro-publish files output/figures/fig1.pdf \
    --paper-root paper \
    --project-root .
```

## Migration from project_template

To use this package in `project_template`:

1. **Update `env/python.yml`**:
   ```yaml
   dependencies:
     - pip:
       - -e /home/stanton/01_work/infrastructure/40_lib/python/repro-tools
   ```

2. **Update imports in build scripts**:
   ```python
   # OLD:
   from scripts.provenance import auto_build_record
   
   # NEW:
   from repro_tools import auto_build_record
   ```

3. **Update Makefile publishing**:
   - Replace `scripts/publish_artifacts.py` with direct `repro-publish` calls
   - Or keep wrapper scripts that import from `repro_tools.publish`

4. **Benefits**:
   - Single source of truth for all projects
   - Easy to update (changes propagate automatically)
   - Simpler for teaching (just `pip install repro-tools`)
   - Can eventually publish to PyPI

## Comparison with housing-analysis

Unlike `housing-analysis/Makefile` which was project-specific:
- `repro-tools` is general-purpose infrastructure
- No project-specific configurations
- Minimal dependencies (just PyYAML)
- Suitable for teaching and sharing

## Testing

```bash
cd /home/stanton/01_work/infrastructure/40_lib/python/repro-tools
pytest
```

## Documentation

See `README.md` for complete API documentation and examples.

## Version History

- **0.1.0** (2026-01-18): Initial extraction from project_template
  - Core provenance tracking
  - Two-mode publishing system
  - Command-line tools
  - Full test suite

## Next Steps

1. Finish migration of `project_template` to use package
2. Test with multiple research projects
3. Add more examples
4. Consider publishing to PyPI
