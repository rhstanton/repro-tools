# ============================================================================
# Developer tooling
# ============================================================================
#
# Targets that need nothing from the project but $(PYTHON).\n#\n# Linting, formatting, type-checking and the test runners. A consumer that\n# can name its interpreter can include this file and get all of it.
#
# Split out of common.mk on 2026-08-19. Include this file directly, or get
# all four by including common.mk.

# ------------------------------------------------------------------ knobs
#
# These targets are otherwise pure toolchain -- they need $(PYTHON) and nothing
# about the project. Three of them used to hardcode the template's own paths,
# which quietly made this file layout-dependent and unusable elsewhere.
#
# TEST_PATHS defaults to EMPTY, and that is the important one. It used to be
# `tests/`. Measured 2026-08-19 against fire, whose testpaths span
# housing-analysis/tests, peer-effects/tests and tests: `pytest tests/` collects
# 147 tests where `pytest` collects 326, and prints a tick either way. A shared
# test target that silently runs 55% of a suite is the precise defect this
# machinery exists to prevent. Empty defers to the project's own pytest
# `testpaths`, which is where that decision belongs; verified equivalent for
# project_template, where the two forms collect the same 407 tests.
#
# Override any of these BEFORE including this file (or common.mk).
TEST_PATHS ?=
COV_TARGET ?= scripts
LINT_PATHS ?= .
TYPECHECK_PATHS ?= run_analysis.py shared/*.py
RUFF_EXCLUDE ?= lib/repro-tools
SYSINFO_OUTPUT ?= output/system_info.yml

.PHONY: system-info
system-info:
	@echo "Logging computational environment..."
	@$(REPRO_SYSINFO) --output $(SYSINFO_OUTPUT) \
	  --repo-root $(REPO_ROOT)
	@echo ""
	@echo "System information saved to $(SYSINFO_OUTPUT)"
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
	@$(PYTHON) -m pytest $(TEST_PATHS) -q -m "not slow"
	@echo ""
	@echo "✓ Fast tests complete -- run 'make test' for the full suite"
	@echo ""

.PHONY: test
test:
	@echo "Running test suite..."
	@$(PYTHON) -m pytest $(TEST_PATHS) -v
	@echo ""
	@echo "✓ Tests complete"
	@echo ""

.PHONY: test-cov
test-cov:
	@echo "Running tests with coverage..."
	@$(PYTHON) -m pytest $(TEST_PATHS) --cov=$(COV_TARGET) --cov-report=html --cov-report=term
	@echo ""
	@echo "Coverage report: htmlcov/index.html"
	@echo ""

# Code Quality

.PHONY: lint
lint:
	@echo "Running linter (ruff)..."
	@$(PYTHON) -m ruff check $(LINT_PATHS) --exclude '$(RUFF_EXCLUDE)' || { \
		echo ""; \
		echo "Linting failed. To see details:"; \
		echo "  $(PYTHON) -m ruff check $(LINT_PATHS)"; \
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
	@$(PYTHON) -m ruff check --fix $(LINT_PATHS) --exclude '$(RUFF_EXCLUDE)' || true
	@echo "  2. Running ruff format..."
	@$(PYTHON) -m ruff format $(LINT_PATHS) --exclude '$(RUFF_EXCLUDE)' || true
	@echo ""
	@echo "✓ Formatting complete"

.PHONY: format-check
format-check:
	@echo "Checking code formatting..."
	@$(PYTHON) -m ruff format --check $(LINT_PATHS) --exclude '$(RUFF_EXCLUDE)' || { \
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
	@$(PYTHON) -m mypy $(TYPECHECK_PATHS) --exclude '$(RUFF_EXCLUDE)' || { \
		echo ""; \
		echo "Type checking failed. Run for details:"; \
		echo "  $(PYTHON) -m mypy $(TYPECHECK_PATHS)"; \
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
	@echo "  ✓ Formatting (ruff)"
	@echo "  ✓ Type checking (mypy)"
	@echo "  ✓ Tests (pytest)"
	@echo ""

.PHONY: dryrun
dryrun:
	@echo "Dry run - showing what would be built:"
	@echo ""
	@$(MAKE) -n all 2>&1 | grep -E '^(Building|Running|======|✓)' || true
