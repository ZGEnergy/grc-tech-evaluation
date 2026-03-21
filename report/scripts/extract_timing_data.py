#!/usr/bin/env python3
"""Extract timing data from evaluation scalability results into test-results.json.

Reads YAML frontmatter from evaluations/<tool>/results/scalability/C-*.md files,
extracts wall_clock_seconds where available, and appends a timing_records array
to report/data/test-results.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).parent
REPORT_DIR = SCRIPT_DIR.parent
WORKSPACE_ROOT = REPORT_DIR.parent
DATA_DIR = REPORT_DIR / "data"

# Test ID → benchmark type mapping (no spaces — used in chart filenames)
BENCHMARK_TYPES: dict[str, str] = {
    "C-1": "DCPF",
    "C-2": "ACPF",
    "C-3": "DCOPF",
    "C-4": "SCUC",
    "C-5": "Contingency",
    "C-6": "Stochastic",
    "C-7": "SolverSwap",
    "C-8": "SCOPF",
    "C-9": "PTDF",
    "C-10": "DistributedSlack",
}

# Network label → approximate bus count
NETWORK_SIZES: dict[str, int] = {
    "TINY": 39,
    "SMALL": 2000,
    "MEDIUM": 10000,
}

TOOLS = [
    "pypsa",
    "pandapower",
    "powermodels",
    "matpower",
    "gridcal",
    "powersimulations",
]


def parse_frontmatter(filepath: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def extract_timing_records() -> list[dict]:
    """Walk all evaluation scalability results and extract timing records."""
    records: list[dict] = []

    for tool in TOOLS:
        scalability_dir = (
            WORKSPACE_ROOT / "evaluations" / tool / "results" / "scalability"
        )
        if not scalability_dir.exists():
            print(f"  {tool}: no scalability directory")
            continue

        md_files = sorted(scalability_dir.glob("C-*.md"))
        tool_count = 0

        for md_file in md_files:
            fm = parse_frontmatter(md_file)
            if fm is None:
                continue

            test_id = str(fm.get("test_id", ""))
            # Normalize test_id: some files have "C-1", others might have full names
            base_test_id = test_id.split("_")[0] if "_" in test_id else test_id

            if base_test_id not in BENCHMARK_TYPES:
                continue

            network = str(fm.get("network", "")).upper()
            if network not in NETWORK_SIZES:
                continue

            status = str(fm.get("status", "skip"))
            wall_clock = fm.get("wall_clock_seconds")

            # Only include records with actual timing data or pass/fail status
            if wall_clock is not None:
                solve_time = float(wall_clock)
            elif status in ("pass", "qualified_pass", "fail"):
                solve_time = 0.0  # no timing but has a result
            else:
                continue  # skip entries have no useful data

            records.append(
                {
                    "tool": tool,
                    "benchmark_type": BENCHMARK_TYPES[base_test_id],
                    "network_size": NETWORK_SIZES[network],
                    "solve_time_seconds": solve_time,
                    "status": status,
                }
            )
            tool_count += 1

        print(f"  {tool}: {tool_count} timing records")

    return records


def main() -> None:
    print("Extracting timing data from evaluation results...")
    records = extract_timing_records()

    # Load existing test-results.json
    test_results_path = DATA_DIR / "test-results.json"
    with open(test_results_path) as f:
        data = json.load(f)

    # Add/replace timing_records
    data["timing_records"] = records

    with open(test_results_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nWrote {len(records)} timing records to {test_results_path.name}")


if __name__ == "__main__":
    main()
