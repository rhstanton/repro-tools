"""Command-line interface for repro-tools."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from repro_tools import publish_analyses, publish_files, write_build_record


def record_provenance() -> None:
    """Command-line tool for recording build provenance."""
    ap = argparse.ArgumentParser(
        description="Record build provenance for an artifact"
    )
    ap.add_argument("--artifact", required=True, help="Artifact name")
    ap.add_argument("--out-meta", type=Path, required=True, help="Output provenance YAML")
    ap.add_argument("--inputs", nargs="+", type=Path, required=True, help="Input files")
    ap.add_argument("--outputs", nargs="+", type=Path, required=True, help="Output files")
    ap.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root")
    ap.add_argument("--command", nargs="*", help="Override command (default: sys.argv)")
    args = ap.parse_args()
    
    command = args.command if args.command else sys.argv
    
    write_build_record(
        out_meta=args.out_meta,
        artifact_name=args.artifact,
        command=command,
        repo_root=args.repo_root,
        inputs=args.inputs,
        outputs=args.outputs,
    )
    
    print(f"✓ Provenance recorded: {args.out_meta}")


def publish() -> None:
    """Command-line tool for publishing artifacts."""
    ap = argparse.ArgumentParser(
        description="Publish outputs to paper directory"
    )
    subparsers = ap.add_subparsers(dest="mode", required=True)
    
    # Analysis-level publishing
    analyses_parser = subparsers.add_parser(
        "analyses",
        help="Publish complete analyses (all outputs per analysis)"
    )
    analyses_parser.add_argument("--project-root", type=Path, default=Path("."))
    analyses_parser.add_argument("--paper-root", type=Path, required=True)
    analyses_parser.add_argument("--names", required=True, help="Space-separated analysis names")
    analyses_parser.add_argument("--kinds", nargs="+", default=["figures", "tables"])
    analyses_parser.add_argument("--allow-dirty", action="store_true")
    analyses_parser.add_argument("--no-require-not-behind", dest="require_not_behind", action="store_false")
    analyses_parser.add_argument("--require-current-head", action="store_true")
    
    # File-level publishing
    files_parser = subparsers.add_parser(
        "files",
        help="Publish specific output files"
    )
    files_parser.add_argument("--project-root", type=Path, default=Path("."))
    files_parser.add_argument("--paper-root", type=Path, required=True)
    files_parser.add_argument("--files", required=True, help="Space-separated file paths")
    files_parser.add_argument("--allow-dirty", action="store_true")
    files_parser.add_argument("--no-require-not-behind", dest="require_not_behind", action="store_false")
    
    args = ap.parse_args()
    
    if args.mode == "analyses":
        names = [n.strip() for n in args.names.split() if n.strip()]
        print(f"Publishing analyses: {', '.join(names)}")
        
        publish_analyses(
            project_root=args.project_root,
            paper_root=args.paper_root,
            analysis_names=names,
            kinds=args.kinds,
            allow_dirty=args.allow_dirty,
            require_not_behind=args.require_not_behind,
            require_current_head=args.require_current_head,
        )
        
        print(f"✓ Published to {args.paper_root}/provenance.yml")
        
    elif args.mode == "files":
        files = [Path(f.strip()) for f in args.files.split() if f.strip()]
        print(f"Publishing {len(files)} file(s)")
        
        publish_files(
            project_root=args.project_root,
            paper_root=args.paper_root,
            file_paths=files,
            allow_dirty=args.allow_dirty,
            require_not_behind=args.require_not_behind,
        )
        
        print(f"✓ Published to {args.paper_root}/provenance.yml")


if __name__ == "__main__":
    publish()
