# ============================================================================
# Developer tooling
# ============================================================================
#
# Targets that need nothing from the project but $(PYTHON).\n#\n# Linting, formatting, type-checking and the test runners. A consumer that\n# can name its interpreter can include this file and get all of it.
#
# Split out of common.mk on 2026-08-19. Include this file directly, or get
# all four by including common.mk.

.PHONY: system-info
system-info:
	@echo "Logging computational environment..."
	@$(REPRO_SYSINFO) --output output/system_info.yml \
	  --repo-root $(REPO_ROOT)
	@echo ""
	@echo "System information saved to output/system_info.yml"
	@echo "This file contains OS, Python, Julia versions and package lists."
	@echo ""

# The iteration loop. `make test` runs everything and takes minutes, because a
# handful of tests launch a full analysis as a subprocess and pay Julia's
# startup each time -- in project_template, five such tests were 355 of the
# suite's 400 seconds while the other 362 took 45.
#
# A suite that takes seven minutes does not get run between edits; one that
# takes one does. CI runs `test`, so nothing is skipped where it matters.
.PHONY: test-fast
test-fast:
	@echo "Running fast tests (deselecting -m slow)..."
	@$(PYTHON) -m pytest tests/ -q -m "not slow"
	@echo ""
	@echo "✓ Fast tests complete -- run 'make test' for the full suite"
	@echo ""

.PHONY: test
test:
	@echo "Running test suite..."
	@$(PYTHON) -m pytest tests/ -v
	@echo ""
	@echo "✓ Tests complete"
	@echo ""

.PHONY: test-cov
test-cov:
	@echo "Running tests with coverage..."
	@$(PYTHON) -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term
	@echo ""
	@echo "Coverage report: htmlcov/index.html"
	@echo ""

# Code Quality

.PHONY: lint
lint:
	@echo "Running linter (ruff)..."
	@$(PYTHON) -m ruff check . --exclude 'lib/repro-tools' || { \
		echo ""; \
		echo "Linting failed. To see details:"; \
		echo "  $(PYTHON) -m ruff check ."; \
		echo ""; \
		echo "To auto-fix some issues:"; \
		echo "  make format"; \
		exit 1; \
	}
	@echo "✓ Linting passed"

.PHONY: format
format:
	@echo "Auto-formatting code..."
	@echo "  1. Running ruff fixes (import sorting, trailing whitespace, etc.)..."
	@$(PYTHON) -m ruff check --fix . --exclude 'lib/repro-tools' || true
	@echo "  2. Running ruff format..."
	@$(PYTHON) -m ruff format . --exclude 'lib/repro-tools' || true
	@echo ""
	@echo "✓ Formatting complete"

.PHONY: format-check
format-check:
	@echo "Checking code formatting..."
	@$(PYTHON) -m ruff format --check . --exclude 'lib/repro-tools' || { \
		echo ""; \
		echo "Ruff formatting check failed. Run:"; \
		echo "  make format"; \
		exit 1; \
	}
	@echo ""
	@echo "✓ Formatting check passed"

.PHONY: type-check
type-check:
	@echo "Running type checker (mypy)..."
	@$(PYTHON) -m mypy run_analysis.py shared/*.py --exclude 'lib/repro-tools' || { \
		echo ""; \
		echo "Type checking failed. Run for details:"; \
		echo "  $(PYTHON) -m mypy run_analysis.py shared/*.py"; \
		exit 1; \
	}
	@echo "✓ Type checking passed"

.PHONY: check
check: lint format-check type-check test
	@echo ""
	@echo "================================================"
	@echo "  ✓ All quality checks passed!"
	@echo "================================================"
	@echo ""
	@echo "  ✓ Linting (ruff)"
	@echo "  ✓ Formatting (black + ruff)"
	@echo "  ✓ Type checking (mypy)"
	@echo "  ✓ Tests (pytest)"
	@echo ""

.PHONY: dryrun
dryrun:
	@echo "Dry run - showing what would be built:"
	@echo ""
	@$(MAKE) -n all 2>&1 | grep -E '^(Building|Running|======|✓)' || true
