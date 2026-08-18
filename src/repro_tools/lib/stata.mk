# ==============================================================================
# Stata packages -- shared environment rules
# ==============================================================================
#
# Included by a project's env/Makefile:
#
#     include $(REPRO_TOOLS_LIB)/stata.mk
#
# Hoisted out of project_template and fire on 2026-08-18, where the two copies
# had stayed almost identical while the Python and Julia sections around them
# diverged badly: measured line by line, stata-requirements shared 23 of 25
# recipe lines, stata-check 17 of 25, stata-vendored-clean 14 of 16, and the
# package stamp rule, stata-update and $(STATA_LOCAL) were byte-identical. That
# is what makes this half worth sharing and the other half not yet.
#
# It is also the half carrying the most easily-broken logic, which is the real
# argument for one copy: SSC has no versioned install, Stata exits 0 when a
# do-file aborts, and the rule that used to install packages reported success on
# a machine with no Stata at all. Those lessons are recorded in the comments
# below and should not have to be relearned once per project.
#
# ASSUMPTIONS
#
# Recipes run from the project's env/ directory, so paths are relative to it.
# Override STATA_DIR if the depot lives elsewhere; everything else derives.
#
# INPUTS
#
#   STATA_DIR   - repo-local Stata depot        (default: ../.stata)
#   STATA       - Stata binary used for installs (default: stata-mp)
#
# Reads env/stata-packages.txt and writes env/stata-requirements.txt.

STATA_DIR ?= ../.stata
STATA ?= stata-mp

#
# SSC has no versioned install: `ssc install pkg 3.1.2` is not "install version
# 3.1.2", it is a syntax error (varlist not allowed, r(101)), and SSC serves only
# whatever is current today. So a version number in stata-packages.txt could
# never have been enforced by anything -- and the rule that read it printed
# "with version 3.1.2" while issuing an unversioned install, or nothing at all.
#
# The only real pinning is to commit the ado files. That is what .stata/ado/plus
# is for, and it follows AEA Data Editor guidance: "provide copies of such
# packages/modules when the package repository does not allow you to specify a
# version." stata-env therefore installs NOTHING when the files are vendored;
# `make stata-update` refreshes from SSC deliberately.
#
# Versions live in stata-requirements.txt, generated from what is actually
# installed and checked by `make stata-check` -- machine-checkable, unlike a
# number typed into a list by hand.
STATA_LOCAL := $(STATA_DIR)/ado/plus

# First word of each non-comment, non-blank line. The comment/blank filter is
# load-bearing: a bare `{print $$1}` turns a "#" comment line into a package
# named "#", and then a stamp target for it.
STATA_PACKAGES := $(shell awk '!/^[[:space:]]*#/ && NF {print $$1}' stata-packages.txt 2>/dev/null)
STATA_STAMPS := $(addprefix $(STATA_DIR)/., $(addsuffix .stamp, $(STATA_PACKAGES)))

.PHONY: stata-env
stata-env: $(STATA_STAMPS)
	@echo "All Stata packages present in $(STATA_LOCAL)"
	@echo "Use env/scripts/runstata to run your .do files"

