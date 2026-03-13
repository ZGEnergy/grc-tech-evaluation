"""Gate evaluation script for PyPSA: G-1, G-2, G-3.

Loads MATPOWER .m files via matpowercaseframes + pypsa, counts topology,
performs data quality checks, and reports pass/fail.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "networks"


def load_network(m_file: Path) -> tuple[Any, float]:
    """Load a MATPOWER .m file into a PyPSA Network and return (net, elapsed_seconds)."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(str(m_file))
    ppc = {
        "version": "2",
        "baseMVA": float(cf.baseMVA),
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    if hasattr(cf, "gencost") and cf.gencost is not None and len(cf.gencost) > 0:
        ppc["gencost"] = cf.gencost.values

    t0 = time.perf_counter()
    net = pypsa.Network()
    net.import_from_pypower_ppc(ppc)
    elapsed = time.perf_counter() - t0

    return net, elapsed, ppc


def audit_network(net: Any, ppc: dict) -> dict[str, Any]:
    """Perform data quality audit on a loaded PyPSA Network."""
    import numpy as np

    notes = []
    warnings = []

    # Bus voltage nominal — check for NaN/inf
    if hasattr(net, "buses") and len(net.buses) > 0:
        v_nom = net.buses.v_nom
        nan_v = v_nom.isna().sum()
        inf_v = np.isinf(v_nom.fillna(0)).sum()
        if nan_v > 0:
            warnings.append(f"Bus v_nom: {nan_v} NaN values")
        if inf_v > 0:
            warnings.append(f"Bus v_nom: {inf_v} infinite values")

    # Line ratings
    if hasattr(net, "lines") and len(net.lines) > 0:
        s_nom = net.lines.s_nom
        nan_s = s_nom.isna().sum()
        zero_s = (s_nom == 0).sum()
        if nan_s > 0:
            warnings.append(f"Line s_nom: {nan_s} NaN values")
        if zero_s > 0:
            notes.append(f"Line s_nom: {zero_s} zero values (unlimited flow assumed)")
        notes.append(f"Line flow limits present: {nan_s == 0 and len(net.lines) > 0}")

    # Transformer ratings
    if hasattr(net, "transformers") and len(net.transformers) > 0:
        s_nom_t = net.transformers.s_nom
        nan_st = s_nom_t.isna().sum()
        if nan_st > 0:
            warnings.append(f"Transformer s_nom: {nan_st} NaN values")

    # Generator limits
    if hasattr(net, "generators") and len(net.generators) > 0:
        p_nom = net.generators.p_nom
        nan_pg = p_nom.isna().sum()
        if nan_pg > 0:
            warnings.append(f"Generator p_nom: {nan_pg} NaN values")

    # Generator cost data
    has_cost = False
    if hasattr(net, "generators") and "marginal_cost" in net.generators.columns:
        mc = net.generators["marginal_cost"]
        nonzero_cost = (mc != 0).sum()
        has_cost = nonzero_cost > 0
        notes.append(
            f"Generator cost data: {nonzero_cost}/{len(net.generators)} generators have non-zero marginal cost"
        )
    else:
        notes.append("Generator marginal_cost column not present in generators DataFrame")

    # Slack bus
    slack_buses = (
        net.buses[net.buses.control == "Slack"] if "control" in net.buses.columns else None
    )
    if slack_buses is not None and len(slack_buses) > 0:
        notes.append(f"Slack/reference bus identified: {list(slack_buses.index)}")
    else:
        # Check v_mag_pu_set or carrier for reference bus
        notes.append(
            "Slack bus: control column not present or no explicit slack — PyPSA uses first PV bus as slack"
        )

    return {"notes": notes, "warnings": warnings, "has_cost": has_cost}


def count_topology(net: Any) -> dict[str, int]:
    """Count buses, branches (lines + transformers), and generators."""
    n_buses = len(net.buses)
    n_lines = len(net.lines) if hasattr(net, "lines") else 0
    n_transformers = len(net.transformers) if hasattr(net, "transformers") else 0
    n_branches = n_lines + n_transformers
    n_generators = len(net.generators) if hasattr(net, "generators") else 0
    return {
        "buses": n_buses,
        "lines": n_lines,
        "transformers": n_transformers,
        "branches": n_branches,
        "generators": n_generators,
    }


def run_gate_test(
    test_id: str,
    network_name: str,
    m_file: Path,
    expected_buses: int | None,
    expected_branches: int | None,
    expected_generators: int | None,
) -> dict[str, Any]:
    """Run a single gate test and return results dict."""
    print(f"\n{'=' * 60}")
    print(f"Running {test_id}: {network_name}")
    print(f"File: {m_file}")
    print(f"{'=' * 60}")

    result: dict[str, Any] = {
        "test_id": test_id,
        "network": network_name,
        "file": str(m_file),
        "status": "FAIL",
        "elapsed": 0.0,
        "counts": {},
        "expected": {
            "buses": expected_buses,
            "branches": expected_branches,
            "generators": expected_generators,
        },
        "audit": {},
        "errors": [],
        "notes": [],
    }

    try:
        net, elapsed, ppc = load_network(m_file)
        result["elapsed"] = elapsed
        counts = count_topology(net)
        result["counts"] = counts

        print(f"Load time: {elapsed:.2f}s")
        print(f"Buses: {counts['buses']} (expected: {expected_buses})")
        print(f"Lines: {counts['lines']}, Transformers: {counts['transformers']}")
        print(f"Branches: {counts['branches']} (expected: {expected_branches})")
        print(f"Generators: {counts['generators']} (expected: {expected_generators})")

        audit = audit_network(net, ppc)
        result["audit"] = audit

        if audit["warnings"]:
            print(f"Warnings: {audit['warnings']}")
        if audit["notes"]:
            print(f"Notes: {audit['notes']}")

        # Pass/fail logic
        pass_checks = []

        # Bus count check
        if expected_buses is not None:
            bus_ok = counts["buses"] == expected_buses
            pass_checks.append(bus_ok)
            if not bus_ok:
                result["errors"].append(
                    f"Bus count mismatch: expected {expected_buses}, got {counts['buses']}"
                )
        else:
            pass_checks.append(True)

        # Branch count check
        if expected_branches is not None:
            branch_ok = counts["branches"] == expected_branches
            pass_checks.append(branch_ok)
            if not branch_ok:
                result["errors"].append(
                    f"Branch count mismatch: expected {expected_branches}, got {counts['branches']}"
                )
        else:
            pass_checks.append(True)

        # Generator count check
        if expected_generators is not None:
            gen_ok = counts["generators"] == expected_generators
            pass_checks.append(gen_ok)
            if not gen_ok:
                result["errors"].append(
                    f"Generator count mismatch: expected {expected_generators}, got {counts['generators']}"
                )
        else:
            pass_checks.append(True)

        # No critical NaN warnings
        critical_nan = any("NaN" in w for w in audit["warnings"])
        pass_checks.append(not critical_nan)
        if critical_nan:
            result["errors"].append(
                f"Critical NaN values: {[w for w in audit['warnings'] if 'NaN' in w]}"
            )

        result["status"] = "PASS" if all(pass_checks) else "FAIL"
        print(f"\nResult: {result['status']}")
        if result["errors"]:
            print(f"Errors: {result['errors']}")

    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"Exception: {type(e).__name__}: {e}")
        print(f"EXCEPTION: {e}")
        import traceback

        traceback.print_exc()

    return result


