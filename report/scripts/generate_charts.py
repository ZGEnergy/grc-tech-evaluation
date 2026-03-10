#!/usr/bin/env python3
"""Chart generation for the Phase 1 Report Site.

Phase 1: Validates data files and produces an empty chart manifest.
Phase 2: Generates actual charts from the validated data.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPORT_DIR = SCRIPT_DIR.parent
DATA_DIR = REPORT_DIR / "data"
IMG_DIR = REPORT_DIR / "static" / "img"
MANIFEST_PATH = IMG_DIR / "chart-manifest.json"

GENERATOR_VERSION = "0.1.0"

# Data files and their required top-level keys
DATA_FILES: dict[str, list[str]] = {
    "grades.json": ["scale", "tools", "criteria", "grades"],
    "sensitivity.json": ["scenarios"],
    "risk-register.json": ["risks"],
    "head-to-head.json": ["capabilities"],
    "sweep-themes.json": ["themes"],
    "probe-results.json": ["probes"],
    "tool-profiles.json": ["tools"],
    "test-results.json": ["suites", "tools"],
}


def validate_data() -> dict[str, dict]:
    """Validate all data files exist, parse, and contain required keys.

    Returns:
        dict mapping filename to parsed data.

    Raises:
        SystemExit: if any validation fails.
    """
    print("Validating data files...")
    errors = []
    data = {}

    for filename, required_keys in DATA_FILES.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            errors.append(f"  {filename}: MISSING")
            continue

        try:
            with open(filepath) as f:
                parsed = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"  {filename}: INVALID JSON - {e}")
            continue

        missing_keys = [k for k in required_keys if k not in parsed]
        if missing_keys:
            errors.append(f"  {filename}: MISSING KEYS - {', '.join(missing_keys)}")
            continue

        print(
            f"  {filename}: OK"
            f" ({len(required_keys)} required key{'s' if len(required_keys) != 1 else ''})"
        )
        data[filename] = parsed

    if errors:
        print("\nValidation FAILED:")
        for error in errors:
            print(error)
        sys.exit(1)

    print(f"All {len(DATA_FILES)} data files validated successfully.\n")
    return data


def generate_charts(data: dict[str, dict]) -> list[dict]:
    """Generate chart assets from validated data.

    Phase 1: returns an empty list (no charts generated).
    Phase 2: returns list of ChartEntry dicts.
    """
    print("Generating charts...")
    print("  No charts to generate (Phase 1 skeleton)")
    return []


def write_manifest(charts: list[dict]) -> None:
    """Write the chart manifest JSON file."""
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_version": GENERATOR_VERSION,
        "charts": charts,
    }

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print(
        f"\nWrote chart manifest:"
        f" {MANIFEST_PATH.relative_to(REPORT_DIR)} ({len(charts)} charts)"
    )


def main() -> int:
    """Entry point. Returns 0 on success, 1 on failure."""
    try:
        data = validate_data()
        charts = generate_charts(data)
        write_manifest(charts)
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
