"""
repro-tools: Reproducibility tools for research and teaching.

Provides provenance tracking and publishing infrastructure for computational
research projects. Tracks git state, input/output checksums, and build metadata
to ensure full reproducibility.
"""

from repro_tools.core import (
    auto_build_record,
    git_state,
    now_utc_iso,
    sha256_file,
    write_build_record,
)
from repro_tools.publish import (
    copy_if_changed,
    load_yml,
    publish_analyses,
    publish_files,
    save_yml,
)

__version__ = "0.1.0"

__all__ = [
    # Core provenance
    "git_state",
    "sha256_file",
    "now_utc_iso",
    "write_build_record",
    "auto_build_record",
    # Publishing
    "publish_analyses",
    "publish_files",
    "load_yml",
    "save_yml",
    "copy_if_changed",
]
