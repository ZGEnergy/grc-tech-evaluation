"""CLI entry point for validating FNM_PATH configuration.

Provides a human-readable summary of the FNM_PATH environment variable status,
including per-file found/missing markers for developer onboarding and debugging.
"""

from __future__ import annotations

import argparse
import sys

from fnm.scripts.fnm_gating import FnmFileStatus, FnmPathStatus, resolve_fnm_path


def cli_validate_fnm_path(args: list[str] | None = None) -> int:
    """CLI entry point for validating FNM_PATH.

    Resolves FNM_PATH and prints a human-readable report of the validation result.

    Args:
        args: Command-line arguments. If None, reads from sys.argv.

    Returns:
        Exit code: 0 if VALID, 1 otherwise.
    """
    parser = argparse.ArgumentParser(
        prog="validate-fnm-path",
        description="Validate the FNM_PATH environment variable and check for expected files.",
    )
    parser.parse_args(args)

    result = resolve_fnm_path()

    print(f"FNM_PATH Status: {result.status.value}")
    print()

    if result.status == FnmPathStatus.NOT_SET:
        print("FNM_PATH environment variable is not set.")
        print()
        print("To configure:")
        print("  export FNM_PATH=/path/to/fnm/data")
        print()
        print("See data/fnm/README.md for setup instructions.")
        return 1

    if result.status == FnmPathStatus.INVALID_PATH:
        print(f"FNM_PATH is set to '{result.fnm_path}' but this is not a valid directory.")
        return 1

    if result.status == FnmPathStatus.MANIFEST_ERROR:
        print(f"Error: {result.message}")
        return 1

    print(f"FNM_PATH: {result.fnm_path}")
    print()

    if result.file_checks:
        print("File checks:")
        for fc in result.file_checks:
            marker = "[FOUND]" if fc.status == FnmFileStatus.FOUND else "[MISSING]"
            print(f"  {marker} {fc.expected_name}")
        print()

    found_count = len(result.found_files)
    missing_count = len(result.missing_files)
    total = len(result.file_checks)
    print(f"Summary: {found_count}/{total} files found, {missing_count} missing.")

    if result.status == FnmPathStatus.VALID:
        print("Status: All expected files are present.")
        return 0

    print("Status: Some files are missing. Verify your FNM data directory is complete.")
    return 1


if __name__ == "__main__":
    sys.exit(cli_validate_fnm_path())
