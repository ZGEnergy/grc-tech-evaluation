"""
Test B-6: Qualitative assessment of DCPF solve path architecture

Dimension: extensibility
Network: TINY (IEEE 39-bus New England)
Pass condition: Document: number of abstraction layers, whether network model /
    problem formulation / solver interface / results are separated, whether
    internal interfaces are documented.
Tool: pandapower 3.4.0

Note: This is a code audit, not a functional test. Trace the DCPF solve path
through pandapower source code.
"""

from __future__ import annotations

import json
import time
import traceback


def run(
    network_file: str = "data/networks/case39.m",
    timeseries_dir: str | None = None,
) -> dict:
    """Execute DCPF architecture audit."""
    results: dict = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        import inspect

        import pandapower as pp
        import pandapower.pd2ppc as pd2ppc_mod
        import pandapower.pypower.dcpf as dcpf_mod
        import pandapower.pypower.makeBdc as makeBdc_mod
        import pandapower.results as results_mod
        import pandapower.run as run_mod

        # --- Layer 1: Public API ---
        layer1 = {
            "name": "Public API (pandapower.run)",
            "entry_point": "pp.rundcpp(net, ...)",
            "function": "rundcpp",
            "module": inspect.getfile(pp.rundcpp),
            "documented": True,
            "description": (
                "Top-level user-facing function. Sets DC-specific options via "
                "_init_rundcpp_options(), then delegates to _powerflow(). "
                "Parameters control transformer model, loading calculation, "
                "connectivity checking, and switch impedance handling."
            ),
        }

        # --- Layer 2: Internal orchestration ---
        layer2 = {
            "name": "Internal Orchestration (pandapower.run._powerflow)",
            "function": "_powerflow",
            "module": inspect.getfile(run_mod._powerflow),
            "documented": False,
            "description": (
                "Coordinates the full solve pipeline: "
                "(1) _add_auxiliary_elements - creates gen elements for dcline endpoints, "
                "(2) _pd2ppc - converts pandapower DataFrames to PYPOWER ppc format, "
                "(3) _run_pf_algorithm - dispatches to the appropriate solver, "
                "(4) _ppci_to_net - maps results back to pandapower DataFrames. "
                "This is the central orchestration point separating data model from solver."
            ),
        }

        # --- Layer 3: Data model conversion ---
        layer3 = {
            "name": "Data Model Conversion (pandapower.pd2ppc._pd2ppc)",
            "function": "_pd2ppc",
            "module": inspect.getfile(pd2ppc_mod._pd2ppc),
            "documented": False,
            "description": (
                "Converts pandapower's DataFrame-based network model to PYPOWER's "
                "numpy-array-based ppc format. Handles: bus type assignment, "
                "generator aggregation at buses, load to bus injection conversion, "
                "branch impedance calculation, transformer modeling, switch handling, "
                "and bus reindexing. Returns both ppc (external numbering) and ppci "
                "(internal consecutive numbering). Stores lookup tables in "
                "net._pd2ppc_lookups for reverse mapping."
            ),
        }

        # --- Layer 4: Problem formulation ---
        layer4 = {
            "name": "Problem Formulation (pandapower.pypower.makeBdc)",
            "function": "makeBdc",
            "module": inspect.getfile(makeBdc_mod.makeBdc),
            "documented": True,
            "description": (
                "Constructs the DC power flow B-matrices from PYPOWER bus/branch "
                "arrays. Returns Bbus (bus admittance), Bf (branch-from admittance), "
                "Pbusinj and Pfinj (phase-shifter injection corrections). "
                "Uses full B-matrix formulation incorporating tap ratios and "
                "phase shift angles. This is the mathematical core separating "
                "network topology from the linear solve."
            ),
        }

        # --- Layer 5: Solver ---
        layer5 = {
            "name": "Solver (pandapower.pypower.dcpf.dcpf)",
            "function": "dcpf",
            "module": inspect.getfile(dcpf_mod.dcpf),
            "documented": True,
            "description": (
                "Direct linear solve: Va = Bbus \\ Pinj. Uses scipy.sparse.linalg.spsolve "
                "for the linear system. No iterative solver needed for DC power flow. "
                "Returns the voltage angle vector which is then used to compute branch "
                "flows via Bf @ Va + Pfinj."
            ),
        }

        # --- Layer 6: Result extraction ---
        layer6 = {
            "name": "Result Extraction (pandapower.results)",
            "function": "_extract_results / _ppci_to_net",
            "module": inspect.getfile(results_mod._extract_results),
            "documented": False,
            "description": (
                "Maps PYPOWER result arrays back to pandapower DataFrames. "
                "Populates net.res_bus, net.res_line, net.res_gen, net.res_trafo, "
                "net.res_ext_grid with MW flows, voltage angles, loading percentages. "
                "Uses the _pd2ppc_lookups stored during conversion to reverse the "
                "bus reindexing. Sets net.converged flag."
            ),
        }

        layers = [layer1, layer2, layer3, layer4, layer5, layer6]
        results["details"]["abstraction_layers"] = layers
        results["details"]["num_layers"] = len(layers)

        # --- Separation analysis ---
        separation = {
            "network_model_separated": True,
            "network_model_notes": (
                "pandapower's DataFrame-based model (net.bus, net.gen, net.line, etc.) "
                "is cleanly separated from the PYPOWER numpy-array model (ppc/ppci). "
                "The _pd2ppc conversion is a well-defined boundary."
            ),
            "problem_formulation_separated": True,
            "problem_formulation_notes": (
                "makeBdc() constructs the B-matrices independently of the solver. "
                "The formulation (linear system) is separate from the data model "
                "conversion and the solve step."
            ),
            "solver_interface_separated": True,
            "solver_interface_notes": (
                "dcpf() is a standalone function taking matrices and vectors. "
                "For OPF, the solver interface goes through opf() in PYPOWER "
                "which uses an interior-point method. The solver is decoupled "
                "from formulation."
            ),
            "results_separated": True,
            "results_notes": (
                "Result extraction is a distinct module (pandapower.results) with "
                "dedicated functions per element type. Results are stored in "
                "separate res_* DataFrames, cleanly separated from input data."
            ),
        }
        results["details"]["separation_analysis"] = separation

        # --- Documentation analysis ---
        documentation = {
            "public_api_documented": True,
            "public_api_notes": (
                "rundcpp(), runpp(), rundcopp(), runopp() are fully documented "
                "with docstrings and ReadTheDocs pages covering all parameters."
            ),
            "internal_interfaces_documented": False,
            "internal_interfaces_notes": (
                "_powerflow(), _pd2ppc(), _ppci_to_net() are internal functions "
                "with leading underscores. They have docstrings but are not in "
                "the public API documentation. The PYPOWER layer (makeBdc, dcpf, "
                "makePTDF) has its own documentation inherited from PYPOWER."
            ),
            "result_schema_documented": True,
            "result_schema_notes": (
                "Result DataFrame columns (p_mw, q_mvar, va_degree, vm_pu, "
                "loading_percent, etc.) are documented on ReadTheDocs with "
                "per-element-type result tables."
            ),
        }
        results["details"]["documentation_analysis"] = documentation

        # --- Verify the call chain exists by introspection ---
        # Check key functions exist
        assert hasattr(run_mod, "_powerflow"), "_powerflow not found"
        assert hasattr(pd2ppc_mod, "_pd2ppc"), "_pd2ppc not found"
        assert hasattr(makeBdc_mod, "makeBdc"), "makeBdc not found"
        assert hasattr(dcpf_mod, "dcpf"), "dcpf not found"
        assert hasattr(results_mod, "_extract_results"), "_extract_results not found"

        # Get line counts for key modules
        module_locs = {}
        for name, mod in [
            ("run.py", run_mod),
            ("pd2ppc.py", pd2ppc_mod),
            ("makeBdc.py", makeBdc_mod),
            ("dcpf.py", dcpf_mod),
            ("results.py", results_mod),
        ]:
            src = inspect.getsource(mod)
            module_locs[name] = len(src.splitlines())

        results["details"]["module_line_counts"] = module_locs

        # Architecture quality summary
        results["details"]["architecture_summary"] = {
            "pattern": "Layered pipeline with data model boundary",
            "strengths": [
                "Clean DataFrame ↔ numpy-array boundary (_pd2ppc / _ppci_to_net)",
                "Reuses proven PYPOWER mathematical core",
                "Result DataFrames mirror input DataFrames (net.bus → net.res_bus)",
                "Modular element handling (each element type has its own converter)",
                "In-place modification pattern enables contingency analysis",
            ],
            "weaknesses": [
                "PYPOWER layer is a fork, not a dependency — maintenance burden",
                "OPF result dict (duals, multipliers) is discarded during result extraction",
                "Internal conversion functions are undocumented private API",
                "Two numbering schemes (external pandapower vs internal PYPOWER) "
                "create complexity in lookup management",
            ],
        }

        results["status"] = "pass"

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
