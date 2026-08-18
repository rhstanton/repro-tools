"""
repro-tools: Reproducibility library for research and teaching.

Provides provenance tracking, publishing infrastructure, and quality assurance
tools for computational research projects.

This is a library package only. For creating new projects, see:
https://github.com/rhstanton/project_template
"""

from repro_tools.cli_utils import (
    ConfigBuilder,
    filter_ipython_args,
    friendly_docopt,
    get_execution_environment,
    parse_csv_list,
    parse_float_or_auto,
    parse_int_or_auto,
    parse_string_or_auto,
    print_config,
    print_header,
    setup_environment,
)
from repro_tools.compare import compare_outputs
from repro_tools.core import (
    auto_build_record,
    auto_provenance_from_config,
    enable_auto_provenance,
    git_state,
    now_utc_iso,
    resolve_recorded_path,
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
from repro_tools.validation import print_validation_errors, validate_study_config

__version__ = "0.2.0"

__all__ = [
    # Core provenance
    "git_state",
    "sha256_file",
    "now_utc_iso",
    "write_build_record",
    "resolve_recorded_path",
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
    # CLI utilities
    "friendly_docopt",
    "print_header",
    "print_config",
    "parse_csv_list",
    "parse_int_or_auto",
    "parse_float_or_auto",
    "parse_string_or_auto",
    "ConfigBuilder",
    "filter_ipython_args",
    "get_execution_environment",
    "setup_environment",
    # Validation
    "print_validation_errors",
    "validate_study_config",
]
