#!/usr/bin/env python
"""Unified analysis runner - handles all studies via configuration."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from docopt import docopt

from repro_tools import auto_build_record, validate_study_config

# Add repo root to path so `shared` is importable when this is run as a script.
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# E402 is real here and cannot be fixed by moving the import: `shared` is only
# importable after the line above runs. Exempted at the single line that needs
# it rather than disabled repo-wide, so the rule keeps working everywhere else.
from shared.config import STUDIES  # noqa: E402

__doc__ = """
Usage:
  run_analysis.py <study> [options]
  run_analysis.py --list
  run_analysis.py --version

Arguments:
  <study>           Study name from config.STUDIES

Options:
  --list            List available studies
  --version         Show version

Example:
  run_analysis.py sample_analysis
"""


def main():
    args = docopt(__doc__)

    if args["--list"]:
        print("Available studies:")
        for name in STUDIES.keys():
            print(f"  - {name}")
        return

    if args["--version"]:
        print("run_analysis.py v1.0.0")
        return

    study_name = args["<study>"]

    if study_name not in STUDIES:
        print(f"❌ Error: Unknown study: {study_name}")
        print(f"Available: {', '.join(STUDIES.keys())}")
        sys.exit(1)

    config = STUDIES[study_name]

    # Validate configuration
    errors = validate_study_config(config, study_name)
    if errors:
        print(f"❌ Configuration errors in '{study_name}':")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    # Run analysis
    print(f"Running: {study_name}")

    # Load data
    df = pd.read_csv(config["data"])

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))
    if config.get("groupby"):
        for group in df[config["groupby"]].unique():
            subset = df[df[config["groupby"]] == group]
            ax.plot(
                subset[config["xvar"]],
                subset[config["yvar"]],
                marker="o",
                label=str(group),
            )
        ax.legend()
    else:
        ax.plot(df[config["xvar"]], df[config["yvar"]], marker="o")

    ax.set_xlabel(config["xlabel"])
    ax.set_ylabel(config["ylabel"])
    ax.set_title(config["title"])
    ax.grid(True, alpha=0.3)

    # Save figure
    config["figure"].parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(config["figure"], bbox_inches="tight", dpi=300)
    plt.close(fig)

    # Create table
    if config.get("groupby"):
        table = (
            df.groupby(config["groupby"])[config["yvar"]]
            .agg(config["table_agg"])
            .reset_index()
        )
    else:
        table = df[[config["xvar"], config["yvar"]]].describe()

    # Save table
    config["table"].parent.mkdir(parents=True, exist_ok=True)
    table.to_latex(config["table"], index=False)

    # Generate provenance
    prov_file = config["figure"].parent.parent / "provenance" / f"{study_name}.yml"
    prov_file.parent.mkdir(parents=True, exist_ok=True)

    auto_build_record(
        artifact_name=study_name,
        out_meta=prov_file,
        inputs=[config["data"]],
        outputs=[config["figure"], config["table"]],
    )

    print(f"✓ {study_name} complete")
    print(f"  Figure: {config['figure']}")
    print(f"  Table: {config['table']}")
    print(f"  Provenance: {prov_file}")


if __name__ == "__main__":
    main()
