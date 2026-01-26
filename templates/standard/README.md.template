# {name}

Reproducible research project with provenance tracking.

## Quick Start

```bash
# 1. Setup environment (~10 minutes)
make environment

# 2. Run all analyses
make all

# 3. Publish results
make publish
```

## Project Structure

- `data/` - Input datasets
- `run_analysis.py` - Main analysis script
- `shared/config.py` - Study configurations
- `output/` - Build outputs (figures, tables, provenance)
- `paper/` - Published artifacts
- `env/` - Environment specifications

## Documentation

- `QUICKSTART.md` - 5-minute getting started guide
- `Makefile` - See `make help` for all commands

## Workflows

### Build All Analyses

```bash
make all
```

### Build Specific Analysis

```bash
make sample_analysis
```

### Verify Environment

```bash
make verify
```

### Publishing

```bash
make publish                              # Publish all
make publish PUBLISH_ANALYSES="sample_analysis"  # Publish specific
```

## Adding New Analyses

1. Add study configuration to `shared/config.py`:

```python
STUDIES = {{
    "my_analysis": {{
        "data": DATA_FILES["sample"],
        "xlabel": "X",
        "ylabel": "Y",
        # ... other parameters
    }},
}}
```

2. Add to Makefile `ANALYSES` variable:

```makefile
ANALYSES := sample_analysis my_analysis
```

3. Add analysis definition in Makefile:

```makefile
my_analysis.script  := run_analysis.py
my_analysis.runner  := $(PYTHON)
my_analysis.inputs  := $(DATA)
my_analysis.outputs := $(OUT_FIG_DIR)/my_analysis.pdf $(OUT_TBL_DIR)/my_analysis.tex $(OUT_PROV_DIR)/my_analysis.yml
my_analysis.args    := my_analysis
```

4. Build:

```bash
make my_analysis
```

## System Requirements

- Python 3.11
- GNU Make 4.3+
- Git

## License

See LICENSE file.
