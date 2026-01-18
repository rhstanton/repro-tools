# Simple Makefile for repro-tools development

ENV_DIR := .env
CONDA := conda

.PHONY: help all env test clean

help:
	@echo "Available targets:"
	@echo "  make help   - Show this help message (default)"
	@echo "  make all    - Set up environment and run tests"
	@echo "  make env    - Create/update conda environment and install package"
	@echo "  make test   - Run all tests"
	@echo "  make test-q - Run tests (quiet)"
	@echo "  make clean  - Remove environment and build artifacts"

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
	@$(CONDA) run --prefix $(ENV_DIR) pytest tests/ -v

# Quick test (quiet mode)
test-q:
	@$(CONDA) run --prefix $(ENV_DIR) pytest tests/ -q

# Clean build artifacts and environment
clean:
	rm -rf $(ENV_DIR)
	rm -rf build/
	rm -rf dist/
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	@echo "Cleaned environment and build artifacts"
