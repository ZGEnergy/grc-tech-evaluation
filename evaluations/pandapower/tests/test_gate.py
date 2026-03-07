"""Gate tests for pandapower: network ingestion checks across three tiers.

G-1: TINY  (case39.m)           — 39 buses, 46 branches, 10 generators
G-2: SMALL (case_ACTIVSg2000.m) — 2000 buses, 3206 branches, 544 generators
G-3: MEDIUM(case_ACTIVSg10k.m)  — 10000 buses, 12706 branches, 2485 generators
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest


@dataclass
class NetworkSpec:
    """Expected counts for a MATPOWER network file."""

    test_id: str
    tier: str
    filename: str
    buses: int
    branches: int
    generators: int


SPECS = [
    NetworkSpec("G-1", "TINY", "case39.m", 39, 46, 10),
    NetworkSpec("G-2", "SMALL", "case_ACTIVSg2000.m", 2000, 3206, 544),
    NetworkSpec("G-3", "MEDIUM", "case_ACTIVSg10k.m", 10000, 12706, 2485),
]


def _load_network(filepath: str):
    """Load a MATPOWER .m file into a pandapower network."""
    from pandapower.converter.matpower.from_mpc import from_mpc

    return from_mpc(filepath, f_hz=60)


def _count_elements(net) -> dict[str, int]:
    """Count buses, branches, and generators in a pandapower network.

    pandapower's MATPOWER converter maps branches to line, trafo, trafo3w, or impedance
    elements depending on voltage ratios and impedance characteristics.
    """
    buses = len(net.bus)
    branches = len(net.line) + len(net.trafo) + len(net.trafo3w) + len(net.impedance)
    generators = len(net.gen) + len(net.ext_grid) + len(net.sgen)
    return {"buses": buses, "branches": branches, "generators": generators}


def _audit_data_quality(net) -> list[str]:
    """Post-import data quality audit. Returns list of warnings."""
    warnings = []

    # Check bus voltages for NaN/inf
    if net.bus["vn_kv"].isna().any():
        warnings.append("NaN found in bus nominal voltages (vn_kv)")
    if np.isinf(net.bus["vn_kv"]).any():
        warnings.append("Inf found in bus nominal voltages (vn_kv)")

    # Check line ratings for NaN/inf
    if len(net.line) > 0:
        if "max_i_ka" in net.line.columns:
            if net.line["max_i_ka"].isna().any():
                warnings.append("NaN found in line current ratings (max_i_ka)")
            if np.isinf(net.line["max_i_ka"]).any():
                warnings.append("Inf found in line current ratings (max_i_ka)")
            if (net.line["max_i_ka"] == 0).all():
                warnings.append("All line current ratings are zero (max_i_ka)")

    # Check generator limits for NaN/inf
    for tbl_name in ["gen", "ext_grid", "sgen"]:
        tbl = getattr(net, tbl_name)
        if len(tbl) > 0:
            for col in ["min_p_mw", "max_p_mw"]:
                if col in tbl.columns:
                    if tbl[col].isna().any():
                        warnings.append(f"NaN found in {tbl_name}.{col}")
                    if np.isinf(tbl[col]).any():
                        warnings.append(f"Inf found in {tbl_name}.{col}")

    # Check for generator cost data (poly_cost or pwl_cost tables)
    has_cost = False
    if hasattr(net, "poly_cost") and len(net.poly_cost) > 0:
        has_cost = True
    if hasattr(net, "pwl_cost") and len(net.pwl_cost) > 0:
        has_cost = True
    if not has_cost:
        warnings.append("No generator cost data found (poly_cost/pwl_cost empty)")

    # Check branch flow limits
    if len(net.line) > 0:
        if "max_i_ka" not in net.line.columns:
            warnings.append("No branch flow limit column (max_i_ka) in lines")

    # Check for slack/reference bus
    if len(net.ext_grid) == 0:
        warnings.append("No ext_grid (slack/reference bus) found")

    return warnings


class TestGate:
    """Gate tests verifying pandapower can ingest MATPOWER networks at three tiers."""

    def test_import(self) -> None:
        """pandapower core library can be imported."""
        import pandapower as pp

        assert hasattr(pp, "__version__")
        assert isinstance(pp.__version__, str)

    @pytest.mark.parametrize(
        "spec",
        SPECS,
        ids=[s.test_id for s in SPECS],
    )
    def test_gate_ingest(self, data_dir: Path, spec: NetworkSpec) -> None:
        """Load MATPOWER file and verify element counts and data quality."""
        filepath = data_dir / spec.filename
        assert filepath.exists(), f"Network file not found: {filepath}"

        # Load network and measure time
        t0 = time.perf_counter()
        net = _load_network(str(filepath))
        load_time = time.perf_counter() - t0

        # Count elements
        counts = _count_elements(net)

        # Verify counts
        assert counts["buses"] == spec.buses, (
            f"[{spec.test_id}] Bus count mismatch: expected {spec.buses}, got {counts['buses']}"
        )
        assert counts["branches"] == spec.branches, (
            f"[{spec.test_id}] Branch count mismatch: "
            f"expected {spec.branches}, got {counts['branches']} "
            f"(lines={len(net.line)}, trafos={len(net.trafo)}, "
            f"trafo3w={len(net.trafo3w)}, impedance={len(net.impedance)})"
        )
        assert counts["generators"] == spec.generators, (
            f"[{spec.test_id}] Generator count mismatch: "
            f"expected {spec.generators}, got {counts['generators']} "
            f"(gen={len(net.gen)}, ext_grid={len(net.ext_grid)}, sgen={len(net.sgen)})"
        )

        # Data quality audit
        warnings = _audit_data_quality(net)

        # Print summary for capture
        print(f"\n[{spec.test_id}] {spec.tier} ({spec.filename})")
        print(f"  Load time: {load_time:.3f}s")
        print(
            f"  Buses: {counts['buses']}, Branches: {counts['branches']}, "
            f"Generators: {counts['generators']}"
        )
        print(
            f"  Lines: {len(net.line)}, Trafos: {len(net.trafo)}, "
            f"Trafo3w: {len(net.trafo3w)}, Impedance: {len(net.impedance)}"
        )
        print(f"  Gen: {len(net.gen)}, ExtGrid: {len(net.ext_grid)}, Sgen: {len(net.sgen)}")
        if warnings:
            print(f"  Data quality warnings ({len(warnings)}):")
            for w in warnings:
                print(f"    - {w}")
        else:
            print("  Data quality: OK (no warnings)")
