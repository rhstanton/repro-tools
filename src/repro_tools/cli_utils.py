"""
Command-line interface utilities for research workflows.

Provides enhanced docopt parsing, configuration display, environment detection,
and parsing utilities commonly used in analysis scripts.

Copyright (c) 2026 Richard Stanton
License: MIT
"""

import difflib
import os
import re
import sys

from docopt import DocoptExit, docopt


def friendly_docopt(doc: str, *, version: str | None = None) -> dict:
    """
    Parse arguments with helpful error messages for unknown options.

    Args:
        doc: Docstring with usage information
        version: Version string for --version flag

    Returns:
        Dict of parsed arguments

    Example:
        >>> doc = '''Usage: script.py [--output=<path>]'''
        >>> args = friendly_docopt(doc)
        # If user types --outpt (typo), suggests: "Did you mean --output?"
    """
    argv = sys.argv[1:]

    try:
        return docopt(doc, argv=argv, version=version, help=True)
    except DocoptExit as e:
        # Extract valid options from docstring
        long_opts = set(re.findall(r"--([A-Za-z0-9][\w-]*)", doc))
        short_opts = set(re.findall(r"(?:^|\s)-([A-Za-z])\b", doc))

        # Find unknown options in argv
        bad_opts = []
        for token in argv:
            if token.startswith("--"):
                name = token[2:].split("=")[0]
                if name and name not in long_opts:
                    bad_opts.append(token)
            elif token.startswith("-") and token != "-" and not token.startswith("--"):
                for char in token[1:]:
                    if char not in short_opts:
                        bad_opts.append(f"-{char}")

        if bad_opts:
            print(e.usage.strip())
            for bad in sorted(set(bad_opts)):
                if bad.startswith("--"):
                    matches = difflib.get_close_matches(bad[2:], list(long_opts), n=1)
                    hint = f"Unknown option {bad}."
                    if matches:
                        hint += f" Did you mean --{matches[0]}?"
                else:
                    matches = difflib.get_close_matches(bad[1:], list(short_opts), n=1)
                    hint = f"Unknown option {bad}."
                    if matches:
                        hint += f" Did you mean -{matches[0]}?"
                print(f"\n{hint}")
            sys.exit(2)

        raise


def print_header(docstring: str) -> None:
    """
    Print script name and description from docstring.

    Args:
        docstring: Script docstring containing name and description

    Example:
        >>> print_header(__doc__)
        # Prints: script.py: Description of the script
    """
    script_name = "script.py"
    description = ""

    if docstring:
        # Extract script name
        match = re.search(r"(\w+\.py)", docstring)
        if match:
            script_name = match.group(1)

        # Extract first non-empty, non-usage line as description
        for line in docstring.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("Usage:"):
                description = line
                break

    print(f"\n{script_name}: {description}\n")


def print_config(config: dict, title: str = "CONFIGURATION") -> None:
    """
    Pretty-print configuration dictionary.

    Args:
        config: Configuration dictionary to display
        title: Header title

    Example:
        >>> config = {"input": "data.csv", "limit": 100}
        >>> print_config(config)
        # Prints formatted table with keys and values
    """
    print("=" * 72)
    print(title)
    print("=" * 72)

    if not config:
        print("(empty)")
        print("=" * 72 + "\n")
        return

    max_key_len = max(len(str(k)) for k in config.keys())

    for key, value in config.items():
        display_value = value if value is not None else "None"
        print(f"{str(key):<{max_key_len}} : {display_value}")

    print("=" * 72 + "\n")


def parse_csv_list(value: str | None) -> list[str]:
    """
    Parse comma-separated string into list.

    Args:
        value: Comma-separated string or None

    Returns:
        List of trimmed non-empty strings

    Example:
        >>> parse_csv_list("a, b,  c")
        ['a', 'b', 'c']
    """
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_int_or_auto(value: str | None, default=None) -> int | None:
    """
    Parse integer option that may be 'auto' or empty.

    Args:
        value: String value to parse
        default: Default value if 'auto' or None

    Returns:
        Parsed integer or default

    Example:
        >>> parse_int_or_auto("100")
        100
        >>> parse_int_or_auto("auto", default=10)
        10
    """
    if value is None:
        return default

    s = str(value).strip().lower()
    if s in ("auto", ""):
        return default

    return int(s)


def parse_float_or_auto(value: str | None, default=None) -> float | None:
    """
    Parse float option that may be 'auto' or empty.

    Args:
        value: String value to parse
        default: Default value if 'auto' or None

    Returns:
        Parsed float or default

    Example:
        >>> parse_float_or_auto("3.14")
        3.14
        >>> parse_float_or_auto("auto", default=1.0)
        1.0
    """
    if value is None:
        return default

    s = str(value).strip().lower()
    if s in ("auto", ""):
        return default

    return float(s)


def parse_string_or_auto(value: str | None, default=None) -> str | None:
    """
    Parse string option that may be 'auto' or empty.

    Args:
        value: String value to parse
        default: Default value if 'auto' or None

    Returns:
        Parsed string or default

    Example:
        >>> parse_string_or_auto("custom")
        'custom'
        >>> parse_string_or_auto("auto", default="default")
        'default'
    """
    if value is None:
        return default

    s = str(value).strip().lower()
    if s in ("auto", ""):
        return default

    return str(value).strip()


