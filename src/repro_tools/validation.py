"""
Configuration validation utilities for research workflows.

Provides validation functions and user-friendly error display.

Copyright (c) 2026 Richard Stanton
License: MIT
"""

from pathlib import Path


def validate_study_config(
    config: dict,
    study_name: str,
    *,
    required_keys: list[str] | None = None,
    valid_aggregations: list[str] | None = None,
) -> list[str]:
    """
    Validate study configuration dictionary.

    Args:
        config: Study configuration dictionary
        study_name: Name of the study being validated
        required_keys: List of required config keys (default: standard analysis keys)
        valid_aggregations: List of valid aggregation functions (default: standard pandas aggs)

    Returns:
        List of error messages (empty if valid)

    Example:
        >>> config = {
        ...     "data": "data/housing.csv",
        ...     "xlabel": "Year",
        ...     "ylabel": "Price",
        ...     "yvar": "price",
        ...     "xvar": "year",
        ...     "figure": "output/figures/price.pdf",
        ...     "table": "output/tables/price.tex",
        ... }
        >>> errors = validate_study_config(config, "price_base")
        >>> assert len(errors) == 0  # Valid config
    """
    errors = []

    # =========================================================================
    # Required Keys
    # =========================================================================

    if required_keys is None:
        required_keys = ["data", "xlabel", "ylabel", "yvar", "xvar", "figure", "table"]

    for key in required_keys:
        if key not in config or config[key] is None:
            errors.append(f"Missing required config for '{study_name}': {key}")

    # =========================================================================
    # File Existence
    # =========================================================================

    data_path = config.get("data")
    if data_path:
        data_file = Path(data_path).expanduser()
        if not data_file.exists():
            errors.append(f"Input file not found: {data_file}")
            errors.append(f"  Expected location: {data_file.absolute()}")

    # =========================================================================
    # Output Paths
    # =========================================================================

    for output_key in ["figure", "table"]:
        output_path = config.get(output_key)
        if output_path:
            output_file = Path(output_path)
            output_dir = output_file.parent

            # Check that parent directory exists or can be created
            if not output_dir.exists():
                try:
                    output_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create output directory {output_dir}: {e}")

    # =========================================================================
    # Variable Names
    # =========================================================================

    for var_name in ["xlabel", "ylabel", "yvar", "xvar", "groupby"]:
        value = config.get(var_name)
        if value and not isinstance(value, str):
            errors.append(f"{var_name} must be a string, got: {type(value).__name__}")

    # =========================================================================
    # Aggregation Function
    # =========================================================================

    table_agg = config.get("table_agg")
    if table_agg:
        if valid_aggregations is None:
            valid_aggregations = ["mean", "sum", "median", "min", "max", "count", "std", "var"]
        
        if table_agg not in valid_aggregations:
            errors.append(
                f"Invalid table_agg '{table_agg}'. Must be one of: {', '.join(valid_aggregations)}"
            )

    return errors


def print_validation_errors(errors: list[str]) -> None:
    """
    Print validation errors in a user-friendly format.

    Args:
        errors: List of error messages

    Example:
        >>> errors = [
        ...     "Missing required config: data",
        ...     "Input file not found: data.csv",
        ... ]
        >>> print_validation_errors(errors)
        # Prints formatted error list with emojis and line numbers
    """
    print("\n" + "=" * 72)
    print("❌ Configuration Validation Failed")
    print("=" * 72)
    print(f"\nFound {len(errors)} error(s):\n")

    for i, error in enumerate(errors, 1):
        # Check if error starts with spaces (continuation line)
        if error.startswith("  "):
            print(f"  {error}")
        else:
            print(f"{i}. {error}")

    print("\n" + "=" * 72)
    print("💡 Fix these issues and try again")
    print("=" * 72 + "\n")
