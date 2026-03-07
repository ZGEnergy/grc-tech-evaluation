"""Gate tests for GridCal: network ingestion checks for G-1, G-2, G-3."""

from __future__ import annotations

import math
import time
from pathlib import Path

# Reference counts from MATPOWER .m files (rows in mpc.bus, mpc.branch, mpc.gen)
REFERENCE = {
    "G-1": {
        "file": "case39.m",
        "tier": "TINY",
        "label": "IEEE 39-bus",
        "buses": 39,
        "branches": 46,
        "generators": 10,
    },
    "G-2": {
        "file": "case_ACTIVSg2000.m",
        "tier": "SMALL",
        "label": "ACTIVSg 2k",
        "buses": 2000,
        "branches": 3206,
        "generators": 544,
    },
    "G-3": {
        "file": "case_ACTIVSg10k.m",
        "tier": "MEDIUM",
        "label": "ACTIVSg 10k",
        "buses": 10000,
        "branches": 12706,
        "generators": 2485,
    },
}


def _load_grid(data_dir: Path, test_id: str):
    """Load a grid and return (grid, load_time_seconds)."""
    import VeraGridEngine as vge

    ref = REFERENCE[test_id]
    filepath = str(data_dir / ref["file"])
    t0 = time.perf_counter()
    grid = vge.open_file(filepath)
    load_time = time.perf_counter() - t0
    return grid, load_time


def _count_branches(grid) -> int:
    """Count total branches: lines + transformers2w + transformers3w."""
    n = len(grid.lines) + len(grid.transformers2w)
    if hasattr(grid, "transformers3w"):
        n += len(grid.transformers3w)
    return n


def _audit_grid(grid, test_id: str) -> list[str]:
    """Post-import data quality audit. Returns list of warnings."""
    warnings = []

    # Check bus voltages for NaN/inf
    for bus in grid.buses:
        if math.isnan(bus.Vnom) or math.isinf(bus.Vnom):
            warnings.append(f"Bus '{bus.name}' has NaN/inf Vnom={bus.Vnom}")
            break  # Don't flood with per-bus warnings

    # Check generator limits for NaN/inf
    nan_gen_count = 0
    for gen in grid.generators:
        if math.isnan(gen.Pmin) or math.isinf(gen.Pmin):
            nan_gen_count += 1
        if math.isnan(gen.Pmax) or math.isinf(gen.Pmax):
            nan_gen_count += 1
    if nan_gen_count > 0:
        warnings.append(f"{nan_gen_count} generator limit values are NaN/inf")

    # Check branch flow limits
    branches_without_rate = 0
    for line in grid.lines:
        if hasattr(line, "rate") and (line.rate == 0 or math.isnan(line.rate)):
            branches_without_rate += 1
    if branches_without_rate > 0:
        warnings.append(f"{branches_without_rate}/{len(grid.lines)} lines have zero or NaN rate")

    # Check for generator cost data
    has_cost_data = False
    for gen in grid.generators:
        if hasattr(gen, "Cost") or hasattr(gen, "cost"):
            has_cost_data = True
            break
        if hasattr(gen, "Cost2") or hasattr(gen, "Cost0"):
            has_cost_data = True
            break
    if not has_cost_data:
        warnings.append("No generator cost attributes found")

    # Check for slack/reference bus
    slack_found = False
    for bus in grid.buses:
        if hasattr(bus, "is_slack") and bus.is_slack:
            slack_found = True
            break
    if not slack_found:
        warnings.append("No slack bus identified via is_slack attribute")

    return warnings


class TestGate:
    """Gate tests verifying GridCal can ingest MATPOWER networks at three scales."""

    def test_g1_tiny_import(self, data_dir: Path) -> None:
        """G-1: Import IEEE 39-bus (TINY) network."""
        test_id = "G-1"
        ref = REFERENCE[test_id]

        grid, load_time = _load_grid(data_dir, test_id)

        bus_count = grid.get_bus_number()
        branch_count = _count_branches(grid)
        gen_count = len(grid.generators)

        print(f"\n[{test_id}] {ref['label']}")
        print(f"  Load time: {load_time:.3f}s")
        print(f"  Buses:      {bus_count} (expected {ref['buses']})")
        print(f"  Branches:   {branch_count} (expected {ref['branches']})")
        print(f"  Generators: {gen_count} (expected {ref['generators']})")

        assert bus_count == ref["buses"], (
            f"Bus count mismatch: got {bus_count}, expected {ref['buses']}"
        )
        assert branch_count == ref["branches"], (
            f"Branch count mismatch: got {branch_count}, expected {ref['branches']}"
        )
        assert gen_count == ref["generators"], (
            f"Generator count mismatch: got {gen_count}, expected {ref['generators']}"
        )

        # Post-import audit
        warnings = _audit_grid(grid, test_id)
        if warnings:
            print(f"  Audit warnings: {warnings}")

    def test_g2_small_import(self, data_dir: Path) -> None:
        """G-2: Import ACTIVSg 2000-bus (SMALL) network."""
        test_id = "G-2"
        ref = REFERENCE[test_id]

        grid, load_time = _load_grid(data_dir, test_id)

        bus_count = grid.get_bus_number()
        branch_count = _count_branches(grid)
        gen_count = len(grid.generators)

        print(f"\n[{test_id}] {ref['label']}")
        print(f"  Load time: {load_time:.3f}s")
        print(f"  Buses:      {bus_count} (expected {ref['buses']})")
        print(f"  Branches:   {branch_count} (expected {ref['branches']})")
        print(f"  Generators: {gen_count} (expected {ref['generators']})")

        assert bus_count == ref["buses"], (
            f"Bus count mismatch: got {bus_count}, expected {ref['buses']}"
        )
        assert branch_count == ref["branches"], (
            f"Branch count mismatch: got {branch_count}, expected {ref['branches']}"
        )
        assert gen_count == ref["generators"], (
            f"Generator count mismatch: got {gen_count}, expected {ref['generators']}"
        )

        warnings = _audit_grid(grid, test_id)
        if warnings:
            print(f"  Audit warnings: {warnings}")

    def test_g3_medium_import(self, data_dir: Path) -> None:
        """G-3: Import ACTIVSg 10000-bus (MEDIUM) network."""
        test_id = "G-3"
        ref = REFERENCE[test_id]

        grid, load_time = _load_grid(data_dir, test_id)

        bus_count = grid.get_bus_number()
        branch_count = _count_branches(grid)
        gen_count = len(grid.generators)

        print(f"\n[{test_id}] {ref['label']}")
        print(f"  Load time: {load_time:.3f}s")
        print(f"  Buses:      {bus_count} (expected {ref['buses']})")
        print(f"  Branches:   {branch_count} (expected {ref['branches']})")
        print(f"  Generators: {gen_count} (expected {ref['generators']})")

        assert bus_count == ref["buses"], (
            f"Bus count mismatch: got {bus_count}, expected {ref['buses']}"
        )
        assert branch_count == ref["branches"], (
            f"Branch count mismatch: got {branch_count}, expected {ref['branches']}"
        )
        assert gen_count == ref["generators"], (
            f"Generator count mismatch: got {gen_count}, expected {ref['generators']}"
        )

        warnings = _audit_grid(grid, test_id)
        if warnings:
            print(f"  Audit warnings: {warnings}")
