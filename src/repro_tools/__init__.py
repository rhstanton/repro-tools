"""
repro-tools: Reproducibility tools for research and teaching.

Provides provenance tracking, publishing infrastructure, and quality assurance
tools for computational research projects.
"""

from repro_tools.core import (
    auto_build_record,
    auto_provenance_from_config,
    enable_auto_provenance,
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
from repro_tools.compare import compare_outputs

__version__ = "0.2.0"

__all__ = [
    # Core provenance
    "git_state",
    "sha256_file",
    "now_utc_iso",
    "write_build_record",
    "auto_build_record",
    "auto_provenance_from_config",
    "enable_auto_provenance",
    # Publishing
    "publish_analyses",
    "publish_files",
    "load_yml",
    "save_yml",
    "copy_if_changed",
    # Comparison
    "compare_outputs",
]
