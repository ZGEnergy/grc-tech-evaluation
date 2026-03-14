"""
Test B-6: Qualitative assessment of DCPF solve path source code architecture.

Dimension: extensibility
Network: N/A
Pass condition: Document: number of abstraction layers, whether network model / problem
    formulation / solver interface / results are separated, whether internal interfaces
    are documented.
Tool: gridcal (VeraGridEngine) 5.6.28

This is an AUDIT test -- reads source code, does not run simulations.
"""

from __future__ import annotations

import json
import os
import time
import traceback


def _count_lines(filepath: str) -> int:
    """Count lines in a file."""
    with open(filepath) as f:
        return sum(1 for _ in f)


def _count_docstrings(filepath: str) -> dict:
    """Count functions/methods and how many have docstrings."""
    with open(filepath) as f:
        content = f.read()
    lines = content.split("\n")
    total_defs = 0
    with_docstring = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("class "):
            total_defs += 1
            # Check if next non-empty line is a docstring
            for j in range(i + 1, min(i + 5, len(lines))):
                next_stripped = lines[j].lstrip()
                if next_stripped.startswith('"""') or next_stripped.startswith("'''"):
                    with_docstring += 1
                    break
                elif next_stripped and not next_stripped.startswith("#"):
                    break
    return {"total_defs": total_defs, "with_docstring": with_docstring}


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute B-6 code architecture audit and return structured results."""
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

        pkg_dir = os.path.dirname(vge.__file__)

        # =====================================================================
        # Layer 1: API Layer (api.py)
        # =====================================================================
        api_path = os.path.join(pkg_dir, "api.py")
        api_loc = _count_lines(api_path)
        api_docs = _count_docstrings(api_path)

        # =====================================================================
        # Layer 2: Driver Layer (PowerFlowDriver)
        # =====================================================================
        driver_path = os.path.join(pkg_dir, "Simulations/PowerFlow/power_flow_driver.py")
        driver_loc = _count_lines(driver_path)
        driver_docs = _count_docstrings(driver_path)

        # =====================================================================
        # Layer 3: Worker/Solver Layer (multi_island_pf, __solve_island)
        # =====================================================================
        worker_path = os.path.join(pkg_dir, "Simulations/PowerFlow/power_flow_worker.py")
        worker_loc = _count_lines(worker_path)
        worker_docs = _count_docstrings(worker_path)

        # =====================================================================
        # Layer 4: Results Layer (PowerFlowResults)
        # =====================================================================
        results_path = os.path.join(pkg_dir, "Simulations/PowerFlow/power_flow_results.py")
        results_loc = _count_lines(results_path)
        results_docs = _count_docstrings(results_path)

        # =====================================================================
        # Data Model Layer (MultiCircuit, NumericalCircuit)
        # =====================================================================
        mc_path = os.path.join(pkg_dir, "Devices/multi_circuit.py")
        mc_loc = _count_lines(mc_path)
        mc_docs = _count_docstrings(mc_path)

        assets_path = os.path.join(pkg_dir, "Devices/assets.py")
        assets_loc = _count_lines(assets_path)
        assets_docs = _count_docstrings(assets_path)

        nc_path = os.path.join(pkg_dir, "DataStructures/numerical_circuit.py")
        nc_loc = _count_lines(nc_path)
        nc_docs = _count_docstrings(nc_path)

        # =====================================================================
        # OPF Formulation Layer (for comparison)
        # =====================================================================
        opf_form_path = os.path.join(pkg_dir, "Simulations/OPF/Formulations/linear_opf_ts.py")
        opf_form_loc = _count_lines(opf_form_path)

        # =====================================================================
        # NumericalMethods (actual solver implementations)
        # =====================================================================
        nm_dir = os.path.join(pkg_dir, "Simulations/PowerFlow/NumericalMethods")
        nm_files = {}
        if os.path.exists(nm_dir):
            for f in sorted(os.listdir(nm_dir)):
                if f.endswith(".py") and f != "__init__.py":
                    nm_files[f] = _count_lines(os.path.join(nm_dir, f))

        pf_formulations_dir = os.path.join(pkg_dir, "Simulations/PowerFlow/Formulations")
        pf_form_files = {}
        if os.path.exists(pf_formulations_dir):
            for f in sorted(os.listdir(pf_formulations_dir)):
                if f.endswith(".py") and f != "__init__.py":
                    pf_form_files[f] = _count_lines(os.path.join(pf_formulations_dir, f))

        # =====================================================================
        # Architecture Assessment
        # =====================================================================

        # DCPF Solve Path Trace:
        # 1. vge.power_flow(grid, options) [api.py:101-118]
        #    -> Creates PowerFlowDriver, calls driver.run()
        # 2. PowerFlowDriver.run() [power_flow_driver.py:126-252]
        #    -> Selects engine (VeraGrid, NewtonPA, Bentayga, PGM, GSLV)
        #    -> Calls multi_island_pf() for VeraGrid engine
        # 3. multi_island_pf() [power_flow_worker.py:994-1031]
        #    -> Compiles MultiCircuit -> NumericalCircuit
        #    -> Calls multi_island_pf_nc()
        # 4. multi_island_pf_nc() [power_flow_worker.py:913-991]
        #    -> Handles island detection
        #    -> Dispatches to __multi_island_pf_nc_limited_support() for DCPF
        # 5. __multi_island_pf_nc_limited_support() [power_flow_worker.py:815-912]
        #    -> Loops over islands
        #    -> Calls __solve_island_limited_support() per island
        # 6. __solve_island_limited_support() [power_flow_worker.py:316-732]
        #    -> For SolverType.Linear: builds Bdc, solves linear system
        #    -> Direct sparse linear solve (scipy.sparse.linalg)

        architecture = {
            "abstraction_layers": 5,
            "layer_descriptions": {
                "L1_api": {
                    "file": "api.py",
                    "loc": api_loc,
                    "role": "Convenience functions wrapping Driver pattern. "
                    "One-liner access to all simulation types.",
                    "documentation": api_docs,
                },
                "L2_driver": {
                    "file": "Simulations/PowerFlow/power_flow_driver.py",
                    "loc": driver_loc,
                    "role": "Orchestration: engine selection, QThread support, "
                    "logging, report generation. Thin coordinator.",
                    "documentation": driver_docs,
                },
                "L3_worker": {
                    "file": "Simulations/PowerFlow/power_flow_worker.py",
                    "loc": worker_loc,
                    "role": "Core solve logic: island decomposition, solver dispatch "
                    "(NR, HELM, DC, etc.), convergence checks. Contains 14+ "
                    "solver algorithm implementations.",
                    "documentation": worker_docs,
                },
                "L4_results": {
                    "file": "Simulations/PowerFlow/power_flow_results.py",
                    "loc": results_loc,
                    "role": "Typed results container with DataFrame export "
                    "(get_bus_df, get_branch_df, etc.), JSON serialization, "
                    "area-based aggregation.",
                    "documentation": results_docs,
                },
                "L5_data_model": {
                    "files": {
                        "multi_circuit.py": mc_loc,
                        "assets.py": assets_loc,
                        "numerical_circuit.py": nc_loc,
                    },
                    "role": "Network data model: MultiCircuit (device-oriented, "
                    "user-facing) -> NumericalCircuit (matrix-oriented, "
                    "solver-ready). Compilation step converts between them.",
                    "documentation": {
                        "multi_circuit": mc_docs,
                        "assets": assets_docs,
                        "numerical_circuit": nc_docs,
                    },
                },
            },
            "numerical_methods": nm_files,
            "pf_formulations": pf_form_files,
        }

        # Separation of concerns assessment
        separation = {
            "network_model_separate": True,
            "network_model_note": (
                "MultiCircuit (Devices/) is clearly separated from simulation code "
                "(Simulations/). NumericalCircuit bridges the two via a compilation "
                "step (compile_numerical_circuit_at)."
            ),
            "problem_formulation_separate": True,
            "problem_formulation_note": (
                "PF: Solver algorithms are in power_flow_worker.py as private "
                "functions. OPF: linear_opf_ts.py contains the full LP formulation "
                "(3146 lines in a single file -- very large). Formulation is "
                "procedural, not class-based."
            ),
            "solver_interface_separate": True,
            "solver_interface_note": (
                "MIP solvers abstracted via Utils/MIP/ with PuLP and OR-Tools "
                "backends behind a common LpModel interface. PF solvers (NR, HELM, "
                "etc.) are implemented directly in NumPy/SciPy -- no external NLP "
                "solver dependency for PF."
            ),
            "results_separate": True,
            "results_note": (
                "PowerFlowResults and OptimalPowerFlowResults are dedicated classes "
                "with DataFrame export, JSON serialization, and area aggregation. "
                "Clean separation from solve logic."
            ),
        }

        # Internal documentation quality
        doc_quality = {
            "api_coverage": (
                f"{api_docs['with_docstring']}/{api_docs['total_defs']} functions documented"
            ),
            "driver_coverage": (
                f"{driver_docs['with_docstring']}/{driver_docs['total_defs']} functions documented"
            ),
            "worker_coverage": (
                f"{worker_docs['with_docstring']}/{worker_docs['total_defs']} functions documented"
            ),
            "external_docs": (
                "ReadTheDocs documentation exists but changelog stops at v5.0.2. "
                "API reference is auto-generated. No dedicated developer guide for "
                "extending the OPF formulation."
            ),
            "code_comments": (
                "Inline comments present throughout, especially in formulation code. "
                "Mathematical notation used in variable naming (e.g., Bdc, Sbus, Sf). "
                "Formulation functions have parameter docstrings."
            ),
        }

        # Architecture concerns
        concerns = {
            "large_files": (
                "Several files exceed 1000 LOC: assets.py (7671), multi_circuit.py "
                "(3199), linear_opf_ts.py (3146), power_flow_worker.py (1031). "
                "The OPF formulation file is particularly monolithic."
            ),
            "deep_inheritance": (
                "MultiCircuit -> Assets -> object. Assets.__slots__ contains 40+ "
                "device list attributes. Not deeply nested but very wide."
            ),
            "compile_step": (
                "The MultiCircuit -> NumericalCircuit compilation step "
                "(compile_numerical_circuit_at) is a critical bottleneck for "
                "extensibility. Every solve recompiles. No caching."
            ),
            "engine_extensibility": (
                "PowerFlowDriver supports 5 compute engines (VeraGrid, NewtonPA, "
                "Bentayga, PGM, GSLV) via EngineType enum. Adding a new engine "
                "requires modifying the driver's run() method."
            ),
        }

        results["details"]["architecture"] = architecture
        results["details"]["separation_of_concerns"] = separation
        results["details"]["documentation_quality"] = doc_quality
        results["details"]["architecture_concerns"] = concerns

        results["details"]["summary"] = {
            "abstraction_layers": 5,
            "total_loc_dcpf_path": (api_loc + driver_loc + worker_loc + results_loc + nc_loc),
            "total_loc_data_model": mc_loc + assets_loc + nc_loc,
            "opf_formulation_loc": opf_form_loc,
            "all_concerns_separated": all(
                separation[k] for k in separation if k.endswith("_separate")
            ),
        }

        results["status"] = "informational"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
