"""B-6 (code_architecture) — Qualitative architecture assessment of PyPSA.

Trace DCPF solve path from n.lpf() to actual computation.
Document abstraction layers, separation of concerns.
No network tier — purely qualitative.
"""

from __future__ import annotations

import inspect
import json

import pypsa


def run() -> dict:
    """Execute B-6 code architecture assessment."""
    details = {}

    # 1. Trace n.lpf() call chain
    lpf_method = pypsa.Network.lpf
    details["lpf_location"] = f"{inspect.getfile(lpf_method)}"
    details["lpf_source_lines"] = len(inspect.getsource(lpf_method).splitlines())

    # 2. Trace n.optimize() call chain
    # PyPSA uses an OptimizationAccessor pattern
    from pypsa.optimization import optimize

    details["optimize_module"] = inspect.getfile(optimize)

    # 3. Key modules in the DCPF path
    modules_in_path = []

    # pypsa.network.power_flow — power flow module
    from pypsa.network import power_flow as pf

    modules_in_path.append(
        {
            "module": "pypsa.network.power_flow",
            "file": inspect.getfile(pf),
            "purpose": "Power flow solvers (lpf, pf, sub_network_lpf, etc.)",
            "lines": len(inspect.getsource(pf).splitlines()),
        }
    )

    # pypsa.optimization.optimize — optimization entry point
    modules_in_path.append(
        {
            "module": "pypsa.optimization.optimize",
            "file": inspect.getfile(optimize),
            "purpose": "OPF entry point, create_model/solve_model workflow",
            "lines": len(inspect.getsource(optimize).splitlines()),
        }
    )

    # pypsa.optimization.constraints
    from pypsa.optimization import constraints

    modules_in_path.append(
        {
            "module": "pypsa.optimization.constraints",
            "file": inspect.getfile(constraints),
            "purpose": "Constraint definitions for OPF (nodal balance, line limits, etc.)",
            "lines": len(inspect.getsource(constraints).splitlines()),
        }
    )

    # pypsa.optimization.variables
    from pypsa.optimization import variables

    modules_in_path.append(
        {
            "module": "pypsa.optimization.variables",
            "file": inspect.getfile(variables),
            "purpose": "Variable definitions for OPF (generator dispatch, line flows, etc.)",
            "lines": len(inspect.getsource(variables).splitlines()),
        }
    )

    # pypsa.optimization.global_constraints
    from pypsa.optimization import global_constraints

    modules_in_path.append(
        {
            "module": "pypsa.optimization.global_constraints",
            "file": inspect.getfile(global_constraints),
            "purpose": "Global constraints (CO2 limits, etc.)",
            "lines": len(inspect.getsource(global_constraints).splitlines()),
        }
    )

    # linopy — the optimization modeling layer
    import linopy

    modules_in_path.append(
        {
            "module": "linopy",
            "file": inspect.getfile(linopy),
            "purpose": "Linear optimization modeling framework (linopy.Model)",
            "lines": "N/A (package)",
        }
    )

    # pypsa.network — network data model
    from pypsa import network

    modules_in_path.append(
        {
            "module": "pypsa.network",
            "file": inspect.getfile(network),
            "purpose": "Network data model (Network class, components, IO)",
            "lines": "N/A (subpackage)",
        }
    )

    details["modules_in_dcpf_path"] = modules_in_path

    # 4. Separation of concerns analysis
    details["architecture_layers"] = [
        {
            "layer": "Data Model",
            "module": "pypsa.Network",
            "description": (
                "Network class holds buses, generators, lines, transformers, loads as "
                "pandas DataFrames. Time-varying data stored in *_t attributes. "
                "Clean separation from solver."
            ),
        },
        {
            "layer": "Power Flow Solver",
            "module": "pypsa.network.power_flow",
            "description": (
                "Direct DCPF and ACPF solvers. DCPF uses numpy linear algebra "
                "(sparse matrix solve). ACPF uses Newton-Raphson iteration. "
                "Operates on Network data model directly."
            ),
        },
        {
            "layer": "Optimization Formulation",
            "module": "pypsa.optimization.*",
            "description": (
                "Builds linopy.Model from Network. Variables, constraints, and "
                "objective are defined in separate modules. create_model() assembles "
                "the full formulation; user can add constraints before solving."
            ),
        },
        {
            "layer": "Solver Interface",
            "module": "linopy",
            "description": (
                "Abstracted solver interface. Supports HiGHS, Gurobi, CPLEX, GLPK, "
                "SCIP via unified API. Solver swap is a parameter change."
            ),
        },
        {
            "layer": "Results",
            "module": "pypsa.optimization.optimize.assign_solution()",
            "description": (
                "Solution values assigned back to Network DataFrames. "
                "Results accessible as n.generators_t.p, n.buses_t.marginal_price, etc."
            ),
        },
    ]

    # 5. Internal interface documentation
    details["internal_docs"] = {
        "linopy_model_documented": True,
        "create_model_documented": True,
        "add_constraints_documented": True,
        "extra_functionality_callback": (
            "Documented but deprecated in favor of create_model/solve_model workflow"
        ),
        "network_graph_documented": True,
        "sub_network_methods_documented": "Partially (PTDF, BODF documented)",
    }

    # 6. Version info
    details["pypsa_version"] = pypsa.__version__
    details["linopy_version"] = linopy.__version__

    return {
        "test_id": "B-6",
        "slug": "code_architecture",
        "tier": "N/A",
        "status": "PASS",
        "wall_clock_seconds": 0.0,
        "details": details,
        "errors": [],
        "workarounds": [],
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
