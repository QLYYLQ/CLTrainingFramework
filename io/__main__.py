"""
CLI entry point for generating IO type stubs.

Usage:
    python -m CLTrainingFramework.io
"""

from CLTrainingFramework.io.stub_generator import generate_io_stubs, print_registry_summary

if __name__ == "__main__":
    print("=" * 50)
    print("IO Type Stub Generator")
    print("=" * 50)
    print()

    print_registry_summary()
    print()

    output_file = generate_io_stubs()
    print(f"Stub file generated: {output_file}")
    print()
    print("PyCharm should now provide type hints for IO.load()")