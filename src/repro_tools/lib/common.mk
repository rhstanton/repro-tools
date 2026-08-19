# ==============================================================================
# repro-tools Common Makefile
# ==============================================================================
#
# Every shared target, in one include:
#
#   include lib/repro-tools/src/repro_tools/lib/common.mk
#
# This file is now a thin aggregator over four layers, split 2026-08-19. It
# behaves exactly as it did before -- including it still gets all 30 targets --
# so no existing consumer needs to change.
#
# WHY THE SPLIT
#
# `include` is all-or-nothing, and 12 of the 30 targets assume the template's
# PROJECT SHAPE rather than its toolchain: $(DATA) as one input file, $(ANALYSES)
# as a flat list at the root, $(OUT_*) directories, an env/ sub-Makefile. A
# project shaped differently could therefore adopt none of the other 18.
#
# That was not theoretical. fire has 114 GB of inputs across many files and
# declares its 43 analyses in a sub-Makefile; measured 2026-08-19, it collided on
# 18 of these 30 target names, so it had hand-copied the generic ones instead --
# and every fix made here reached project_template and never reached fire.
#
# THE LAYERS, by what each requires
#
#   tools.mk   $(PYTHON) only ......... lint, format, format-check, type-check,
#                                       check, test, test-fast, test-cov,
#                                       system-info, dryrun
#   repro.mk   + the repro_tools pkg .. pre-submit, pre-submit-strict,
#                                       diff-outputs, replication-report,
#                                       template-diff
#   git.mk     git only ............... init-submodules, update-submodules,
#                                       update-environment
#   layout.mk  the project shape ...... environment, verify, test-outputs,
#                                       check-deps, clean, cleanall, examples,
#                                       sample-*, list-analyses-names
#
# A project whose shape differs includes the first three and keeps its own
# equivalents of the fourth.
#
# Required variables, by layer:
#   PYTHON       tools.mk, repro.mk, layout.mk   (e.g. env/scripts/runpython)
#   JULIA        layout.mk                        (e.g. env/scripts/runjulia)
#   STATA        layout.mk                        (e.g. env/scripts/runstata)
#   DATA         layout.mk                        the input data file
#   ANALYSES     layout.mk                        the artifact names
#   OUT_*_DIR    layout.mk                        output directories
#
# Resolved relative to THIS file, so the layers are found wherever repro-tools is
# checked out -- a submodule path, an installed package, anywhere. Hardcoding
# lib/repro-tools/... would break every consumer that vendors it elsewhere.
REPRO_LIB_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

include $(REPRO_LIB_DIR)tools.mk
include $(REPRO_LIB_DIR)repro.mk
include $(REPRO_LIB_DIR)git.mk
include $(REPRO_LIB_DIR)layout.mk
