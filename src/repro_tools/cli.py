"""Command-line interface for repro-tools."""

import argparse
import sys
from pathlib import Path


def record_provenance():
    """CLI entry point for repro-record command."""
    from repro_tools import auto_build_record

    parser = argparse.ArgumentParser(description="Record build provenance")
    parser.add_argument(
        "--out-meta", type=Path, required=True, help="Output provenance YAML"
    )
    parser.add_argument(
        "--inputs", nargs="+", type=Path, required=True, help="Input files"
    )
    parser.add_argument(
        "--outputs", nargs="+", type=Path, required=True, help="Output files"
    )
    parser.add_argument("--artifact-name", help="Override auto-detected artifact name")
    parser.add_argument(
        "--repo-root", type=Path, help="Override auto-detected repo root"
    )

    args = parser.parse_args()

    auto_build_record(
        out_meta=args.out_meta,
        inputs=args.inputs,
        outputs=args.outputs,
        artifact_name=args.artifact_name,
        repo_root=args.repo_root,
    )
    print(f"✓ Provenance recorded: {args.out_meta}")


def publish():
    """CLI entry point for repro-publish command."""
    from repro_tools import publish_analyses, publish_files

    parser = argparse.ArgumentParser(description="Publish artifacts to paper directory")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    # Analyses mode
    analyses_parser = subparsers.add_parser(
        "analyses", help="Publish all outputs from analyses"
    )
    analyses_parser.add_argument(
        "analyses", nargs="+", help="Analysis names to publish"
    )
    analyses_parser.add_argument(
        "--paper-root", type=Path, required=True, help="Paper directory"
    )
    analyses_parser.add_argument(
        "--project-root",
        type=Path,
        required=True,
        help="Project/analysis repository root",
    )
    analyses_parser.add_argument(
        "--allow-dirty", type=int, default=0, help="Allow dirty working tree"
    )
    analyses_parser.add_argument(
        "--require-not-behind", type=int, default=1, help="Require branch up-to-date"
    )
    analyses_parser.add_argument(
        "--require-current-head",
        type=int,
        default=0,
        help="Require artifacts from current HEAD",
    )
    # publish_analyses has always accepted `kinds`; the CLI just never exposed
    # it. Makefiles publish figures and tables under separate stamps so that
    # touching one table does not republish every figure, and they were passing
    # `--kind figures` to a parser that had no such option.
    analyses_parser.add_argument(
        "--kind",
        action="append",
        dest="kinds",
        choices=["figures", "tables"],
        help="Restrict to one artifact kind; repeatable. Default: all kinds.",
    )

    # Files mode
    files_parser = subparsers.add_parser("files", help="Publish specific files")
    files_parser.add_argument("files", nargs="+", type=Path, help="Files to publish")
    files_parser.add_argument(
        "--paper-root", type=Path, required=True, help="Paper directory"
    )
    files_parser.add_argument(
        "--project-root",
        type=Path,
        required=True,
        help="Project/analysis repository root",
    )
    files_parser.add_argument(
        "--allow-dirty", type=int, default=0, help="Allow dirty working tree"
    )
    files_parser.add_argument(
        "--require-not-behind", type=int, default=1, help="Require branch up-to-date"
    )

    args = parser.parse_args()

    if args.mode == "analyses":
        publish_analyses(
            project_root=args.project_root,
            paper_root=args.paper_root,
            analysis_names=args.analyses,
            kinds=args.kinds,
            allow_dirty=bool(args.allow_dirty),
            require_not_behind=bool(args.require_not_behind),
            require_current_head=bool(args.require_current_head),
        )
    else:  # files
        publish_files(
            project_root=args.project_root,
            paper_root=args.paper_root,
            file_paths=args.files,
            allow_dirty=bool(args.allow_dirty),
            require_not_behind=bool(args.require_not_behind),
        )


def compare():
    """CLI entry point for repro-compare command."""
    from repro_tools.compare import compare_outputs

    parser = argparse.ArgumentParser(description="Compare current vs reference outputs")
    parser.add_argument(
        "--reference",
        type=Path,
        default="paper",
        help="Reference directory (default: paper)",
    )
    parser.add_argument("--artifacts", nargs="*", help="Specific artifacts to compare")
    parser.add_argument(
        "--current-dir", type=Path, default="output", help="Current output directory"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed diff output"
    )

    args = parser.parse_args()

    # No reference to compare against is not a failure -- a project has no
    # published outputs until it publishes. Handled before compare_outputs,
    # which cannot distinguish "nothing to compare" from "compared and differed"
    # (it returns False for both), and exiting 1 here would make
    # `make diff-outputs` red on arrival in every fresh project.
    reference = Path(args.reference)
    if not reference.exists():
        print(f"No reference directory at {reference}; nothing to compare.")
        print("Not a failure: point --reference at published outputs once there")
        print("are some.")
        sys.exit(0)

    all_identical, report = compare_outputs(
        current_dir=Path(args.current_dir),
        reference_dir=reference,
        artifacts=args.artifacts,
        verbose=args.verbose,
    )

    print(report)
    # THE EXIT STATUS IS THE POINT.
    #
    # This used to compute all_identical and then `sys.exit(0)` regardless, so
    # `make diff-outputs` -- announced as "Comparing current outputs with
    # published outputs" -- passed whether or not they matched. A comparison
    # that always succeeds is not a comparison; anything reading the exit code,
    # CI included, was being told the outputs agreed without anyone having
    # checked.
    sys.exit(0 if all_identical else 1)


