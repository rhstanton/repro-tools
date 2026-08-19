# ==============================================================================
# {name} - Makefile
# ==============================================================================

# Delete partial outputs on error
.DELETE_ON_ERROR:

# Default shell with safer options
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# Ensure git submodules are initialized
$(shell git submodule update --init --recursive 2>/dev/null || true)

# ==============================================================================
# Environment Variables
# ==============================================================================

# Julia threading (auto-detect CPU cores)
export JULIA_NUM_THREADS ?= $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)

# ==============================================================================
# Executable Scripts
# ==============================================================================

{runners}

# repro-tools CLI commands, invoked as a MODULE rather than by console-script
# path. Two reasons, both learned the hard way:
#
#   * `.env/bin/...` was the conda-era layout. Environments are built with uv
#     now and live in `.venv/`, so those paths named files that do not exist.
#   * `$(PYTHON) -m` runs the project's OWN interpreter, so it cannot pick up a
#     repro-tools installed somewhere else on PATH.
#
# This mirrors what project_template itself does. Note that the module form
# requires repro-tools to have a __main__ entry point, which it lacked until
# 2026-08-18 -- before that, every one of these commands silently did nothing
# and exited 0.
REPRO_CHECK   := $(PYTHON) -m repro_tools.cli check
REPRO_PUBLISH := $(PYTHON) -m repro_tools.cli publish
REPRO_COMPARE := $(PYTHON) -m repro_tools.cli compare
REPRO_SYSINFO := $(PYTHON) -m repro_tools.cli sysinfo
REPRO_REPORT  := $(PYTHON) -m repro_tools.cli report

# ==============================================================================
# Analysis Definitions
# ==============================================================================

# All analyses to run
ANALYSES := sample_analysis

# Input data files
DATA := data/sample.csv

# ==============================================================================
# Directory Paths
# ==============================================================================

REPO_ROOT := $(shell pwd)

OUT_FIG_DIR := output/figures
OUT_TBL_DIR := output/tables
OUT_PROV_DIR := output/provenance
OUT_LOG_DIR := output/logs

PAPER_DIR := paper
PAPER_FIG_DIR := $(PAPER_DIR)/figures
PAPER_TBL_DIR := $(PAPER_DIR)/tables

# Default target
.DEFAULT_GOAL := default

# ==============================================================================
# Include Generic Targets from repro-tools
# ==============================================================================

include lib/repro-tools/lib/common.mk

# ==============================================================================
# Main Build Targets
# ==============================================================================

.PHONY: all
all:
	@rm -f .make_build_marker
	@$(MAKE) --no-print-directory $(ANALYSES)
	@if [ -f .make_build_marker ]; then \
		echo ""; \
		echo "✓ All analyses complete!"; \
		echo ""; \
		rm -f .make_build_marker; \
	else \
		echo ""; \
		echo "✓ Nothing to do - all outputs up-to-date"; \
		echo ""; \
	fi

# ==============================================================================
# Analysis Build Rules
# ==============================================================================

# sample_analysis definition
sample_analysis.script  := run_analysis.py
sample_analysis.runner  := $(PYTHON)
sample_analysis.inputs  := $(DATA)
sample_analysis.outputs := $(OUT_FIG_DIR)/sample_analysis.pdf $(OUT_TBL_DIR)/sample_analysis.tex $(OUT_PROV_DIR)/sample_analysis.yml
sample_analysis.args    := sample_analysis

# Rule generator macro
define make-analysis-rule

$($(1).outputs) &: $($(1).script) $($(1).inputs) | $(OUT_FIG_DIR) $(OUT_TBL_DIR) $(OUT_PROV_DIR) $(OUT_LOG_DIR)
	@echo "========================================"
	@echo "Running analysis: $(1)"
	@echo "========================================"
	$($(1).runner) $($(1).script) $($(1).args) 2>&1 | tee $(OUT_LOG_DIR)/$(1).log
	@echo "✓ $(1) complete"
	@echo "Built: $(1)" >> .make_build_marker

.PHONY: $(1)
$(1): $($(1).outputs)

endef

# Generate rules for all analyses
$(foreach analysis,$(ANALYSES),$(eval $(call make-analysis-rule,$(analysis))))

# Ensure output directories exist
$(OUT_FIG_DIR) $(OUT_TBL_DIR) $(OUT_PROV_DIR) $(OUT_LOG_DIR):
	@mkdir -p $@

# ==============================================================================
# Publishing
# ==============================================================================

PUBLISH_ANALYSES ?= $(ANALYSES)
PUBLISH_STAMP_DIR := .publish_stamps

.PHONY: publish publish-force
publish:
	@echo "Publishing to paper/..."
	@$(MAKE) --no-print-directory -s $(addprefix $(PUBLISH_STAMP_DIR)/,$(addsuffix .stamp,$(PUBLISH_ANALYSES)))
	@echo "✓ Publishing complete"

publish-force:
	@rm -rf $(PUBLISH_STAMP_DIR)
	@$(MAKE) publish

$(PUBLISH_STAMP_DIR)/%.stamp: $(OUT_FIG_DIR)/%.pdf $(OUT_TBL_DIR)/%.tex $(OUT_PROV_DIR)/%.yml
	@mkdir -p $(PUBLISH_STAMP_DIR) $(PAPER_FIG_DIR) $(PAPER_TBL_DIR)
	@$(REPRO_PUBLISH) analyses --paper-root $(PAPER_DIR) --project-root . "$*"
	@touch $@

# ==============================================================================
# Utility Targets
# ==============================================================================

.PHONY: list-analyses
list-analyses:
	@echo "Available analyses:"
	@for name in $(ANALYSES); do echo "  - $$name"; done

# ==============================================================================
# Help Targets
# ==============================================================================

.PHONY: default
default:
	@echo ""
	@echo "{name}"
	@echo "{name_underline}"
	@echo ""
	@echo "ESSENTIAL COMMANDS:"
	@echo "  make environment  Setup environments (~10 min)"
	@echo "  make all          Run all analyses"
	@echo "  make verify       Quick environment check"
	@echo "  make publish      Publish to paper/"
	@echo "  make clean        Remove outputs"
	@echo ""
	@echo "  make help         Show all commands"
	@echo ""

.PHONY: help
help:
	@echo "{name} - Available Commands"
	@echo ""
	@echo "ENVIRONMENT:"
	@echo "  make environment  Setup Python/Julia/Stata"
	@echo "  make verify       Quick verification check"
	@echo ""
	@echo "BUILD:"
	@echo "  make all          Run all analyses"
	@echo "  make $(word 1,$(ANALYSES))     Run specific analysis"
	@echo ""
	@echo "PUBLISH:"
	@echo "  make publish      Publish to paper/"
	@echo ""
	@echo "CLEANUP:"
	@echo "  make clean        Remove outputs"
	@echo "  make cleanall     Remove outputs + environments"
	@echo ""
