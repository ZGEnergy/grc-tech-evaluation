"""
Test B-6: Code Architecture Assessment

Dimension: extensibility
Network: TINY (IEEE 39-bus, case39.m)
Pass condition: Document number of abstraction layers, whether network model /
  problem formulation / solver interface / results are separable, and where
  custom logic can be injected.
Tool: PyPSA 1.1.2

Note: This is a qualitative architecture assessment. The script uses inspect
to trace the call path from n.lpf() to the matrix solve, then produces a
structured report of the architecture findings.
"""

import inspect
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_NETWORK = str(REPO_ROOT / "data" / "networks" / "case39.m")


def load_network(network_file: str):
    """Load case39.m via matpowercaseframes -> pypower ppc dict -> pypsa."""
    import pypsa
    from matpowercaseframes import CaseFrames

    cf = CaseFrames(network_file)
    ppc = {
        "version": "2",
        "baseMVA": cf.baseMVA,
        "bus": cf.bus.values,
        "gen": cf.gen.values,
        "branch": cf.branch.values,
    }
    n = pypsa.Network()
    n.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=True)
    return n


def trace_call_chain() -> dict:
    """Use inspect to locate key functions in the call chain."""
    import pypsa
    from pypsa import Network

    chain = {}

    # Top-level: n.lpf()
    try:
        lpf_file = inspect.getsourcefile(Network.lpf)
        lpf_src = inspect.getsource(Network.lpf)
        chain["Network.lpf"] = {
            "file": lpf_file,
            "loc": len(lpf_src.splitlines()),
        }
    except (TypeError, OSError) as e:
        chain["Network.lpf"] = {"error": str(e)}

    # SubNetwork.lpf — the actual computation
    try:
        import pypsa.pf as pf_mod

        if hasattr(pf_mod, "sub_network_lpf"):
            fn = pf_mod.sub_network_lpf
        else:
            # Try alternative location
            fn = getattr(pf_mod, "lpf", None)

        if fn:
            sn_lpf_file = inspect.getsourcefile(fn)
            sn_lpf_src = inspect.getsource(fn)
            chain["sub_network_lpf"] = {
                "file": sn_lpf_file,
                "loc": len(sn_lpf_src.splitlines()),
            }
        else:
            chain["sub_network_lpf"] = {"note": "not found as standalone function"}
    except Exception as e:
        chain["sub_network_lpf"] = {"error": str(e)}

    # Optimization: n.optimize (accessor, not a class method)
    try:
        # n.optimize is an OptimizationAccessor — locate via its module
        import pypsa.optimization.optimize as opt_module

        opt_file = inspect.getsourcefile(opt_module)
        opt_src = inspect.getsource(opt_module)
        chain["Network.optimize"] = {
            "file": opt_file,
            "loc": len(opt_src.splitlines()),
            "type": "OptimizationAccessor",
        }
        # Also inspect create_model
        from pypsa.optimization.optimize import OptimizationAccessor

        cm_src = inspect.getsource(OptimizationAccessor.create_model)
        chain["OptimizationAccessor.create_model"] = {
            "loc": len(cm_src.splitlines()),
        }
    except (TypeError, OSError, ImportError) as e:
        chain["Network.optimize"] = {"error": str(e)}

    # Mixin architecture
    try:
        # List all base classes of Network
        base_classes = [c.__name__ for c in Network.__mro__]
        chain["Network_base_classes"] = base_classes
    except Exception as e:
        chain["Network_base_classes"] = {"error": str(e)}

    # Module structure
    try:
        pypsa_root = Path(inspect.getfile(pypsa)).parent
        py_files = sorted([f.name for f in pypsa_root.glob("*.py")])
        chain["pypsa_modules"] = py_files
        chain["pypsa_root"] = str(pypsa_root)
    except Exception as e:
        chain["pypsa_modules"] = {"error": str(e)}

    return chain


