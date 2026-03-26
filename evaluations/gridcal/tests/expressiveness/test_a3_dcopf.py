"""
Test A-3: Solve DC OPF with differentiated gen costs and 70% branch derating on TINY.

Dimension: expressiveness
Network: TINY (IEEE 39-bus New England)
Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable. With
    differentiated costs and 70% derating, at least 2 branches have non-zero shadow prices
    (binding flow constraints). Report max LMP spread across buses.
Tool: gridcal (VeraGridEngine) 5.6.28
Solver: HiGHS
"""

from __future__ import annotations

import csv
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "shared"))

from matpower_loader import load_gridcal

# Cost mapping from gen_temporal_params.csv tech_class_key
COST_MAP = {
    "hydro": {"c1": 5.0, "c2": 0.005},
    "nuclear": {"c1": 10.0, "c2": 0.010},
    "coal_large": {"c1": 25.0, "c2": 0.025},
    "gas_CC": {"c1": 40.0, "c2": 0.040},
}

BRANCH_DERATING = 0.70


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = "data/timeseries/case39",
) -> dict:
    """Execute A-3 DCOPF test and return structured results."""
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import VeraGridEngine as vge
        from VeraGridEngine.enumerations import MIPSolvers, SolverType

        # 1. Load network
        grid = load_gridcal(network_file)
        n_buses = grid.get_bus_number()
        generators = grid.get_generators()
        branches = grid.get_branches()
        results["details"]["bus_count"] = n_buses
        results["details"]["gen_count"] = len(generators)
        results["details"]["branch_count"] = len(branches)

        # 2. Load augmented cost data from timeseries directory
        ts_dir = Path(timeseries_dir) if timeseries_dir else None
        if ts_dir and (ts_dir / "gen_temporal_params.csv").exists():
            gen_params = {}
            with open(ts_dir / "gen_temporal_params.csv") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    gen_idx = int(row["gen_index"])
                    gen_params[gen_idx] = row

            # Apply differentiated costs to generators
            for idx, gen in enumerate(generators):
                if idx in gen_params:
                    tech_key = gen_params[idx]["tech_class_key"]
                    if tech_key in COST_MAP:
                        gen.Cost = COST_MAP[tech_key]["c1"]  # linear cost $/MWh
                        gen.Cost2 = COST_MAP[tech_key]["c2"]  # quadratic cost $/MW^2h
                        gen.Cost0 = 0.0  # constant cost

            results["details"]["cost_augmentation"] = (
                "Applied differentiated costs from gen_temporal_params.csv"
            )
            results["details"]["cost_mapping"] = {k: v["c1"] for k, v in COST_MAP.items()}
        else:
            results["errors"].append("gen_temporal_params.csv not found; using default costs")

        # 3. Apply 70% branch derating
        for branch in branches:
            if hasattr(branch, "rate") and branch.rate > 0:
                branch.rate = branch.rate * BRANCH_DERATING
            elif hasattr(branch, "Rate") and branch.Rate > 0:
                branch.Rate = branch.Rate * BRANCH_DERATING
        results["details"]["branch_derating"] = BRANCH_DERATING

        # 4. Configure and solve DC OPF
        opf_opts = vge.OptimalPowerFlowOptions(
            solver=SolverType.LINEAR_OPF,
            mip_solver=MIPSolvers.HIGHS,
        )

        opf_results = vge.linear_opf(grid, opf_opts)

        # 5. Extract results
        converged = bool(opf_results.converged)
        results["details"]["converged"] = converged
        results["details"]["solver"] = "HiGHS"

        if not converged:
            results["errors"].append("DC OPF did not converge")
            return results

        # Generator dispatch
        gen_power = opf_results.generator_power
        gen_names = [g.name for g in generators]
        results["details"]["generator_dispatch_mw"] = {
            gen_names[i]: float(gen_power[i]) for i in range(len(gen_power))
        }
        results["details"]["total_generation_mw"] = float(np.sum(gen_power))

        # LMPs / bus shadow prices
        lmps = opf_results.bus_shadow_prices
        bus_names = [b.name for b in grid.get_buses()]

        if lmps is not None and len(lmps) > 0:
            results["details"]["lmps"] = {bus_names[i]: float(lmps[i]) for i in range(len(lmps))}
            lmp_min = float(np.min(lmps))
            lmp_max = float(np.max(lmps))
            lmp_spread = lmp_max - lmp_min
            results["details"]["lmp_min"] = lmp_min
            results["details"]["lmp_max"] = lmp_max
            results["details"]["lmp_spread"] = lmp_spread
            results["details"]["lmp_mean"] = float(np.mean(lmps))
        else:
            results["details"]["lmp_spread"] = 0.0
            results["errors"].append("No LMP/shadow price data available")

        # Branch flows and shadow prices
        sf = opf_results.Sf
        loading = opf_results.loading
        branch_names_all = [b.name for b in branches]

        results["details"]["branch_flows_mw"] = {
            branch_names_all[i]: float(np.real(sf[i])) for i in range(len(sf))
        }
        results["details"]["branch_loading_pct"] = {
            branch_names_all[i]: float(np.abs(loading[i]) * 100) for i in range(len(loading))
        }

        # Count binding branches (loading >= 99%)
        binding_branches = []
        for i in range(len(loading)):
            if np.abs(loading[i]) >= 0.99:
                binding_branches.append(branch_names_all[i])
        results["details"]["binding_branch_count"] = len(binding_branches)
        results["details"]["binding_branches"] = binding_branches

        # Check for branch overloads/shadow prices
        if hasattr(opf_results, "overloads") and opf_results.overloads is not None:
            overloads = opf_results.overloads
            nonzero_shadow = np.sum(np.abs(overloads) > 1e-6)
            results["details"]["branches_with_shadow_prices"] = int(nonzero_shadow)
            results["details"]["overloads"] = {
                branch_names_all[i]: float(overloads[i])
                for i in range(len(overloads))
                if abs(overloads[i]) > 1e-6
            }

        # 6. Check max branch loading for soft constraint detection (v11)
        max_loading_abs = float(np.max(np.abs(loading)))
        results["details"]["max_branch_loading"] = max_loading_abs
        results["details"]["max_branch_loading_pct"] = f"{max_loading_abs * 100:.2f}%"

        # Find which branch has max loading
        max_idx = int(np.argmax(np.abs(loading)))
        results["details"]["max_loading_branch"] = branch_names_all[max_idx]

        # Soft constraint detection: if any branch exceeds 100% + 1e-4 tolerance
        soft_constraint_detected = max_loading_abs > (1.0 + 1e-4)
        results["details"]["soft_constraint_detected"] = soft_constraint_detected

        if soft_constraint_detected:
            results["details"]["soft_constraint_note"] = (
                f"Branch {branch_names_all[max_idx]} has loading "
                f"{max_loading_abs * 100:.2f}%, exceeding 100% + 1e-4 tolerance. "
                "GridCal linear_opf uses soft branch flow constraints (LP slack variables). "
                "[tool-specific: soft constraint formulation in linear_opf]"
            )

        # 7. Check pass condition
        pass_checks = {
            "converged": converged,
            "lmps_extractable": lmps is not None and len(lmps) > 0,
            "binding_branches_ge_2": len(binding_branches) >= 2,
        }
        results["details"]["pass_checks"] = pass_checks

        if all(pass_checks.values()):
            if soft_constraint_detected:
                # v11: soft constraints -> partial_pass
                results["status"] = "partial_pass"
                results["workarounds"].append(
                    "GridCal linear_opf uses soft branch flow constraints. "
                    f"Max loading {max_loading_abs * 100:.2f}% exceeds hard limit. "
                    "This is a legitimate numerical stabilization technique but "
                    "must be labeled as soft-constraint DCOPF."
                )
            else:
                results["status"] = "pass"
        else:
            failing = [k for k, v in pass_checks.items() if not v]
            results["errors"].append(f"Failed checks: {failing}")

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
