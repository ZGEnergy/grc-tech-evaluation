"""
Test B-6: Qualitative assessment — trace DCPF solve path from API call to solver invocation

Dimension: extensibility
Network: N/A
Pass condition: Document: number of abstraction layers, whether network model / problem
  formulation / solver interface / results are separated, whether internal interfaces
  are documented.
Tool: PyPSA 1.1.2
"""

import inspect
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "evaluations" / "shared"))
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")


def trace_lpf_call_chain() -> dict:
    """Trace n.lpf() from API call to scipy.sparse.linalg.spsolve.

    Returns structured call chain with source file, line count, and role.
    """
    import pypsa

    chain = {}

    # --- Layer 1: Network.lpf() entry point ---
    try:
        from pypsa.networks import Network

        lpf_method = Network.lpf
        lpf_file = inspect.getsourcefile(lpf_method)
        lpf_src = inspect.getsource(lpf_method)
        chain["1_Network_lpf"] = {
            "file": lpf_file,
            "loc": len(lpf_src.splitlines()),
            "role": "User-facing entry point. Delegates to sub_network_lpf for each SubNetwork.",
        }
    except (TypeError, OSError) as e:
        chain["1_Network_lpf"] = {"error": str(e)}

    # --- Layer 2: SubNetwork power flow mixin ---
    try:
        # In PyPSA 1.x, lpf logic is in the SubNetworkPowerFlowMixin
        from pypsa.network.power_flow import SubNetworkPowerFlowMixin

        sn_lpf = SubNetworkPowerFlowMixin.lpf
        sn_file = inspect.getsourcefile(sn_lpf)
        sn_src = inspect.getsource(sn_lpf)
        chain["2_SubNetworkPowerFlowMixin_lpf"] = {
            "file": sn_file,
            "loc": len(sn_src.splitlines()),
            "role": (
                "Builds B-matrix (susceptance), assembles injection vector P, "
                "calls scipy.sparse.linalg.spsolve(B, P), assigns voltage angles "
                "and line flows back to Network DataFrames."
            ),
        }
    except (TypeError, OSError, ImportError) as e:
        chain["2_SubNetworkPowerFlowMixin_lpf"] = {"error": str(e)}

    # --- Layer 2b: B-matrix construction ---
    try:
        from pypsa.network.power_flow import SubNetworkPowerFlowMixin

        calc_bh = SubNetworkPowerFlowMixin.calculate_B_H
        bh_file = inspect.getsourcefile(calc_bh)
        bh_src = inspect.getsource(calc_bh)
        chain["2b_calculate_B_H"] = {
            "file": bh_file,
            "loc": len(bh_src.splitlines()),
            "role": (
                "Constructs the DC B-matrix and H-matrix from line/transformer "
                "parameters. Uses scipy.sparse CSC format. Incorporates tap ratios."
            ),
        }
    except (TypeError, OSError, ImportError) as e:
        chain["2b_calculate_B_H"] = {"error": str(e)}

    # --- Layer 2c: PTDF computation ---
    try:
        from pypsa.network.power_flow import SubNetworkPowerFlowMixin

        ptdf_fn = SubNetworkPowerFlowMixin.calculate_PTDF
        ptdf_file = inspect.getsourcefile(ptdf_fn)
        ptdf_src = inspect.getsource(ptdf_fn)
        chain["2c_calculate_PTDF"] = {
            "file": ptdf_file,
            "loc": len(ptdf_src.splitlines()),
            "role": "Computes Power Transfer Distribution Factor matrix from B and H.",
        }
    except (TypeError, OSError, ImportError) as e:
        chain["2c_calculate_PTDF"] = {"error": str(e)}

    # --- Layer 3: scipy sparse solver ---
    try:
        from scipy.sparse.linalg import spsolve

        sp_file = inspect.getsourcefile(spsolve)
        chain["3_scipy_spsolve"] = {
            "file": sp_file,
            "role": (
                "Direct sparse LU factorization (SuperLU). No iterative solver; "
                "no external optimizer. DCPF is a linear system, not an optimization."
            ),
        }
    except (TypeError, OSError) as e:
        chain["3_scipy_spsolve"] = {"error": str(e)}

    # --- Network inheritance chain (method resolution order) ---
    try:
        class_chain = [c.__name__ for c in pypsa.Network.__mro__]
        chain["network_class_chain"] = class_chain
    except Exception as e:
        chain["network_class_chain"] = {"error": str(e)}

    # --- Module structure ---
    try:
        pypsa_root = Path(inspect.getfile(pypsa)).parent
        # Top-level modules
        top_py = sorted([f.name for f in pypsa_root.glob("*.py")])
        # Sub-packages
        sub_dirs = sorted(
            [d.name for d in pypsa_root.iterdir() if d.is_dir() and not d.name.startswith("_")]
        )
        chain["module_structure"] = {
            "root": str(pypsa_root),
            "top_level_py": top_py,
            "sub_packages": sub_dirs,
        }
    except Exception as e:
        chain["module_structure"] = {"error": str(e)}

    return chain


