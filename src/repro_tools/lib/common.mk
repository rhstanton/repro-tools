# ==============================================================================
# repro-tools Common Makefile
# ==============================================================================
#
# Generic targets for reproducible research projects.
# Include this in your project Makefile:
#
#   include lib/repro-tools/lib/common.mk
#
# Required variables (define before including):
#   PYTHON       - Path to Python wrapper (e.g., env/scripts/runpython)
#   JULIA        - Path to Julia wrapper (e.g., env/scripts/runjulia)
#   STATA        - Path to Stata wrapper (e.g., env/scripts/runstata)
#   REPRO_CHECK  - repro-tools CLI check command
#   REPRO_SYSINFO - repro-tools CLI sysinfo command
#   REPRO_COMPARE - repro-tools CLI compare command
#   REPRO_REPORT  - repro-tools CLI report command
#   OUT_LOG_DIR  - Output directory for logs
#   REPO_ROOT    - Repository root path
#   DATA         - Input data files (for verify target)
#
# ==============================================================================

# Ensure submodules are initialized
.PHONY: init-submodules
init-submodules:
	@git submodule update --init --recursive 2>/dev/null || true

# ==============================================================================
# Environment Setup
# ==============================================================================

.PHONY: environment
environment: init-submodules
	@echo ""
	@echo "=========================================="
	@echo "Setting up software environment..."
	@echo "=========================================="
	@echo ""
	@echo "📦 Initializing git submodules..."
	@git submodule update --init --recursive 2>/dev/null || echo "  ⚠️  Warning: git submodule update failed (not critical if already initialized)"
	@echo ""
	$(MAKE) -C env all-env
	@echo ""
	@echo "✓ Environment ready!"
	@echo ""
	@echo "Next: make all (to run all analyses)"
	@echo ""

# ==============================================================================
# Example Scripts
# ==============================================================================

.PHONY: sample-python sample-julia sample-juliacall sample-stata examples

sample-python: | $(OUT_LOG_DIR)
	@echo "Running Python example..."
	$(PYTHON) env/examples/sample_python.py 2>&1 | tee $(OUT_LOG_DIR)/sample_python.log

sample-julia: | $(OUT_LOG_DIR)
	@echo "Running Julia example..."
	$(JULIA) env/examples/sample_julia.jl 2>&1 | tee $(OUT_LOG_DIR)/sample_julia.log

sample-juliacall: | $(OUT_LOG_DIR)
	@echo "Running Python/Julia interop example (juliacall)..."
	$(PYTHON) env/examples/sample_juliacall.py 2>&1 | tee $(OUT_LOG_DIR)/sample_juliacall.log

sample-stata: | $(OUT_LOG_DIR)
	@echo "Running Stata example..."
	$(STATA) env/examples/sample_stata.do 2>&1 | tee $(OUT_LOG_DIR)/sample_stata.log

examples: sample-python sample-julia sample-juliacall
	@echo "✓ All examples complete (Stata skipped - run 'make sample-stata' if Stata is installed)"

# ==============================================================================
# Cleanup Targets
# ==============================================================================

.PHONY: clean
clean:
	rm -rf output/figures output/tables output/provenance output/logs .publish_stamps
	@rm -f .publish_marker .make_build_marker

.PHONY: cleanall
cleanall: clean
	@rm -rf .env .julia .stata

# ==============================================================================
# Verification & Testing
# ==============================================================================

.PHONY: verify
verify:
	@echo ""
	@echo "========================================"
	@echo "  Quick Verification (~1 minute)"
	@echo "========================================"
	@echo ""
	@echo "1. Checking Python environment..."
	@if [ -f .env/bin/python ]; then \
		$(PYTHON) --version | sed 's/^/   /' && echo "   ✓"; \
	else \
		echo "   ✗ Python environment not found"; \
		echo "   Run: make environment"; \
		exit 1; \
	fi
	@echo ""
	@echo "2. Checking key packages..."
	@$(PYTHON) -c "import pandas; print('   pandas', pandas.__version__, '✓')" || echo "   ✗ pandas missing"
	@$(PYTHON) -c "import matplotlib; print('   matplotlib', matplotlib.__version__, '✓')" || echo "   ✗ matplotlib missing"
	@$(PYTHON) -c "import yaml; print('   pyyaml ✓')" || echo "   ✗ pyyaml missing"
	@$(PYTHON) -c "import juliacall; print('   juliacall ✓')" || echo "   ✗ juliacall missing"
	@echo ""
	@echo "3. Checking data availability..."
	@if [ -f $(DATA) ]; then \
		echo "   $(DATA) ✓"; \
		sha256sum $(DATA) | awk '{print "   SHA256: " substr($$1,1,16) "... ✓"}'; \
	else \
		echo "   ✗ Data file not found: $(DATA)"; \
		exit 1; \
	fi
	@echo ""
	@echo "========================================"
	@echo "  ✓ Verification Complete"
	@echo "========================================"
	@echo ""
	@echo "Environment is ready. Next steps:"
	@echo "  make all              # Run all analyses"
	@echo "  make system-info      # Log computational environment"
	@echo ""

.PHONY: system-info
system-info:
	@echo "Logging computational environment..."
	@$(REPRO_SYSINFO) --output output/system_info.yml \
	  --repo-root $(REPO_ROOT)
	@echo ""
	@echo "System information saved to output/system_info.yml"
	@echo "This file contains OS, Python, Julia versions and package lists."
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

.PHONY: diff-outputs
diff-outputs:
	@echo "Comparing current outputs with published outputs..."
	@$(REPRO_COMPARE) --reference paper \
	  --current-dir output
	@echo ""