# Install one package.
#
# Fails loudly, which the version this replaces did not: it wrapped the install
# in `cap noi`, sent output to /dev/null, appended `|| true`, and touched the
# stamp -- and under .ONESHELL that touch is the SAME shell, so the recipe's exit
# status was touch's. "All Stata packages installed" printed on a machine with no
# Stata at all.
$(STATA_DIR)/.%.stamp: stata-packages.txt | $(STATA_LOCAL)
	@mkdir -p $(STATA_DIR)
	ado=$$(find "$(CURDIR)/$(STATA_DIR)/ado/plus" -name '$*.ado' 2>/dev/null | head -1)
	if [ -n "$$ado" ] && [ -z "$$STATA_UPDATE" ]; then
	  echo "  vendored: $* $$(grep -m1 '^\*!' "$$ado" | sed 's/^\*! *//')"
	  touch $@
	  exit 0
	fi
	echo "Installing Stata package from SSC: $*"
	if ! command -v $(STATA) >/dev/null 2>&1; then
	  echo "ERROR: $(STATA) not found on PATH; cannot install $*." >&2
	  exit 1
	fi
	d=$$(mktemp -d)
	echo 'sysdir set PLUS "$(CURDIR)/$(STATA_DIR)/ado/plus"' > $$d/install.do
	echo 'ssc install $*, replace all' >> $$d/install.do
	echo 'exit, clear STATA' >> $$d/install.do
	(cd $$d && $(STATA) -b do install.do >/dev/null 2>&1) || true
	# Judge by the LOG, not the exit status. Stata returns 0 even when a
	# do-file aborts, so trusting $$? here produces a check that always passes.
	if [ ! -f $$d/install.log ] || grep -qE '^r\([0-9]+\);' $$d/install.log; then
	  echo "ERROR: $(STATA) failed while installing $*. Log:" >&2
	  sed -n '1,40p' $$d/install.log >&2 2>/dev/null || echo "  (no log produced)" >&2
	  rm -rf $$d
	  exit 1
	fi
	rm -rf $$d
	ado=$$(find "$(CURDIR)/$(STATA_DIR)/ado/plus" -name '$*.ado' 2>/dev/null | head -1)
	if [ -z "$$ado" ]; then
	  echo "ERROR: $* installed without error, but $*.ado is not in $(STATA_LOCAL)." >&2
	  exit 1
	fi
	echo "  installed: $$(grep -m1 '^\*!' "$$ado" | sed 's/^\*! *//')"
	touch $@

$(STATA_LOCAL):
	@mkdir -p $(STATA_LOCAL)

# Record the versions actually installed, in the format `require` reads. Written
# by require's own `list save` mode rather than hand-rolled, so it stays
# canonical and machine-checkable.
.PHONY: stata-requirements
stata-requirements:
	@if ! command -v $(STATA) >/dev/null 2>&1; then
	  echo "ERROR: $(STATA) not found; cannot generate requirements." >&2
	  exit 1
	fi
	d=$$(mktemp -d)
	echo 'sysdir set PLUS "$(CURDIR)/$(STATA_DIR)/ado/plus"' > $$d/gen.do
	echo "require using \"$$d/req.txt\", list save replace exact" >> $$d/gen.do
	echo 'exit, clear STATA' >> $$d/gen.do
	if ! (cd $$d && $(STATA) -b do gen.do >/dev/null 2>&1) || [ ! -f $$d/req.txt ]; then
	  echo "ERROR: could not generate requirements. First 40 log lines:" >&2
	  sed -n '1,40p' $$d/gen.log >&2 2>/dev/null || true
	  rm -rf $$d; exit 1
	fi
	{
	  echo "# Stata package versions vendored in .stata/ado/plus, which is committed."
	  echo "# Generated by 'make stata-requirements' using require's own list mode."
	  echo "#"
	  echo "# Check the installed tree against this file:  make stata-check"
	  echo "#"
	  echo "# SSC serves only the current release, so these cannot be re-obtained by"
	  echo "# version; that is why the ado files themselves are committed."
	  awk '!/^[*#]/ && NF {print $$1, $$2, $$3}' $$d/req.txt | sort -u
	} > stata-requirements.txt
	rm -rf $$d
	echo ">> Wrote env/stata-requirements.txt"

