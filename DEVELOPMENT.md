# Development Setup

## Quick Start

**One command to set everything up:**
```bash
make env
```

This creates a conda environment named `repro-tools-dev` and installs the package in editable mode.

**Run tests:**
```bash
make test       # Verbose output
make test-q     # Quiet output
```

## Manual Setup (without Makefile)

```bash
# Create conda environment in .env/
conda env create --prefix .env -f environment.yml

# Activate it
conda activate ./.env

# Install package in editable mode
pip install -e .

# Run tests
pytest tests/ -v
```

## Daily Workflow

**Activate environment:**
```bash
conda activate ./.env
```

**Run tests after changes:**
```bash
make test-q
```

**Deactivate when done:**
```bash
conda deactivate
```

## Available Make Targets

- `make help` - Show all available targets
- `make env` - Create conda environment and install package (one step!)
- `make test` - Run all tests (verbose)
- `make test-q` - Run all tests (quiet)
- `make clean` - Remove environment and build artifacts

## Notes

- Conda environment is in `.env/` directory (gitignored)
- Package is installed in **editable mode** (`-e`) so code changes take effect immediately
- Dependencies managed via conda (see `environment.yml`)
- Python 3.9+ required

## Using the Package from Other Projects

Other projects can install repro-tools in editable mode from this directory:

```yaml
# In their environment.yml:
dependencies:
  - pip:
    - -e /path/to/repro-tools
```

This way, changes to repro-tools are immediately available in consuming projects.
