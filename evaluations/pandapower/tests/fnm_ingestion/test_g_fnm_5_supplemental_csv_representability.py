"""
Test G-FNM-5: Supplemental CSV representability assessment

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01)
Pass condition: No hard pass/fail gate. Evidence-collection test. Per-CSV
    representability report with N/E/X classifications and market solution
    fidelity summary.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import time
import traceback

# pandapower representability classifications for each supplemental CSV field.
# Derived from the analytical reference in data/fnm/docs/supplemental-csvs.md
# and validated against pandapower 3.4.0's data model.

CLASSIFICATIONS = {
    "LINE_AND_TRANSFORMER": {
        "FROM_BUS": ("N", "line.from_bus / trafo.hv_bus"),
        "TO_BUS": ("N", "line.to_bus / trafo.lv_bus"),
        "CKT": ("E", "custom column on line/trafo DataFrame"),
        "ELEMENT_TYPE": ("E", "custom column on line/trafo DataFrame"),
        "RATE_A": (
            "N",
            "line.max_i_ka (converted from MVA via voltage); trafo.sn_mva for transformers",
        ),
        "RATE_B": ("E", "custom column on line/trafo DataFrame"),
        "RATE_C": ("E", "custom column on line/trafo DataFrame"),
        "RATE_D": ("E", "custom column on line/trafo DataFrame"),
        "STATUS": ("N", "line.in_service / trafo.in_service (bool)"),
        "EFFECTIVE_DATE": ("E", "custom column on line/trafo DataFrame"),
    },
    "CONTINGENCY": {
        "CONTINGENCY_NAME": (
            "X",
            "pandapower has no native contingency definition model. "
            "Contingency analysis (run_contingency) takes element indices "
            "as input, not named contingency objects.",
        ),
        "ELEMENT_TYPE": (
            "X",
            "No contingency model means no element type association. "
            "Contingency analysis operates on element indices directly.",
        ),
        "ELEMENT_FROM_BUS": ("N", "line.from_bus / trafo.hv_bus"),
        "ELEMENT_TO_BUS": ("N", "line.to_bus / trafo.lv_bus"),
        "ELEMENT_CKT": ("E", "custom column on element DataFrames"),
        "ELEMENT_BUS": ("N", "gen.bus"),
    },
    "INTERFACE": {
        "INTERFACE_ID": (
            "X",
            "pandapower has no interface/flowgate model. "
            "No structural analog for named groups of branches "
            "with aggregate flow limits.",
        ),
        "INTERFACE_NAME": ("X", "No interface model in pandapower."),
        "NORMAL_LIMIT_MW": ("X", "No interface model in pandapower."),
        "EMERGENCY_LIMIT_MW": ("X", "No interface model in pandapower."),
        "DIRECTION": ("X", "No interface model in pandapower."),
    },
    "INTERFACE_ELEMENT": {
        "INTERFACE_ID": ("X", "No interface model in pandapower."),
        "FROM_BUS": ("N", "line.from_bus"),
        "TO_BUS": ("N", "line.to_bus"),
        "CKT": ("E", "custom column on line DataFrame"),
        "DIRECTION_COEFF": ("X", "No interface model in pandapower."),
        "WEIGHT_FACTOR": ("X", "No interface model in pandapower."),
    },
    "GEN_DISTRIBUTION_FACTOR": {
        "GEN_BUS": ("N", "gen.bus"),
        "GEN_ID": ("E", "custom column on gen DataFrame"),
        "HUB_NAME": (
            "X",
            "pandapower has no trading hub or generator distribution "
            "factor concept. These are market-layer abstractions "
            "outside the power flow domain.",
        ),
        "PARTICIPATION_FACTOR": (
            "X",
            "No generator distribution factor attribute. "
            "pandapower does not model hub-based allocation.",
        ),
        "GEN_NAME": ("N", "gen.name"),
    },
    "TRADING_HUB": {
        "HUB_NAME": (
            "X",
            "pandapower has no trading hub model. Hubs are market "
            "constructs with no analog in the power flow domain.",
        ),
        "BUS_NUMBER": ("N", "bus index (integer bus number)"),
        "DISTRIBUTION_FACTOR": (
            "X",
            "No hub model, so distribution factors cannot be "
            "associated with buses within pandapower.",
        ),
        "HUB_TYPE": ("X", "No hub model in pandapower."),
    },
    "OUTAGE": {
        "ELEMENT_TYPE": (
            "X",
            "pandapower has no outage schedule model. "
            "Elements can be set out of service (in_service=False) "
            "but there is no temporal outage scheduling.",
        ),
        "ELEMENT_FROM_BUS": ("N", "line.from_bus / trafo.hv_bus"),
        "ELEMENT_TO_BUS": ("N", "line.to_bus / trafo.lv_bus"),
        "ELEMENT_CKT": ("E", "custom column on element DataFrames"),
        "ELEMENT_BUS": ("N", "gen.bus"),
        "OUTAGE_START": ("X", "No temporal outage model in pandapower."),
        "OUTAGE_END": ("X", "No temporal outage model in pandapower."),
        "OUTAGE_TYPE": ("X", "No outage classification model in pandapower."),
    },
}


def run() -> dict:
    """Execute the G-FNM-5 supplemental CSV representability assessment.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results = {
        "status": "informational",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        # Aggregate statistics per CSV
        csv_summaries = {}
        total_n = 0
        total_e = 0
        total_x = 0
        total_fields = 0

        for csv_name, fields in CLASSIFICATIONS.items():
            n_count = sum(1 for cls, _ in fields.values() if cls == "N")
            e_count = sum(1 for cls, _ in fields.values() if cls == "E")
            x_count = sum(1 for cls, _ in fields.values() if cls == "X")
            field_count = len(fields)

            csv_summaries[csv_name] = {
                "fields": field_count,
                "native": n_count,
                "extension": e_count,
                "external": x_count,
                "n_pct": round(n_count / field_count * 100, 1),
                "e_pct": round(e_count / field_count * 100, 1),
                "x_pct": round(x_count / field_count * 100, 1),
                "field_detail": {
                    fname: {"classification": cls, "mechanism": mech}
                    for fname, (cls, mech) in fields.items()
                },
            }

            total_n += n_count
            total_e += e_count
            total_x += x_count
            total_fields += field_count

        results["details"]["csv_summaries"] = csv_summaries
        results["details"]["totals"] = {
            "fields": total_fields,
            "native": total_n,
            "extension": total_e,
            "external": total_x,
            "n_pct": round(total_n / total_fields * 100, 1),
            "e_pct": round(total_e / total_fields * 100, 1),
            "x_pct": round(total_x / total_fields * 100, 1),
        }

        # Market solution fidelity summary
        results["details"]["market_fidelity"] = {
            "n1_n2_contingency_enforcement": {
                "classification": "achievable",
                "notes": (
                    "pandapower.contingency.run_contingency() supports N-1 sweeps "
                    "with both DCPF and ACPF. N-2 requires custom scripting over "
                    "element pairs. No native contingency definition objects — "
                    "contingencies are specified by element indices. SCOPF is not "
                    "supported natively (no contingency constraints in OPF)."
                ),
            },
            "interface_flow_limits": {
                "classification": "complex",
                "notes": (
                    "pandapower has no native interface/flowgate concept. "
                    "Interface flow limits would require: (1) computing branch "
                    "flows post-solve, (2) aggregating by interface definition "
                    "from an external DataFrame, (3) checking against limits. "
                    "Not enforceable within the OPF formulation without the "
                    "PandaModels.jl Julia bridge for custom constraints."
                ),
            },
            "aggregate_hub_pricing": {
                "classification": "complex",
                "notes": (
                    "pandapower has no hub model. Hub LMP computation requires: "
                    "(1) extracting bus-level LMPs from OPF, (2) applying "
                    "PTDF-weighted or distribution-factor-weighted averaging "
                    "from an external hub definition DataFrame. Feasible as "
                    "post-processing but entirely external to pandapower."
                ),
            },
            "outage_scheduling": {
                "classification": "achievable",
                "notes": (
                    "pandapower supports setting elements out of service via "
                    "in_service=False. Temporal scheduling requires external "
                    "logic to modify in_service status across time periods. "
                    "The timeseries module can automate this via controllers, "
                    "but outage definitions must be maintained externally."
                ),
            },
        }

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