class ConfigBuilder:
    """
    Builder for constructing configuration from command-line arguments.

    Example:
        >>> builder = ConfigBuilder(args)
        >>> builder.add("input_path", lambda: args["--input"])
        >>> builder.add("limit", lambda: int(args["--limit"]) if args["--limit"] else None)
        >>> config = builder.build()
        # Prints formatted configuration and returns dict
    """

    def __init__(self, args: dict):
        self.args = args
        from typing import Callable

        self._specs: list[tuple[str, str, Callable]] = []

    def add(self, key: str, parser_fn, display_name: str | None = None):
        """
        Add a configuration option.

        Args:
            key: Configuration key
            parser_fn: Function that parses the value from args
            display_name: Optional display name (defaults to formatted key)

        Returns:
            self for chaining
        """
        if display_name is None:
            display_name = key.replace("_", " ").title()

        self._specs.append((key, display_name, parser_fn))
        return self

    def build(self, print_output: bool = True) -> dict:
        """
        Build configuration dictionary.

        Args:
            print_output: Whether to print the configuration

        Returns:
            Configuration dictionary
        """
        config = {}

        if print_output:
            print("=" * 72)
            print("CONFIGURATION")
            print("=" * 72)

            max_display_len = max(len(display) for _, display, _ in self._specs)

        for key, display, parser_fn in self._specs:
            value = parser_fn()
            config[key] = value

            if print_output:
                display_value = value if value is not None else "None"
                print(f"{display:<{max_display_len}} : {display_value}")

        if print_output:
            print("=" * 72 + "\n")

        return config


def filter_ipython_args():
    """
    Remove IPython-specific arguments from sys.argv.

    Modifies sys.argv in-place to remove IPython flags that would
    cause issues with docopt parsing.

    Example:
        # If sys.argv contains ['script.py', '--simple-prompt', '--input=data.csv']
        >>> filter_ipython_args()
        # sys.argv becomes ['script.py', '--input=data.csv']
    """
    ipython_flags = {
        "--simple-prompt",
        "-i",
        "--InteractiveShell.ast_node_interactivity=all",
        "--profile-dir",
        "--ipython-dir",
        "--colors",
        "--quick",
        "--classic",
        "--autoindent",
        "--no-autoindent",
        "--automagic",
        "--no-automagic",
        "--pdb",
        "--no-pdb",
        "--pprint",
        "--no-pprint",
        "--color-info",
        "--no-color-info",
        "--nosep",
        "--term-title",
        "--no-term-title",
        "--banner",
        "--no-banner",
        "--confirm-exit",
        "--no-confirm-exit",
    }

    filtered = [sys.argv[0]]  # Keep script name

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        # Skip IPython flags
        if arg in ipython_flags:
            i += 1
            continue

        # Skip IPython flags with value (--flag=value)
        if any(arg.startswith(flag + "=") for flag in ipython_flags):
            i += 1
            continue

        # Skip IPython config (--Module.option=value)
        if arg.startswith("--") and "." in arg and "=" in arg:
            i += 1
            continue

        # Keep this argument
        filtered.append(arg)
        i += 1

    sys.argv = filtered


def get_execution_environment() -> str:
    """
    Detect execution environment.

    Returns:
        One of: 'jupyter', 'ipython', 'emacs-jupyter', 'emacs-python',
                'emacs-ipython', 'emacs-batch', 'terminal', 'batch'

    Example:
        >>> env = get_execution_environment()
        >>> print(env)
        'terminal'  # or 'jupyter', 'ipython', etc.
    """
    in_emacs = bool(os.environ.get("INSIDE_EMACS"))

    # Check for IPython/Jupyter
    try:
        shell = get_ipython().__class__.__name__  # type: ignore[name-defined]
        if "ZMQ" in shell or "Notebook" in shell:
            return "emacs-jupyter" if in_emacs else "jupyter"
        # Regular IPython
        return "emacs-ipython" if in_emacs else "ipython"
    except NameError:
        pass

    # Not IPython - check for Emacs
    if in_emacs:
        term = os.environ.get("TERM", "")

        # If TERM is dumb or not set, likely compilation buffer
        if not term or term == "dumb":
            return "emacs-batch"

        # Interactive Emacs with regular Python
        if sys.stdin.isatty():
            return "emacs-python"

        return "emacs-batch"

    # Check if running interactively at command line
    if sys.stdin.isatty():
        return "terminal"

    return "batch"


def setup_environment():
    """
    Detect execution environment and filter IPython arguments.

    Returns:
        Environment type string

    Example:
        >>> env = setup_environment()
        Execution environment: terminal
        >>> print(env)
        'terminal'
    """
    env = get_execution_environment()
    print(f"Execution environment: {env}\n")

    # Filter out IPython arguments
    if env in ["ipython", "emacs-ipython", "jupyter", "emacs-jupyter"]:
        filter_ipython_args()

    return env
