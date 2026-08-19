# Quick Start Guide - {name}

## TL;DR - Copy-Paste Commands

```bash
# 1. Setup environment (~10 minutes)
make environment

# 2. Verify setup
make verify

# 3. Run all analyses
make all

# 4. Publish to paper/
make publish
```

## What Just Happened?

### `make environment`

Installed:
- Python environment (`.venv/`, built by uv)
- Julia packages (`.julia/` directory, if enabled)
- Git submodules (repro-tools)

### `make verify`

Checked:
- Python environment
- Key packages (pandas, matplotlib, etc.)
- Data availability

### `make all`

Ran all analyses and generated:
- `output/figures/*.pdf` - Figures
- `output/tables/*.tex` - Tables
- `output/provenance/*.yml` - Build metadata

### `make publish`

Copied artifacts to `paper/` directory with provenance tracking.

## Next Steps

1. **Customize configurations**: Edit `shared/config.py`
2. **Add your data**: Place files in `data/`
3. **Modify analysis**: Edit `run_analysis.py`
4. **Build specific analysis**: `make sample_analysis`

## Common Commands

```bash
make help             # Show all commands
make clean            # Remove outputs
make list-analyses    # List available analyses
make test             # Run test suite
```

## Troubleshooting

**ImportError**: Run `make environment` first

**Build errors**: Check `output/logs/*.log`

**Need help?**: Run `make help`