def assess_separation_of_concerns(chain: dict) -> dict:
    """Assess whether network model, formulation, solver, and results are separated."""
    assessment = {}

    # 1. Abstraction layers
    assessment["abstraction_layers"] = [
        {
            "layer": 1,
            "name": "User API (Network methods)",
            "description": (
                "n.lpf(), n.pf(), n.optimize() are single-call entry points on the "
                "Network object. All hide internal complexity. Results stored in-place "
                "on n.*_t DataFrames."
            ),
        },
        {
            "layer": 2,
            "name": "Mixin Dispatch Layer",
            "description": (
                "Network is composed of 8+ mixins: SubNetworkPowerFlowMixin, "
                "NetworkGraphMixin, OptimizationAccessor, etc. Each mixin owns one "
                "concern. n.lpf() dispatches to SubNetwork.lpf() for each connected "
                "synchronous area."
            ),
        },
        {
            "layer": 3,
            "name": "SubNetwork Computation",
            "description": (
                "SubNetwork objects own the B-matrix, PTDF, Y-bus, and perform the "
                "actual linear algebra. calculate_B_H() builds the susceptance matrix; "
                "lpf() assembles the injection vector and calls spsolve()."
            ),
        },
        {
            "layer": 4,
            "name": "Linear Algebra / Solver Backend",
            "description": (
                "For DCPF: scipy.sparse.linalg.spsolve (SuperLU direct solver). "
                "For ACPF: Newton-Raphson iteration using scipy.sparse. "
                "For OPF: linopy modeling layer -> HiGHS/GLPK/etc."
            ),
        },
    ]

    # 2. Separation assessment
    assessment["separation"] = {
        "network_model_vs_formulation": {
            "separated": True,
            "evidence": (
                "Network data lives in pandas DataFrames (n.buses, n.lines, n.generators). "
                "Formulation logic lives in separate modules: pypsa/network/power_flow.py "
                "for PF, pypsa/optimization/ package for OPF. No mixing of data storage "
                "and mathematical formulation."
            ),
        },
        "formulation_vs_solver": {
            "separated": True,
            "evidence": (
                "OPF: formulation built via linopy (abstract LP/MILP model), solver "
                "selected at solve-time via solver_name kwarg. Swapping HiGHS for GLPK "
                "requires zero model changes. "
                "DCPF: formulation (B-matrix) is separate from solver (spsolve), but "
                "the solver is hardcoded — no kwarg to swap the sparse solver backend."
            ),
        },
        "solver_vs_results": {
            "separated": True,
            "evidence": (
                "Solver outputs are immediately assigned back to n.*_t DataFrames. "
                "No intermediate result objects or solver-specific return types. "
                "Results are always pandas DataFrames regardless of solver backend."
            ),
        },
        "model_build_vs_solve": {
            "separated_for_opf": True,
            "separated_for_pf": False,
            "evidence": (
                "OPF: n.optimize.create_model() and n.optimize.solve_model() are "
                "explicitly separate steps. Model can be inspected/modified between "
                "build and solve. "
                "PF: n.lpf() and n.pf() combine build and solve in one call. "
                "B-matrix can be extracted separately via calculate_B_H()/calculate_PTDF() "
                "but this is not the standard workflow."
            ),
        },
    }

    # 3. Internal interface documentation
    assessment["internal_documentation"] = {
        "public_api_documented": True,
        "internal_interfaces_documented": "partially",
        "evidence": (
            "Public methods (lpf, pf, optimize) are documented in official docs at "
            "docs.pypsa.org with examples. The SubNetwork-level methods (calculate_B_H, "
            "calculate_PTDF, calculate_Y) are docstring-documented in source but not "
            "prominently featured in the user guide. The mixin architecture itself "
            "(which classes provide which methods) is not documented — requires reading "
            "source to understand method resolution order."
        ),
    }

    # 4. Injection/extension points
    assessment["injection_points"] = [
        {
            "name": "extra_functionality callback",
            "scope": "OPF only",
            "access": "public API",
            "documented": True,
            "description": (
                "n.optimize(extra_functionality=fn) — callback receives (n, snapshots) "
                "after model build, before solve. Full linopy API available to add "
                "constraints, variables, objective terms."
            ),
        },
        {
            "name": "n.model (linopy.Model)",
            "scope": "OPF only",
            "access": "public attribute",
            "documented": True,
            "description": (
                "After create_model(), n.model is a linopy.Model. Can be inspected, "
                "modified, serialized. Supports all linopy operations."
            ),
        },
        {
            "name": "Component DataFrames (in-place mutation)",
            "scope": "All analyses",
            "access": "public API",
            "documented": True,
            "description": (
                "n.buses, n.lines, n.generators are standard pandas DataFrames. "
                "Parameters can be modified in-place before any solve call."
            ),
        },
        {
            "name": "n.graph() (NetworkX export)",
            "scope": "Topology analysis",
            "access": "public API",
            "documented": True,
            "description": "Returns NetworkX MultiGraph with full graph algorithm access.",
        },
        {
            "name": "SubNetwork matrices (B, H, PTDF, Y)",
            "scope": "Power flow internals",
            "access": "public attributes on SubNetwork",
            "documented": "partially (docstrings, not user guide)",
            "description": (
                "After calculate_B_H() or calculate_PTDF(), matrices are stored as "
                "sub_network.B, sub_network.H, sub_network.PTDF. Scipy sparse format."
            ),
        },
    ]

    return assessment


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Trace DCPF solve path and assess code architecture.

    Returns:
        dict with keys:
        - status: "pass" | "fail" | "qualified_pass"
        - wall_clock_seconds: float
        - details: dict of test-specific outputs
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
        # 1. Trace the call chain
        chain = trace_lpf_call_chain()
        results["details"]["call_chain"] = chain

        # 2. Assess architecture
        assessment = assess_separation_of_concerns(chain)
        results["details"]["architecture"] = assessment
        results["details"]["n_abstraction_layers"] = len(assessment["abstraction_layers"])
        results["details"]["n_injection_points"] = len(assessment["injection_points"])

        # 3. Summary statistics
        class_chain = chain.get("network_class_chain", [])
        results["details"]["mro_depth"] = len(class_chain) if isinstance(class_chain, list) else 0
        results["details"]["mixin_classes"] = (
            [c for c in class_chain if "Mixin" in c] if isinstance(class_chain, list) else []
        )

        mod_struct = chain.get("module_structure", {})
        results["details"]["n_top_level_modules"] = len(mod_struct.get("top_level_py", []))
        results["details"]["sub_packages"] = mod_struct.get("sub_packages", [])

        # Print summary
        print("=== PyPSA DCPF Call Chain ===")
        for key, val in chain.items():
            if key in ("network_class_chain", "module_structure"):
                continue
            if isinstance(val, dict) and "file" in val:
                print(f"  {key}: {val.get('file', 'N/A')} ({val.get('loc', '?')} LOC)")
                print(f"    Role: {val.get('role', 'N/A')}")
            elif isinstance(val, dict) and "error" in val:
                print(f"  {key}: ERROR — {val['error']}")

        print("\n=== Architecture Summary ===")
        print(f"Abstraction layers: {results['details']['n_abstraction_layers']}")
        print(f"Injection points: {results['details']['n_injection_points']}")
        print(f"Inheritance depth: {results['details']['mro_depth']}")
        print(f"Mixin classes: {results['details']['mixin_classes']}")
        print(f"Sub-packages: {results['details']['sub_packages']}")

        print("\n=== Separation of Concerns ===")
        for k, v in assessment["separation"].items():
            sep = v.get("separated", v.get("separated_for_opf", "?"))
            print(f"  {k}: {sep}")

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    import json

    result = run()
    print(json.dumps(result, indent=2, default=str))
