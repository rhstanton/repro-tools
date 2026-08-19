# ============================================================================
# Git and submodule maintenance
# ============================================================================
#
# Targets that need only git. Kept apart because a project can want submodule\n# handling without adopting this repo's opinions about anything else.
#
# Split out of common.mk on 2026-08-19. Include this file directly, or get
# all four by including common.mk.

# ------------------------------------------------------------------ knobs
#
# Where repro-tools is vendored. Hardcoding lib/repro-tools made these targets
# update the wrong path for any project that vendors it elsewhere -- and they
# would have reported success while doing it, since `git submodule update` on a
# path that is not a submodule is not an error.
REPRO_SUBMODULE_PATH ?= lib/repro-tools

# repro-tools Common Makefile
#
# Generic targets for reproducible research projects.
# Include this in your project Makefile:
#
#   include lib/repro-tools/src/repro_tools/lib/common.mk
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

# Ensure submodules are initialized.
#
# The previous version was `git submodule update --init --recursive 2>/dev/null
# || true`, which discarded stderr AND the exit status, so an unreachable URL, a
# missing git, or a failed clone were all indistinguishable from success. The
# build then continued against submodules that were not there, and the real
# failure surfaced later as a missing module -- somewhere that gave no hint the
# cause was here.
#
# The message lists causes in order of likelihood, and that order was corrected
# 2026-08-19 after it misled a debugging session for twenty minutes: a copied
# working tree left lib/repro-tools non-empty, git said "destination path already
# exists and is not an empty directory", and the advice to "check network access
# and whether any are private" sent the reader to test credentials that were
# fine. An error message that offers one hypothesis is read as a diagnosis.
#
# "Nothing to initialize" and "initialization failed" are different, and only
# the first is fine. A project exported with `git archive` has no .git and no
# submodules to fetch; that is normal and silent. A checkout that declares
# submodules and cannot fetch them is broken, and says so.
.PHONY: init-submodules
init-submodules:
	@if [ ! -e .gitmodules ]; then \
	  : ; \
	elif ! git rev-parse --git-dir >/dev/null 2>&1; then \
	  echo "Not a git checkout (an export?) -- skipping submodule init."; \
	elif ! git submodule update --init --recursive; then \
	  echo "" >&2; \
	  echo "ERROR: git submodule update failed." >&2; \
	  echo "  .gitmodules declares submodules that could not be checked out." >&2; \
	  echo "  Read the git output ABOVE this message -- it names the cause." >&2; \
	  echo "  Most likely, in order:" >&2; \
	  echo "    - the submodule path already exists and is not empty" >&2; \
	  echo "      (a working tree copied over a clone); remove it and retry" >&2; \
	  echo "    - no credentials for a private submodule" >&2; \
	  echo "    - no network access" >&2; \
	  exit 1; \
	fi

# Utility Commands

.PHONY: update-submodules
update-submodules:
	@echo "=========================================="
	@echo "Updating git submodules to latest..."
	@echo "=========================================="
	@echo ""
	@echo "📦 Fetching latest repro-tools from main branch..."
	@BEFORE=$$(git submodule status $(REPRO_SUBMODULE_PATH) | awk '{print $$1}'); \
	git submodule update --remote $(REPRO_SUBMODULE_PATH); \
	AFTER=$$(git submodule status $(REPRO_SUBMODULE_PATH) | awk '{print $$1}'); \
	echo ""; \
	if [ "$$BEFORE" = "$$AFTER" ]; then \
		echo "✓ Already up to date!"; \
		echo ""; \
		echo "Current commit:"; \
		git submodule status $(REPRO_SUBMODULE_PATH); \
	else \
		echo "✓ Submodule updated!"; \
		echo ""; \
		echo "Updated from $$BEFORE to $$AFTER"; \
		echo ""; \
		echo "To track this update in your project:"; \
		echo "  git add $(REPRO_SUBMODULE_PATH)"; \
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
