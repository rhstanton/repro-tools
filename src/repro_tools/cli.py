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

    all_identical, report = compare_outputs(
        current_dir=Path(args.current_dir),
        reference_dir=Path(args.reference),
        artifacts=args.artifacts,
        verbose=args.verbose,
    )

    print(report)
    sys.exit(0)


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
