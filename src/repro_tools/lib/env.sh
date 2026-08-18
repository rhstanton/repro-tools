# env.sh — the shared toolchain environment for a repro-tools project.
#
# This is the half of the environment that is identical in every project: which
# Python runs, which Julia runs, and how the two are bridged. It lives here, in
# the submodule, so that fixing it fixes every project that updates the
# submodule. Project-specific settings (DATA_DIR, extra PYTHONPATH entries,
# machine-local overrides) belong in the project's own env/env.sh, which sources
# this file.
#
# That split is the point. Every environment bug worth fixing so far has been in
# this half -- an inherited Julia path, a variable name that was a no-op, three
# wrapper scripts disagreeing about the same variable -- and while this content
# was copied into each project at creation, none of those fixes could ever reach
# an existing project.
#
# CONTRACT: this file is *sourced*, never executed.
#   - No `set -e`, no `exec`, no output on success, no exit.
#   - Safe to source repeatedly (direnv re-evaluates on every directory change),
#     hence the idempotence guard on PATH.
#   - Never `unset CDPATH`: that would mutate the caller's interactive shell.
#     Clear it inside a command substitution instead.
#   - Does NOT hard-fail on a missing environment. A fresh clone should still
#     give a usable shell; the wrapper scripts check and fail loudly.
#
# INPUT: REPRO_PROJECT_ROOT must be set by the caller, because only the project
# knows where its own root is. Passing it in beats guessing from this file's
# location, which would encode the submodule path and break the moment anyone
# vendors it elsewhere.

if [[ -z "${REPRO_PROJECT_ROOT:-}" ]]; then
    echo "env.sh: REPRO_PROJECT_ROOT is not set." >&2
    echo "  Source this from the project's env/env.sh, which sets it first." >&2
    return 1 2>/dev/null || exit 1
fi

if [[ ! -d "$REPRO_PROJECT_ROOT" ]]; then
    echo "env.sh: REPRO_PROJECT_ROOT does not exist: $REPRO_PROJECT_ROOT" >&2
    echo "  If it looks like two paths joined, CDPATH leaked into a" >&2
    echo "  \$(cd ... && pwd) in the caller. Use: \$(CDPATH= cd -- ... && pwd)" >&2
    return 1 2>/dev/null || exit 1
fi

# --- Python interpreter --------------------------------------------------
# .venv only, with no fallback on purpose. An alternate interpreter that
# silently takes over when .venv is missing is exactly the failure a
# reproducible environment exists to prevent: a missing environment must be an
# error, not a quiet substitution.
if [[ -x "$REPRO_PROJECT_ROOT/.venv/bin/python" ]]; then
    REPRO_VENV="$REPRO_PROJECT_ROOT/.venv"
else
    REPRO_VENV=""
fi
REPRO_PYTHON="${REPRO_VENV:+$REPRO_VENV/bin/python}"
export REPRO_VENV REPRO_PYTHON

# --- Julia / Python bridge -----------------------------------------------
# Without these, juliacall downloads its own Julia and lets CondaPkg build a
# second, redundant Python environment underneath it. Both are pinned in-repo.
export PYTHON_JULIACALL_HANDLE_SIGNALS=yes
export PYTHON_JULIAPKG_PROJECT="$REPRO_PROJECT_ROOT/.julia"
export JULIA_PROJECT="$REPRO_PROJECT_ROOT/env"
export JULIA_DEPOT_PATH="$REPRO_PROJECT_ROOT/.julia"
export JULIA_LOAD_PATH="$JULIA_PROJECT:$PYTHON_JULIAPKG_PROJECT:@stdlib"

# Optional GPU environment, layered on when it exists.
#
# CUDA.jl is never a dependency of env/Project.toml -- that would force a GPU
# stack onto every machine, including the Macs. `JULIA_ENABLE_CUDA=1 make
# environment` installs it into $REPRO_PROJECT_ROOT/.julia/gpu-env instead,
# which is gitignored and machine-local, and it is put on the load path here so
# `using CUDA` resolves. On a machine that never opted in, the directory does
# not exist and this is a no-op: the project stays CPU-only with nothing to
# switch.
#
# This lives in env.sh, not in a wrapper or an analysis script, because the
# assignment above is UNCONDITIONAL and therefore destroys any JULIA_LOAD_PATH
# set by the caller. Until 2026-08-17 the layering was done only in Python, by
# run_did.py, after the wrapper had already run -- so GPU support existed
# through juliacall and was invisible to `runjulia`, and pre-setting
# JULIA_LOAD_PATH before a wrapper was silently discarded. One feature, two
# entry points, different answers: the exact split that consolidating the
# environment into this file was meant to end.
#
# run_did.py's own layering is now redundant rather than load-bearing. It is
# harmless (it appends only if the entry is absent) and is kept so the analysis
# still finds the GPU if invoked through some future path that misses env.sh.
if [[ -f "$REPRO_PROJECT_ROOT/.julia/gpu-env/Project.toml" ]]; then
    export JULIA_LOAD_PATH="$JULIA_LOAD_PATH:$REPRO_PROJECT_ROOT/.julia/gpu-env"
