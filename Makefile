# Simple Makefile for repro-tools development

# How every target invokes Python. Detected, not assumed.
#
# This used to branch on $(CI): plain commands in CI, `conda run --prefix .env`
# locally. Both halves were wrong after the move to uv. There is no .env here --
# there is a .venv -- so every local `make test`, `make lint` and `make check`
# died with "EnvironmentLocationNotFound: Not a conda environment", and the way
# people carried on working was to type the underlying ruff and pytest commands
# by hand, with their own path lists.
#
# That is how CI stayed red for a day while local runs passed: the two were never
# running the same thing. `make lint` failing to START is a worse failure than
# `make lint` reporting an error, because it trains everyone to bypass it.
#
# Detect the interpreter instead. A .venv is used when present; otherwise the
# tools are expected on PATH, which is what CI does after pip-installing them.
# `uv run` when uv is available, because it guarantees the DECLARED dev
# dependencies -- a bare .venv can be missing ruff entirely, which is how
# `make lint` came to fail with "No module named ruff" while `make test` worked.
# Otherwise the tools are expected on PATH, which is what CI has after
# `pip install -e '.[dev]'`.
UV := $(shell command -v uv 2>/dev/null)
ifeq ($(UV),)
	PYTHON := python3
	RUN_CMD :=
else
	PYTHON := uv run python
	RUN_CMD := uv run
endif

.PHONY: help all env test clean lint format typecheck check coverage format-check

help:
	@echo "Available targets:"
	@echo "  make help      - Show this help message (default)"
	@echo "  make all       - Set up environment and run tests"
	@echo "  make env       - Create/update conda environment and install package"
	@echo "  make test      - Run all tests (including slow Julia tests)"
	@echo "  make test-fast - Run only fast tests (skip Julia installation)"
	@echo "  make test-slow - Run only slow tests (Julia installation)"
	@echo "  make test-q    - Run tests (quiet)"
	@echo "  make coverage  - Run tests with coverage report"
	@echo "  make lint      - Run all linters (black check + mypy)"
	@echo "  make format    - Format code with black"
	@echo "  make typecheck - Run mypy type checker"
	@echo "  make check     - Run all checks (lint + test)"
	@echo "  make clean     - Remove environment and build artifacts"

# Set up and test
all: env test

# Create the environment and install the package in editable mode
env:
	@echo "Setting up conda environment in $(ENV_DIR)/..."
	@if [ ! -d "$(ENV_DIR)" ]; then \
		$(CONDA) env create --prefix $(ENV_DIR) -f environment.yml; \
	else \
		echo "Environment already exists in $(ENV_DIR)/"; \
	fi
	@echo "Installing repro-tools in editable mode..."
	$(CONDA) run --prefix $(ENV_DIR) pip install -e .
	@echo ""
	@echo "Setup complete! To use:"
	@echo "  conda activate ./$(ENV_DIR)"
	@echo "Or run tests directly:"
	@echo "  make test"

# Run tests
test:
	@$(RUN_CMD) pytest tests/ -v

# Run only fast tests (skip Julia installation tests)
test-fast:
	@echo "Running fast tests (skipping Julia installation)..."
	@$(RUN_CMD) pytest tests/ -v -m "not slow"

# Run only slow tests (Julia installation)
test-slow:
	@echo "Running slow tests (Julia installation ~5-10 min)..."
	@$(RUN_CMD) pytest tests/ -v -m "slow"

# Quick test (quiet mode)
test-q:
	@$(RUN_CMD) pytest tests/ -q

# Run tests with coverage report
coverage:
	@$(RUN_CMD) pytest tests/ -v --cov=repro_tools --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

# Format code with ruff
format:
	@echo "Formatting code with ruff..."
	@$(RUN_CMD) ruff format src/ tests/
	@echo "Code formatted!"

# Check formatting without modifying
format-check:
	@echo "Checking code formatting with ruff..."
	@$(RUN_CMD) ruff format --check $(LINT_PATHS)
	@echo "Format check complete!"

# Run type checker
typecheck type-check:
	@echo "Running mypy type checker..."
	@$(RUN_CMD) mypy src/repro_tools
	@echo "Type checking complete!"

# LINT_PATHS is the single definition of scope, used by lint, format and
# format-check alike, so the three cannot disagree about what they cover.
#
# It listed project_template/ until 2026-08-19, when that directory was deleted
# as a dead duplicate of the real template repo — and ruff then failed with
# "E902 No such file or directory", which is a lint error about a path, not about
# code. CI went red on every commit for the next day while local runs passed,
# because the local runs were typing their own path list rather than using this
# one. What CI runs and what you can run must be the SAME STRING.
LINT_PATHS ?= src/ tests/ examples/

# Run linter
lint:
	@echo "Running ruff linter..."
	@$(RUN_CMD) ruff check $(LINT_PATHS)
	@echo "Linting complete!"

# Run all checks (lint + format-check + type-check)
check: lint format-check type-check
	@echo ""
	@echo "All checks passed!"

# Clean build artifacts and environment
clean:
	rm -rf $(ENV_DIR)
	rm -rf build/
	rm -rf dist/
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	@echo "Cleaned environment and build artifacts"
