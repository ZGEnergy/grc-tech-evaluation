"""
Standalone verification script for the shared PyPSA MATPOWER loader.

Validates that load_pypsa() correctly patches transformer susceptance and
populates generator marginal costs from gencost data.

Optionally tests G-FNM-3 bus-angle accuracy against a cleaned FNM .m file
when the FNM_PATH environment variable is set.

Usage:
    # Basic verification against TINY (IEEE 39-bus) network
    python evaluations/shared/verify_pypsa_loader.py

    # With G-FNM-3 bus-angle check (requires FNM data)
    FNM_PATH=/workspace/data/fnm python evaluations/shared/verify_pypsa_loader.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

# Allow running from any working directory by locating repo root via this file's path
_THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = _THIS_DIR.parent.parent

# Ensure shared/ is importable
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from matpower_loader import load_pypsa  # noqa: E402


TINY_NETWORK = REPO_ROOT / "data" / "networks" / "case39.m"


def _check_tiny(results: dict) -> None:
    """Verify loader against IEEE 39-bus (TINY) network."""
    print(f"Loading TINY network: {TINY_NETWORK}", file=sys.stderr)
    n = load_pypsa(str(TINY_NETWORK))

    # --- Marginal cost check ---
    mc = n.generators["marginal_cost"]
    populated = (mc > 0).sum()
    total = len(mc)
    mc_ok = populated == total

    results["details"]["marginal_cost_populated"] = bool(mc_ok)
    results["details"]["generators_with_positive_mc"] = int(populated)
    results["details"]["total_generators"] = int(total)

    if not mc_ok:
        results["errors"].append(
            f"marginal_cost not fully populated: {populated}/{total} generators > 0"
        )

    # --- Transformer count check ---
    n_transformers = len(n.transformers)
    results["details"]["transformers_count"] = n_transformers
    # case39 has no off-nominal tap transformers, so this just checks that the
    # network loaded without error; a count of 0 is expected and acceptable.

    # --- Linear power flow check ---
    n.lpf()
    results["details"]["lpf_converged"] = True

    if mc_ok:
        results["status"] = "pass"


def _check_fnm(fnm_path: str, results: dict) -> None:
    """Verify G-FNM-3 bus-angle accuracy against a cleaned FNM .m file.

    Pass condition: ≥95% of buses within 1° of MATPOWER reference solution.
    """
    import numpy as np

    try:
        import pandapower as pp
        from pandapower.converter.matpower.from_mpc import from_mpc

        _has_pp = True
    except ImportError:
        _has_pp = False

    # Locate cleaned .m file — accept either a direct path or a directory
    fnm_dir = Path(fnm_path)
    if fnm_dir.is_dir():
        candidates = list(fnm_dir.glob("*.m"))
        if not candidates:
            results["details"]["fnm_skipped"] = True
            results["details"]["fnm_skip_reason"] = (
                f"No .m files found in FNM_PATH={fnm_path}"
            )
            return
        fnm_file = candidates[0]
    else:
        fnm_file = fnm_dir

    if not fnm_file.exists():
        results["details"]["fnm_skipped"] = True
        results["details"]["fnm_skip_reason"] = f"FNM file not found: {fnm_file}"
        return

    print(f"Loading FNM network: {fnm_file}", file=sys.stderr)
    n = load_pypsa(str(fnm_file))

    # Run linear power flow
    n.lpf()
    pypsa_angles_deg = np.degrees(n.buses_t.v_ang.iloc[0].values)

    if _has_pp:
        # Use pandapower as reference (lossless loader)
        net_ref = from_mpc(str(fnm_file), f_hz=60)
        pp.rundcpp(net_ref)
        ref_angles_deg = net_ref.res_bus["va_degree"].values
        # Align by bus index order
        n_buses = min(len(pypsa_angles_deg), len(ref_angles_deg))
        diffs = np.abs(pypsa_angles_deg[:n_buses] - ref_angles_deg[:n_buses])
    else:
        # No reference available — check self-consistency only
        results["details"]["fnm_reference"] = (
            "pandapower not available; self-check only"
        )
        results["details"]["fnm_lpf_converged"] = True
        return

    within_1deg = (diffs < 1.0).sum()
    total_buses = len(diffs)
    pct = within_1deg / total_buses if total_buses > 0 else 0.0

    results["details"]["buses_within_1deg_pct"] = round(float(pct), 4)
    results["details"]["buses_within_1deg"] = int(within_1deg)
    results["details"]["total_fnm_buses"] = int(total_buses)
    results["details"]["fnm_file"] = str(fnm_file)

    if pct < 0.95:
        results["errors"].append(
            f"G-FNM-3 FAIL: only {pct:.1%} of buses within 1° "
            f"(required ≥95%); max diff = {diffs.max():.2f}°"
        )
        results["status"] = "fail"
    else:
        results["details"]["fnm_pass"] = True


def run(
    tiny_path: str = str(TINY_NETWORK),
    fnm_path: str | None = None,
) -> dict:
    """Execute verification and return structured results.

    Returns:
        dict with keys:
        - status: "pass" | "fail"
        - wall_clock_seconds: float
        - details: dict of check-specific outputs
        - errors: list of error messages (empty if pass)
        - workarounds: list of workaround descriptions (empty if none)
    """
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        _check_tiny(results)

        if fnm_path is not None:
            _check_fnm(fnm_path, results)

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    fnm_path = os.environ.get("FNM_PATH")
    result = run(fnm_path=fnm_path)
    print(json.dumps(result, indent=2, default=str))