def sysinfo():
    """CLI entry point for repro-sysinfo command."""
    from repro_tools.sysinfo import main as sysinfo_main

    sysinfo_main()


def presubmit():
    """CLI entry point for repro-check command."""
    from repro_tools.presubmit import main as presubmit_main

    sys.exit(presubmit_main())


def report_gen():
    """CLI entry point for repro-report command."""
    from repro_tools.report import main as report_main

    report_main()


def template_diff():
    """CLI entry point for repro-template-diff command.

    template_update.main takes argv explicitly, so this wraps it: a console
    script is called with no arguments. Until 2026-08-17 there was no entry
    point at all, and the module's own docstring advertised an invocation
    (`repro-tools template-diff`) that had never existed -- so the "apply
    template updates to existing projects" feature was written, tested, and
    unreachable.
    """
    from repro_tools.template_update import main as template_diff_main

    sys.exit(template_diff_main(sys.argv[1:]))


# ==============================================================================
# Module entry point
# ==============================================================================
#
# WHY THIS EXISTS, AND WHAT ITS ABSENCE COST
#
# Every console script above is reachable as `repro-publish`, `repro-check` and
# so on. But project Makefiles do not call the console scripts -- they call the
# module, so that the interpreter is the project's own .venv rather than
# whatever is first on PATH:
#
#     REPRO_PUBLISH := $(PYTHON) -m repro_tools.cli publish
#
# Until 2026-08-17 this file had no `if __name__ == "__main__"` block. A module
# run with `-m` and no such block is simply IMPORTED: every function definition
# executes, no function is called, every argument is ignored, and the process
# exits 0. So the command above did nothing, successfully, and make -- seeing a
# zero exit -- proceeded to `touch` the stamp that records the work as done.
#
# In project_template that silently disabled `make publish`, `make diff-outputs`,
# `make pre-submit`, `make pre-submit-strict` and `make replication-report`: the
# entire publishing and verification surface, including the git safety gates
# that are the reason publishing is supposed to be the only sanctioned route
# from output/ into paper/. `make publish` printed "Publishing complete!" over
# a paper/ directory it had not touched since January.
#
# Demonstration of the failure mode, which is worth keeping because it looks
# exactly like success:
#
#     $ python -m repro_tools.cli publish --nonsense-flag-that-does-not-exist
#     $ echo $?
#     0
#
# An unrecognized flag is the cheapest possible probe for "is anything parsing
# my arguments", and it answered no.
#
# The dispatcher below maps a subcommand onto the same functions the console
# scripts use, so there is one implementation and two ways in. sys.argv is
# rewritten so that argparse inside each function reports the name a user typed.


def lib_path():
    """CLI entry point: print the directory holding common.mk / stata.mk / env.sh.

    Exists so a Makefile can locate the shared machinery without knowing whether
    repro-tools is a vendored submodule or an installed package:

        REPRO_LIB := $(shell $(PYTHON) -m repro_tools.cli lib-path)
        include $(REPRO_LIB)/common.mk

    It parses arguments even though it takes none. The first version just
    printed and returned, which meant `lib-path --nonsense` exited 0 -- and the
    suite caught it immediately, because that is precisely the failure this
    package spent a day fixing: a command that ignores its input cannot tell you
    that you asked for something it does not do.
    """
    from repro_tools.core import lib_dir

    parser = argparse.ArgumentParser(
        prog="repro-lib-path",
        description=(
            "Print the directory containing the shared build machinery "
            "(common.mk, stata.mk, env.sh)."
        ),
    )
    parser.parse_args()
    print(lib_dir())


_COMMANDS = {
    "lib-path": lib_path,
    "record": record_provenance,
    "publish": publish,
    "compare": compare,
    "sysinfo": sysinfo,
    "check": presubmit,
    "report": report_gen,
    "template-diff": template_diff,
}


def main(argv=None) -> int:
    """Dispatch `python -m repro_tools.cli <command> [args...]`.

    Returns an exit status rather than calling sys.exit, so it is testable.
    An unknown or missing command is an error (status 2), never a silent
    success -- that was the whole defect.
    """
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help"):
        _print_usage()
        return 0 if argv else 2

    command, rest = argv[0], argv[1:]
    if command not in _COMMANDS:
        print(f"repro-tools: unknown command {command!r}", file=sys.stderr)
        _print_usage(sys.stderr)
        return 2

    # argparse reads sys.argv, so present it the command the user typed.
    saved = sys.argv
    sys.argv = [f"repro-{command}", *rest]
    try:
        result = _COMMANDS[command]()
    finally:
        sys.argv = saved
    return 0 if result is None else int(result)


def _print_usage(stream=None) -> None:
    stream = stream or sys.stdout
    print("usage: python -m repro_tools.cli <command> [args...]", file=stream)
    print("", file=stream)
    print("commands:", file=stream)
    for name in _COMMANDS:
        print(f"  {name}", file=stream)
    print("", file=stream)
    print(
        "Each command also exists as a console script, e.g. `repro-publish`.",
        file=stream,
    )


if __name__ == "__main__":
    sys.exit(main())