if __name__ == "__main__":
    # G-1: TINY — IEEE 39-bus
    r1 = run_gate_test(
        "G-1",
        "TINY",
        DATA_DIR / "case39.m",
        expected_buses=39,
        expected_branches=46,
        expected_generators=10,
    )

    if r1["status"] == "FAIL":
        print("\n\nG-1 FAILED — disqualifying. Stopping.")
    else:
        # G-2: SMALL — ACTIVSg 2k
        r2 = run_gate_test(
            "G-2",
            "SMALL",
            DATA_DIR / "case_ACTIVSg2000.m",
            expected_buses=None,
            expected_branches=None,
            expected_generators=None,
        )

        # G-3: MEDIUM — ACTIVSg 10k
        r3 = run_gate_test(
            "G-3",
            "MEDIUM",
            DATA_DIR / "case_ACTIVSg10k.m",
            expected_buses=None,
            expected_branches=None,
            expected_generators=None,
        )

    print("\n\n=== SUMMARY ===")
    print(f"G-1: {r1['status']} — counts: {r1.get('counts', {})} in {r1.get('elapsed', 0):.2f}s")
    if r1["status"] == "PASS":
        print(
            f"G-2: {r2['status']} — counts: {r2.get('counts', {})} in {r2.get('elapsed', 0):.2f}s"
        )
        print(
            f"G-3: {r3['status']} — counts: {r3.get('counts', {})} in {r3.get('elapsed', 0):.2f}s"
        )