# Assert the vendored ado tree still matches what is committed.
#
# Needs no Stata, and it is the check that catches the failure actually observed
# in a downstream project on 2026-08-17: estout/esttab modified, both .trk
# indexes rewritten, and require.ado DELETED -- SSC versions overwriting the
# pinned ones, which is precisely what committing them exists to prevent. A
# `make stata-update` does exactly this, by design; the defect was that nothing
# afterwards said so.
#
# It runs before the Stata-based check for two reasons. It is instant, and
# `stata-check` verifies versions by invoking Stata's `require` command -- which
# is itself one of the vendored packages. When require.ado is the file that went
# missing, the checker cannot report its own absence. Comparing against git has
# no such circularity.
.PHONY: stata-vendored-clean
stata-vendored-clean:
	@if ! git -C .. rev-parse --git-dir >/dev/null 2>&1; then \
	  echo ">> Not a git checkout; skipping vendored-tree comparison."; \
	  exit 0; \
	fi
	@if ! git -C .. ls-files --error-unmatch .stata/ado/plus >/dev/null 2>&1; then \
	  echo ">> No vendored Stata tree committed; nothing to compare."; \
	  exit 0; \
	fi
	@if ! git -C .. diff --quiet -- .stata/ado/plus 2>/dev/null; then \
	  echo "ERROR: the vendored Stata tree differs from what is committed." >&2; \
	  echo "" >&2; \
	  git -C .. status --short -- .stata/ado/plus >&2; \
	  echo "" >&2; \
	  echo "  These files are PINS. SSC serves no versioned install, so the ado" >&2; \
	  echo "  files themselves are the version record." >&2; \
	  echo "" >&2; \
	  echo "  To discard the drift:      git restore .stata/ado/plus" >&2; \
	  echo "  To adopt it deliberately:  make stata-requirements && review the diff" >&2; \
	  exit 1; \
	fi
	@echo ">> Vendored Stata tree matches HEAD."

# Assert the installed tree still matches stata-requirements.txt. This is the
# check the old "with version 3.1.2" console line only pretended to be.
.PHONY: stata-check
stata-check: stata-vendored-clean
	@if [ ! -f stata-requirements.txt ]; then
	  echo "No env/stata-requirements.txt yet. Installed packages:"
	  find $(STATA_DIR)/ado/plus -name "*.ado" -exec basename {} \; 2>/dev/null \
	    | sort -u | sed 's/^/     /' || echo "     (none)"
	  echo "Generate the pin record with: make stata-requirements"
	  exit 0
	fi
	if ! command -v $(STATA) >/dev/null 2>&1; then
	  echo "ERROR: $(STATA) not found; cannot check Stata packages." >&2
	  exit 1
	fi
	d=$$(mktemp -d)
	echo 'sysdir set PLUS "$(CURDIR)/$(STATA_DIR)/ado/plus"' > $$d/check.do
	echo "require using \"$(CURDIR)/stata-requirements.txt\"" >> $$d/check.do
	echo 'exit, clear STATA' >> $$d/check.do
	(cd $$d && $(STATA) -b do check.do >/dev/null 2>&1) || true
	if [ ! -f $$d/check.log ]; then
	  echo "ERROR: $(STATA) produced no log; it may not have run." >&2
	  rm -rf $$d; exit 1
	fi
	if grep -qE '^r\([0-9]+\);' $$d/check.log; then
	  echo "ERROR: installed Stata packages do NOT match env/stata-requirements.txt" >&2
	  grep -E 'require error|^r\([0-9]+\);' $$d/check.log >&2 || true
	  rm -rf $$d; exit 1
	fi
	echo ">> Stata packages match env/stata-requirements.txt:"
	sed -n '/^[^#]/p' stata-requirements.txt | sed 's/^/     /'
	rm -rf $$d

# Deliberately refresh from SSC, overwriting the committed ado files. Never
# automatic: it replaces reviewed versions with whatever SSC serves today.
.PHONY: stata-update
stata-update:
	@rm -f $(STATA_STAMPS)
	STATA_UPDATE=1 $(MAKE) --no-print-directory stata-env
	$(MAKE) --no-print-directory stata-requirements
	@echo ">> Refreshed from SSC. Review 'git diff' on .stata/ado/plus and"
	@echo "   env/stata-requirements.txt, then commit deliberately."

.PHONY: stata-clean
stata-clean:
	rm -rf $(STATA_DIR)

# What is actually installed in the repo-local Stata adopath, as opposed to what
# env/stata-requirements.txt claims.
.PHONY: stata-list
stata-list:
	@echo "Installed Stata packages (.stata/ado/plus):"
	@find $(STATA_LOCAL) -name "*.ado" -exec basename {} \; 2>/dev/null \
	  | sort | uniq || echo "  none installed"
