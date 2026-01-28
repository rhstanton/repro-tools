"""Sample Julia script demonstrating Python/Julia interop via juliacall."""

import sys

print("=" * 60)
print("Sample Julia Script (via juliacall)")
print("=" * 60)
print()

try:
    from juliacall import Main as jl

    print(f"Julia version: {jl.seval('VERSION')}")
    print()

    # Simple Julia computation
    jl.seval(
        """
    println("Running Julia code from Python...")
    println()

    # Create a simple array
    x = [1, 2, 3, 4, 5]
    println("Array x: ", x)
    println("Mean: ", sum(x) / length(x))
    println("Sum: ", sum(x))
    println()
    """
    )

    # Python can call Julia functions
    result = jl.seval("sum([1, 2, 3, 4, 5])")
    print(f"Sum computed in Julia, returned to Python: {result}")
    print()

    print("✓ Julia example completed successfully")
    print("=" * 60)

except ImportError as e:
    print(f"✗ juliacall not available: {e}")
    print()
    print("Run 'make environment' to install Julia support")
    print("=" * 60)
    sys.exit(1)