def assess_architecture(n, chain: dict) -> dict:
    """Produce structured architecture assessment."""
    assessment = {}

    # 1. Abstraction layers
    assessment["abstraction_layers"] = [
        {
            "layer": 1,
            "name": "User API",
            "description": (
                "n.lpf(), n.pf(), n.optimize() — single-call entry points. "
                "Hides all internal complexity. Returns None; results in n.*_t attributes."
            ),
        },
        {
            "layer": 2,
            "name": "Network Mixin Dispatch",
            "description": (
                "Network class is composed of 8+ mixins (NetworkMixin, OptimizationMixin, "
                "PowerFlowMixin, GraphMixin, etc.). n.lpf() dispatches to sub_network_lpf() "
                "for each sub-network in n.sub_networks."
            ),
        },
        {
            "layer": 3,
            "name": "SubNetwork Computation",
            "description": (
                "SubNetwork objects own the B-matrix, PTDF, and linear algebra. "
                "sub_network.lpf() builds the B-matrix from n.lines/transformers, "
                "applies per-unit admittances, solves Bθ=P using scipy.sparse.linalg."
            ),
        },
        {
            "layer": 4,
            "name": "Linear Algebra Backend",
            "description": (
                "scipy.sparse + numpy. No external solver for DCPF — solved directly "
                "via sparse LU factorization. AC PF (n.pf()) uses Newton-Raphson with "
                "scipy.sparse solvers. OPF (n.optimize()) uses linopy + HiGHS."
            ),
        },
    ]

    # 2. Separability
    assessment["separability"] = {
        "model_build_vs_solve": {
            "verdict": "clean for OPF; implicit for PF",
            "detail": (
                "For n.optimize(): model build (n.optimize.create_model()) and solve "
                "(n.optimize.solve_model()) are explicitly separate steps. "
                "For n.lpf(): the B-matrix construction and solve happen inside "
                "sub_network_lpf() without explicit separation, but the PTDF can be "
                "extracted independently via sub_network.calculate_PTDF()."
            ),
        },
        "data_model_vs_formulation": {
            "verdict": "well separated",
            "detail": (
                "Network data lives in n.buses, n.lines, n.generators (static DataFrames) "
                "and n.*_t (time-series DataFrames). Formulation logic lives in pf.py, "
                "optimization/*.py modules. No mixing of data and math."
            ),
        },
        "solver_interface": {
            "verdict": "abstracted via linopy for OPF; direct for PF",
            "detail": (
                "OPF: solver selected via solver_name kwarg; solver_options dict passed "
                "through linopy to the backend. Swapping from HiGHS to GLPK is one kwarg. "
                "DCPF: no solver kwarg — scipy.sparse is hard-coded. Not swappable."
            ),
        },
        "results_extraction": {
            "verdict": "clean read-only DataFrames",
            "detail": (
                "All results in n.*_t accessors (buses_t.v_ang, lines_t.p0, etc.). "
                "These are pandas DataFrames — zero-friction interoperability. "
                "No unwrapping, no special result objects."
            ),
        },
    }

    # 3. Injection points
    assessment["injection_points"] = [
        {
            "name": "extra_functionality",
            "type": "OPF custom constraints",
            "access": "public API",
            "description": (
                "n.optimize(extra_functionality=fn) where fn(n, snapshots) receives "
                "the fully built linopy model as n.model. Full JuMP/linopy API available "
                "to add custom constraints, objectives, or variables before solve."
            ),
            "durability": "stable",
        },
        {
            "name": "n.model",
            "type": "linopy model direct access",
            "access": "public attribute after create_model()",
            "description": (
                "n.optimize.create_model() exposes n.model as a linopy.Model. "
                "Can add variables/constraints/objective terms before calling "
                "n.optimize.solve_model(). Fully documented."
            ),
            "durability": "stable",
        },
        {
            "name": "sub_network.calculate_PTDF()",
            "type": "PTDF matrix extraction",
            "access": "public API",
            "description": (
                "Exposes sub_network.PTDF (numpy array) after determine_network_topology(). "
                "Enables custom sensitivity analyses, BODF computation, flow-based market "
                "coupling, etc."
            ),
            "durability": "stable",
        },
        {
            "name": "n.graph()",
            "type": "NetworkX graph export",
            "access": "public API",
            "description": (
                "Returns networkx.MultiGraph with full NetworkX API available. "
                "Enables topological analysis, shortest paths, graph algorithms."
            ),
            "durability": "stable",
        },
        {
            "name": "Component DataFrames",
            "type": "In-place data modification",
            "access": "public API",
            "description": (
                "n.lines, n.buses, n.generators are pandas DataFrames. Parameters can be "
                "modified in-place before solve. n.add(), n.remove() for component addition/removal."
            ),
            "durability": "stable",
        },
    ]

    # 4. Architecture quality summary
    assessment["quality_summary"] = {
        "mixin_count": len(
            [c for c in chain.get("Network_MRO", []) if "Mixin" in c or "Accessor" in c]
        ),
        "module_count": len(chain.get("pypsa_modules", [])),
        "positive": [
            "Clean separation of data model (DataFrames) from computation (pf.py, optimization/)",
            "OPF model build/solve separation is explicit and well-documented",
            "extra_functionality injection point is idiomatic and documented in examples",
            "All results as pandas DataFrames — zero-friction interop",
            "NetworkX graph export is a single API call",
            "PTDF accessible via public API after topology determination",
        ],
        "negative": [
            "DCPF solver (scipy.sparse) is hard-coded — not swappable via kwarg",
            "lpf_contingency() is broken on Python 3.12+ (known bug, no workaround in public API)",
            "SubNetwork access requires knowing internal data structure (n.sub_networks.at['0','obj'])",
            "Mixin architecture creates non-obvious method resolution order",
        ],
    }

    return assessment


def run(network_file: str = DEFAULT_NETWORK, timeseries_dir: str | None = None) -> dict:
    """Assess PyPSA code architecture by tracing the DCPF call path.

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
        # 1. Load network (needed for dynamic assessment)
        n = load_network(network_file)
        n.lpf()

        # 2. Trace call chain via inspect
        chain = trace_call_chain()

        # 3. Produce architecture assessment
        assessment = assess_architecture(n, chain)

        results["details"]["call_chain"] = chain
        results["details"]["architecture"] = assessment
        results["details"]["n_abstraction_layers"] = len(assessment["abstraction_layers"])
        results["details"]["n_injection_points"] = len(assessment["injection_points"])

        print("=== PyPSA Architecture Assessment ===")
        print(f"Abstraction layers: {results['details']['n_abstraction_layers']}")
        print(f"Injection points: {results['details']['n_injection_points']}")
        print("\nKey modules:")
        for m in chain.get("pypsa_modules", [])[:15]:
            print(f"  {m}")
        print("\nMRO (first 10):")
        for c in chain.get("Network_MRO", [])[:10]:
            print(f"  {c}")

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
