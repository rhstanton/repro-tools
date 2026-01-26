"""Project configuration - centralized paths and study definitions."""

from pathlib import Path

# ==============================================================================
# Directory Paths
# ==============================================================================

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUT_DIR = REPO_ROOT / "output"

# ==============================================================================
# Data Files
# ==============================================================================

DATA_FILES = {
    "sample": DATA_DIR / "sample.csv",
}

# ==============================================================================
# Study Definitions
# ==============================================================================

STUDIES = {
    "sample_analysis": {
        "data": DATA_FILES["sample"],
        "xlabel": "X Variable",
        "ylabel": "Y Variable",
        "title": "Sample Analysis",
        "groupby": None,
        "yvar": "y",
        "xvar": "x",
        "table_agg": "mean",
        "figure": OUTPUT_DIR / "figures" / "sample_analysis.pdf",
        "table": OUTPUT_DIR / "tables" / "sample_analysis.tex",
    },
}