fi

export JULIA_CONDAPKG_BACKEND=Null

# Thread count belongs here rather than in a wrapper or a Makefile, because the
# value has to be the SAME everywhere and it was not: one project had runjulia
# defaulting to 1 while its Makefile exported $(nproc). That is not a
# performance detail. Thread count changes the order of floating-point
# reductions, so the same regression run through two entry points can differ in
# the last digit -- which is exactly the kind of unexplained discrepancy that
# costs days to chase.
#
# 1 because reproducibility outranks speed here: it is the only setting that
# gives the same answer on every machine regardless of core count.
#
# Assigned unconditionally, NOT as ${JULIA_NUM_THREADS:-1}. The `:-` form honors
# whatever the ambient shell happens to hold, and the ambient shell carries
# values from whichever project you were last in -- this very line, written with
# `:-`, silently produced JULIA_NUM_THREADS=32 in a fresh project because another
# repo's direnv had exported it. That is the PYTHON_JULIAPKG_EXE failure wearing
# different clothes: a default that quietly defers to an inherited value is not a
# default. The sanctioned override channel is env/local.sh, which the project's
# env.sh sources AFTER this file precisely so a deliberate override still wins.
export JULIA_NUM_THREADS=1

if [[ -n "$REPRO_PYTHON" ]]; then
    # JULIA_PYTHONCALL_EXE is the name PythonCall actually reads. A project
    # carried JULIA_PYTHONCALL_PYTHON here for months, which PythonCall does not
    # consult at all -- a silent no-op, so the interpreter was never pinned and
    # PythonCall stayed free to have CondaPkg build its own. Keep this in step
    # with install_julia.py, which must set the same name.
    export JULIA_PYTHONCALL_EXE="$REPRO_PYTHON"
fi

# --- Julia binary --------------------------------------------------------
# PYTHON_JULIAPKG_EXE is set HERE and only here, decided *entirely* by
# REPRO_PROJECT_ROOT: either this project's own bundled Julia, or nothing.
#
# The `unset` in the else branch is load-bearing. Leaving an inherited value in
# place is not neutral: building a fresh clone from a shell that still had
# another checkout's environment loaded (direnv unloads on the next *prompt*, so
# `git clone && cd && make environment` as one command sequence never triggers
# it) silently builds the clone against the OTHER project's Julia. juliapkg finds
# a working Julia there, so it never installs one into the clone's depot, and the
# build reports success -- including a GPU check against the wrong CUDA -- until
# something looks for the clone-local binary that was never created.
#
# The general lesson, which is why this comment is long: a variable can be
# correct in every observed case and still be wrong in principle, when every
# observation had the setter and the reader in the same repo.
_rt_bundled_julia="$REPRO_PROJECT_ROOT/.julia/pyjuliapkg/install/bin/julia"
if [[ -x "$_rt_bundled_julia" ]]; then
    export PYTHON_JULIAPKG_EXE="$_rt_bundled_julia"
else
    # No project-local Julia yet, so any value here came from somewhere else.
    unset PYTHON_JULIAPKG_EXE
fi
unset _rt_bundled_julia

# Strip juliaup from PATH unconditionally -- not only when there is no bundled
# Julia. Pinning PYTHON_JULIAPKG_EXE governs what juliacall launches, but it says
# nothing about anything that resolves `julia` through PATH, so leaving juliaup
# visible keeps a second Julia one lookup away. A self-contained project should
# not have one.
_rt_safe_path=""
IFS=':' read -r -a _rt_path_parts <<< "${PATH:-}"
for _rt_p in "${_rt_path_parts[@]}"; do
    # Lowercased compare, written for bash 3.2 (macOS ships it).
    case "$(echo "$_rt_p" | tr '[:upper:]' '[:lower:]')" in
        *juliaup*) continue ;;
    esac
    _rt_safe_path="${_rt_safe_path:+$_rt_safe_path:}$_rt_p"
done
export PATH="$_rt_safe_path"
unset _rt_safe_path _rt_path_parts _rt_p
