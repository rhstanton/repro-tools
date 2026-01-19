"""
Configuration validation utilities for research workflows.

Provides user-friendly error display for configuration validation.

Copyright (c) 2026 Richard Stanton
License: MIT
"""


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
