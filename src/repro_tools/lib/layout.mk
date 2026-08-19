# ============================================================================
# Project layout
# ============================================================================
#
# Targets that assume the template's PROJECT SHAPE, not just its toolchain:\n# $(DATA) as a single input file, $(ANALYSES) as a flat list at the root,\n# $(OUT_*) directories, an env/ sub-Makefile with an all-env target.\n#\n# This is the file a project with a different shape does NOT include. fire has\n# 114 GB of inputs across many files and declares its 43 analyses in a\n# sub-Makefile, so its verify, test-outputs, check-deps and clean are its own.\n# Splitting these out is what let fire adopt the other three files at all --\n# `include` is all-or-nothing, so one monolith meant taking 12 targets that\n# encode a shape fire does not have.
#
# Split out of common.mk on 2026-08-19. Include this file directly, or get
# all four by including common.mk.

# Artifact list (machine-readable)

# Bare artifact names, one per line, nothing else -- no header, no bullets.
#
# `repro-tools check` needs to know what a project is supposed to have built.
# It used to regex the root Makefile for a line starting `ANALYSES`, which fails
# on any project whose list is assembled rather than literal: fire builds its
# ANALYSES from $(REMODEL_ANALYSES) $(MORTGAGE_ANALYSES) ..., in a sub-Makefile,
# so the regex returned the variable references as text and the check reported
# "Could not determine artifact list" -- a check that silently stopped checking.
#
# make already knows. Asking it costs one process and works for any expansion.
#
# This is deliberately NOT `list-analyses`, which exists in both projects and is
# formatted for a human ("Available analyses:" then "  - name"). Parsing a
# display format couples a checker to how something looks; a project is free to
# make list-analyses prettier without breaking the contract.
#
# A project that assembles its list elsewhere overrides this target -- see fire,
# which delegates to its sub-Makefiles.
.PHONY: list-analyses-names
list-analyses-names:
	@$(foreach a,$(ANALYSES),echo $(a);)

# Environment Setup

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
	@$(MAKE) -C env all-env
	@echo ""
	@echo "✓ Environment ready!"
	@echo ""
	@echo "Next: make all (to run all analyses)"
	@echo ""

# Example Scripts

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

examples: sample-python
	@if [ -f env/examples/sample_julia.jl ] && [ -x env/scripts/runjulia ]; then \
		echo ""; \
		$(MAKE) sample-julia; \
	fi
	@if [ -f env/examples/sample_juliacall.py ]; then \
		echo ""; \
		$(MAKE) sample-juliacall; \
	fi
	@if [ -f env/examples/sample_stata.do ] && [ -x env/scripts/runstata ]; then \
		echo ""; \
		$(MAKE) sample-stata; \
		echo "✓ All examples complete"; \
	else \
		echo "✓ All examples complete"; \
	fi

# Cleanup Targets

.PHONY: clean
clean:
	rm -rf output/figures output/tables output/provenance output/logs .publish_stamps
	@rm -f .publish_marker .make_build_marker

.PHONY: cleanall
cleanall: clean
	@rm -rf .venv .julia .stata

# Verification & Testing

.PHONY: verify
verify:
	@echo ""
	@echo "========================================"
	@echo "  Quick Verification (~1 minute)"
	@echo "========================================"
	@echo ""
	@echo "1. Checking Python environment..."
	@if [ -f .venv/bin/python ]; then \
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