.PHONY: pre-submit
pre-submit:
	@echo "Running pre-submission checklist..."
	@$(REPRO_CHECK) --pre-submit
	@echo ""

.PHONY: pre-submit-strict
pre-submit-strict:
	@echo "Running pre-submission checklist (strict mode)..."
	@$(REPRO_CHECK) --pre-submit --strict
	@echo ""

.PHONY: replication-report
replication-report:
	@echo "Generating replication report..."
	@$(REPRO_REPORT) --format html \
	  --output output/replication_report.html
	@echo ""
	@echo "Report generated: output/replication_report.html"
	@echo "Open in browser: file://$(REPO_ROOT)/output/replication_report.html"
	@echo ""

.PHONY: test-outputs
test-outputs:
	@echo "Verifying all expected outputs exist..."
	@echo ""
	@echo "Expected figures:"
	@for analysis in $(ANALYSES); do \
		fig="output/figures/$$analysis.pdf"; \
		if [ -f "$$fig" ]; then \
			size=$$(stat -f%z "$$fig" 2>/dev/null || stat -c%s "$$fig" 2>/dev/null); \
			size_kb=$$(( size / 1024 )); \
			echo "  ✓ $$fig ($${size_kb} KB)"; \
		else \
			echo "  ✗ $$fig (missing)"; \
		fi; \
	done
	@echo ""
	@echo "Expected tables:"
	@for analysis in $(ANALYSES); do \
		tbl="output/tables/$$analysis.tex"; \
		if [ -f "$$tbl" ]; then \
			size=$$(stat -f%z "$$tbl" 2>/dev/null || stat -c%s "$$tbl" 2>/dev/null); \
			echo "  ✓ $$tbl ($$size bytes)"; \
		else \
			echo "  ✗ $$tbl (missing)"; \
		fi; \
	done
	@echo ""
	@echo "Expected provenance:"
	@for analysis in $(ANALYSES); do \
		prov="output/provenance/$$analysis.yml"; \
		if [ -f "$$prov" ]; then \
			echo "  ✓ $$prov"; \
		else \
			echo "  ✗ $$prov (missing)"; \
		fi; \
	done
	@echo ""

# ==============================================================================
# Code Quality
# ==============================================================================

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
	@echo "  1. Running black formatter..."
	@$(PYTHON) -m black run_analysis.py shared/*.py tests/*.py --exclude 'lib/repro-tools' || true
	@echo "  2. Running ruff fixes (import sorting, trailing whitespace, etc.)..."
	@$(PYTHON) -m ruff check --fix --select I,W,UP . --exclude 'lib/repro-tools' || true
	@echo "  3. Running ruff format..."
	@$(PYTHON) -m ruff format . --exclude 'lib/repro-tools' || true
	@echo ""
	@echo "✓ Formatting complete"

.PHONY: format-check
format-check:
	@echo "Checking code formatting..."
	@$(PYTHON) -m black --check run_analysis.py shared/*.py tests/*.py --exclude 'lib/repro-tools' || { \
		echo ""; \
		echo "Formatting check failed. Run:"; \
		echo "  make format"; \
		exit 1; \
	}
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

# ==============================================================================
# Utility Commands
# ==============================================================================

.PHONY: update-submodules
update-submodules:
	@echo "=========================================="
	@echo "Updating git submodules to latest..."
	@echo "=========================================="
	@echo ""
	@echo "📦 Fetching latest repro-tools from main branch..."
	@BEFORE=$$(git submodule status lib/repro-tools | awk '{print $$1}'); \
	git submodule update --remote lib/repro-tools; \
	AFTER=$$(git submodule status lib/repro-tools | awk '{print $$1}'); \
	echo ""; \
	if [ "$$BEFORE" = "$$AFTER" ]; then \
		echo "✓ Already up to date!"; \
		echo ""; \
		echo "Current commit:"; \
		git submodule status lib/repro-tools; \
	else \
		echo "✓ Submodule updated!"; \
		echo ""; \
		echo "Updated from $$BEFORE to $$AFTER"; \
		echo ""; \
		echo "To track this update in your project:"; \
		echo "  git add lib/repro-tools"; \
		echo "  git commit -m \"Update repro-tools to latest\""; \
	fi; \
	echo ""

.PHONY: update-environment
update-environment: update-submodules
	@echo "=========================================="
	@echo "Reinstalling environment with updates..."
	@echo "=========================================="
	@echo ""
	@echo "📦 Reinstalling Python environment with updated repro-tools..."
	$(MAKE) -C env python-env
	@echo ""
	@echo "📦 Reinstalling Julia packages..."
	$(MAKE) -C env julia-install-via-python
	@echo ""
	@echo "✓ Environment updated!"
	@echo ""

.PHONY: check-deps
check-deps:
	@echo "Checking dependencies..."
	@echo -n "  Python: "
	@$(PYTHON) --version 2>&1 || echo "❌ ERROR: Python not available (run: make environment)"
	@echo -n "  Julia:  "
	@$(JULIA) --version 2>&1 | xargs echo || echo "❌ ERROR: Julia not available (run: make environment)"
	@echo -n "  Data files: "
	@if [ -f $(DATA) ]; then \
		echo "✓ $(DATA)"; \
	else \
		echo "❌ ERROR: Data file not found: $(DATA)"; \
	fi
	@echo ""
	@echo "Julia thread count: $(JULIA_NUM_THREADS)"
	@echo ""

.PHONY: dryrun
dryrun:
	@echo "Dry run - showing what would be built:"
	@echo ""
	@$(MAKE) -n all 2>&1 | grep -E '^(Building|Running|======|✓)' || true

# End of common.mk
