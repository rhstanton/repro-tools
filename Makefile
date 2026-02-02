# Simple Makefile for repro-tools development

ENV_DIR := .env
CONDA := conda

# Detect if we're in CI (no conda) or local dev (with conda)
ifeq ($(CI),true)
	# CI mode: use direct commands (packages installed via pip)
	PYTHON := python
	RUN_CMD :=
else
	# Local dev mode: use conda run
	PYTHON := python
	RUN_CMD := $(CONDA) run --prefix $(ENV_DIR)
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

# Create conda environment in .env/ and install package in editable mode
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
	@$(RUN_CMD) ruff format --check src/ tests/
	@echo "Format check complete!"

# Run type checker
typecheck type-check:
	@echo "Running mypy type checker..."
	@$(RUN_CMD) mypy src/repro_tools
	@echo "Type checking complete!"

# Run linter
lint:
	@echo "Running ruff linter..."
	@$(RUN_CMD) ruff check src/ tests/
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
