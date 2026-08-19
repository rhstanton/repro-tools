# ============================================================================
# Reproducibility workflow
# ============================================================================
#
# Targets that drive the repro_tools CLI: pre-submission checks, output\n# comparison, the replication report, and template diffing.\n#\n# Separate from tools.mk because these need the repro_tools PACKAGE installed,\n# not merely a Python interpreter.
#
# Split out of common.mk on 2026-08-19. Include this file directly, or get
# all four by including common.mk.

# ------------------------------------------------------------------ knobs
#
# REPORT_OUTPUT is the one path this layer names. Parameterized for the same
# reason as tools.mk's: a shared target that writes to a directory the consuming
# project does not have fails in that project, not here.
REPORT_OUTPUT ?= output/replication_report.html

.PHONY: diff-outputs
diff-outputs:
	@echo "Comparing current outputs with published outputs..."
	@$(REPRO_COMPARE) --reference paper \
	  --current-dir output
	@echo ""

# `repro-check` IS the pre-submission checklist -- there is no --pre-submit
# flag and never was. These targets passed one until 2026-08-17, which went
# unnoticed because `$(PYTHON) -m repro_tools.cli check` had no module entry
# point and so ignored every argument and exited 0. Fixing the entry point is
# what made the wrong flags visible.
.PHONY: pre-submit
pre-submit:
	@echo "Running pre-submission checklist..."
	@$(REPRO_CHECK)
	@echo ""

.PHONY: pre-submit-strict
pre-submit-strict:
	@echo "Running pre-submission checklist (strict mode)..."
	@$(REPRO_CHECK) --strict
	@echo ""

.PHONY: replication-report
replication-report:
	@echo "Generating replication report..."
	@$(REPRO_REPORT) --format html \
	  --output $(REPORT_OUTPUT)
	@echo ""
	@echo "Report generated: $(REPORT_OUTPUT)"
	@echo "Open in browser: file://$(REPO_ROOT)/$(REPORT_OUTPUT)"
	@echo ""

# Template updates

# Show which project_template changes have not been applied here yet, split by
# whether this project has customized the file. Prints only -- it never writes.
#
# An auto-applying version would be the dangerous one: template changes routinely
# collide with the project-specific decisions that make a project a project, and
# resolving that silently is how an analysis acquires an edit nobody reviewed.
#
# Needs template-origin.toml (written by bootstrap.py at creation); without a
# record of which template version this project came from there is no baseline
# and the question cannot be answered.
.PHONY: template-diff
template-diff:
	@$(PYTHON) -m repro_tools.template_update $(ARGS)
