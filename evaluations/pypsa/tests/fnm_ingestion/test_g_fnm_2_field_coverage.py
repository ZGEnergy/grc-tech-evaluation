"""G-FNM-2: Field Coverage Audit — LARGE FNM (~30K buses).

After successful ingestion, enumerate which fields from the field criticality
matrix are present in PyPSA's data model.

For each intermediate format table, check DCPF-critical and ACPF-critical fields.
100% DCPF-critical coverage is required to pass.

Tool: PyPSA
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

import numpy as np

MAT_PATH = Path("/workspace/data/fnm/reference/matpower_parse/mpc_case.mat")

# Field criticality definitions from the field-criticality-matrix.md
# Each entry: (intermediate_field, tier, pypsa_component, pypsa_attributes_to_check)
# tier: 1=DCPF-critical, 2=ACPF-critical, 3=Informational
# pypsa_attributes_to_check: list of candidate column names to look for

FIELD_COVERAGE = {
    "bus": [
        # DCPF-critical (Tier 1) — per field-criticality-matrix.md
        ("I", 1, "buses", ["__index__"]),
        ("IDE", 1, "buses", ["control", "type"]),
        ("VA", 1, "buses", ["v_ang_set"]),
        # ACPF-critical (Tier 2)
        ("BASKV", 2, "buses", ["v_nom"]),
        ("VM", 2, "buses", ["v_mag_pu_set"]),
        # Informational (Tier 3)
        ("NAME", 3, "buses", ["name"]),
        ("AREA", 3, "buses", ["area"]),
        ("ZONE", 3, "buses", ["zone"]),
        ("OWNER", 3, "buses", ["owner"]),
        ("NVHI", 3, "buses", ["v_mag_pu_max"]),
        ("NVLO", 3, "buses", ["v_mag_pu_min"]),
        ("EVHI", 3, "buses", ["v_mag_pu_max_emerg"]),
        ("EVLO", 3, "buses", ["v_mag_pu_min_emerg"]),
    ],
    "load": [
        # DCPF-critical (Tier 1)
        ("I", 1, "loads", ["bus"]),
        ("ID", 1, "loads", ["load_id", "id"]),  # PPC aggregates: no explicit ID
        ("STATUS", 1, "loads", ["active", "status"]),
        ("PL", 1, "loads", ["p_set"]),
        # ACPF-critical (Tier 2)
        ("QL", 2, "loads", ["q_set"]),
        ("IP", 2, "loads", ["ip"]),
        ("IQ", 2, "loads", ["iq"]),
        ("YP", 2, "loads", ["yp"]),
        ("YQ", 2, "loads", ["yq"]),
        # Informational (Tier 3)
        ("AREA", 3, "loads", ["area"]),
        ("ZONE", 3, "loads", ["zone"]),
        ("OWNER", 3, "loads", ["owner"]),
        ("SCALE", 3, "loads", ["scale"]),
    ],
    "generator": [
        # DCPF-critical (Tier 1)
        ("I", 1, "generators", ["bus"]),
        ("ID", 1, "generators", ["gen_id", "id"]),  # PPC uses row index
        ("PG", 1, "generators", ["p_set"]),
        ("STAT", 1, "generators", ["active", "status"]),
        # ACPF-critical (Tier 2)
        ("QG", 2, "generators", ["q_set"]),
        ("QT", 2, "generators", ["q_max", "q_max_pu", "Qc1max"]),
        ("QB", 2, "generators", ["q_min", "q_min_pu", "Qc1min"]),
        ("VS", 2, "generators", ["v_set_pu"]),
        ("IREG", 2, "generators", ["ireg", "control_bus"]),
        # Informational (Tier 3)
        ("MBASE", 3, "generators", ["mva_base"]),
        ("ZR", 3, "generators", ["zr"]),
        ("ZX", 3, "generators", ["zx"]),
        ("RT", 3, "generators", ["rt"]),
        ("XT", 3, "generators", ["xt"]),
        ("GTAP", 3, "generators", ["gtap"]),
        ("RMPCT", 3, "generators", ["rmpct"]),
        ("PT", 3, "generators", ["p_nom"]),
        ("PB", 3, "generators", ["p_min_pu", "p_min"]),
        ("O1", 3, "generators", ["o1", "owner"]),
        ("F1", 3, "generators", ["f1"]),
        ("WMOD", 3, "generators", ["wmod"]),
        ("WPF", 3, "generators", ["wpf"]),
    ],
    "branch": [
        # DCPF-critical (Tier 1)
        ("I", 1, "lines", ["bus0"]),
        ("J", 1, "lines", ["bus1"]),
        ("CKT", 1, "lines", ["ckt", "circuit", "id"]),  # PPC uses row index
        ("X", 1, "lines", ["x"]),
        ("ST", 1, "lines", ["active", "status"]),
        # ACPF-critical (Tier 2)
        ("R", 2, "lines", ["r"]),
        ("B", 2, "lines", ["b"]),
        ("GI", 2, "lines", ["gi"]),
        ("BI", 2, "lines", ["bi"]),
        ("GJ", 2, "lines", ["gj"]),
        ("BJ", 2, "lines", ["bj"]),
        # Informational (Tier 3)
        ("RATEA", 3, "lines", ["s_nom"]),
        ("RATEB", 3, "lines", ["rateB", "rate_b"]),
        ("RATEC", 3, "lines", ["rateC", "rate_c"]),
        ("MET", 3, "lines", ["met", "metered_end"]),
        ("LEN", 3, "lines", ["length", "len"]),
        ("O1", 3, "lines", ["o1", "owner"]),
        ("F1", 3, "lines", ["f1"]),
    ],
    "transformer": [
        # DCPF-critical (Tier 1) — mapped from 83-field intermediate format
        # PPC merges transformer fields into branch array; PyPSA splits by tap_ratio
        ("I", 1, "transformers", ["bus0"]),  # intermediate I
        ("J", 1, "transformers", ["bus1"]),  # intermediate J
        ("K", 1, "transformers", ["bus2"]),  # 3-winding bus; not in PPC
        ("CKT", 1, "transformers", ["ckt", "circuit", "id"]),
        ("STAT", 1, "transformers", ["active", "status"]),
        ("X1_2", 1, "transformers", ["x"]),  # PPC branch X col
        ("WINDV1", 1, "transformers", ["tap_ratio"]),  # PPC TAP col
        ("ANG1", 1, "transformers", ["phase_shift"]),  # PPC SHIFT col
        ("X2_3", 1, "transformers", ["x2_3"]),  # 3W only
        ("X3_1", 1, "transformers", ["x3_1"]),  # 3W only
        # ACPF-critical (Tier 2)
        ("CW", 2, "transformers", ["cw"]),
        ("CZ", 2, "transformers", ["cz"]),
        ("CM", 2, "transformers", ["cm"]),
        ("MAG1", 2, "transformers", ["mag1"]),
        ("MAG2", 2, "transformers", ["mag2"]),
        ("R1_2", 2, "transformers", ["r"]),  # PPC branch R col
        ("SBASE1_2", 2, "transformers", ["sbase1_2"]),
        ("RATA1", 2, "transformers", ["s_nom"]),
        ("WINDV2", 2, "transformers", ["windv2"]),
        ("NOMV1", 2, "transformers", ["nomv1"]),
        ("NOMV2", 2, "transformers", ["nomv2"]),
        ("COD1", 2, "transformers", ["cod1"]),
        ("CONT1", 2, "transformers", ["cont1"]),
        ("NTP1", 2, "transformers", ["ntp1"]),
        # Informational (Tier 3)
        ("NAME", 3, "transformers", ["name"]),
        ("NMETR", 3, "transformers", ["nmetr"]),
        ("RATB1", 3, "transformers", ["rateB", "rate_b"]),
        ("RATC1", 3, "transformers", ["rateC", "rate_c"]),
        ("O1", 3, "transformers", ["o1", "owner"]),
        ("F1", 3, "transformers", ["f1"]),
        ("VECGRP", 3, "transformers", ["vecgrp"]),
    ],
    "fixed_shunt": [
        # ACPF-critical (Tier 2) — all fixed shunt fields
        # PPC carries Gs/Bs on bus rows -> n.buses.Gs/Bs columns
        ("I", 2, "buses", ["__index__"]),  # bus number from Gs/Bs on bus
        ("GL", 2, "buses", ["Gs"]),
        ("BL", 2, "buses", ["Bs"]),
        ("ID", 2, "buses", ["shunt_id"]),  # aggregated per bus; no explicit ID
        ("STATUS", 2, "buses", ["shunt_status"]),  # not separately tracked
    ],
    "switched_shunt": [
        # ACPF-critical (Tier 2)
        # PPC carries bus Bs column but loses switched shunt discrete steps
        ("I", 2, "shunt_impedances", ["bus"]),
        ("BINIT", 2, "shunt_impedances", ["b"]),
        ("STAT", 2, "shunt_impedances", ["active", "sign"]),
        ("MODSW", 2, "shunt_impedances", ["modsw"]),
        ("VSWHI", 2, "shunt_impedances", ["vswhi"]),
        ("VSWLO", 2, "shunt_impedances", ["vswlo"]),
        ("SWREM", 2, "shunt_impedances", ["swrem"]),
        ("N1", 2, "shunt_impedances", ["n1"]),
        ("B1", 2, "shunt_impedances", ["b1"]),
    ],
    "area": [
        # ACPF-critical (Tier 2)
        ("ISW", 2, "buses", ["area_slack"]),  # no area table in PyPSA via PPC
        ("PDES", 2, "buses", ["area_pdes"]),
        ("PTOL", 2, "buses", ["area_ptol"]),
        # Informational (Tier 3)
        ("I", 3, "buses", ["area"]),
        ("ARNAME", 3, "buses", ["area_name"]),
    ],
}


def _check_attribute(net, component_name, candidate_attrs):
    """Check if a PyPSA component has any of the candidate attributes."""
    component_df = getattr(net, component_name, None)
    if component_df is None or len(component_df) == 0:
        return False, "component empty or missing"

    for attr in candidate_attrs:
        if attr == "__index__":
            return True, "present (index)"
        if attr in component_df.columns:
            return True, f"present ({attr})"

    return False, f"missing (tried: {', '.join(candidate_attrs)})"


def run() -> dict:
    """Execute G-FNM-2 field coverage audit."""
    import pypsa

    workarounds = []
    errors = []

    try:
        # Load network (same as G-FNM-1)
        import scipy.io

        t0 = time.perf_counter()

        mat = scipy.io.loadmat(str(MAT_PATH))
        mpc_struct = mat["mpc"][0, 0]
        baseMVA = float(mpc_struct["baseMVA"].flat[0])
        bus_array = mpc_struct["bus"]
        gen_array = mpc_struct["gen"]
        branch_array = mpc_struct["branch"]

        # Filter type-4 buses
        bus_types = bus_array[:, 1].astype(int)
        type4_mask = bus_types == 4
        type4_bus_numbers = set(bus_array[type4_mask, 0].astype(int).tolist())

        bus_filtered = bus_array[~type4_mask]
        gen_mask = np.array([int(b) not in type4_bus_numbers for b in gen_array[:, 0].astype(int)])
        gen_filtered = gen_array[gen_mask]
        branch_from = branch_array[:, 0].astype(int)
        branch_to = branch_array[:, 1].astype(int)
        branch_mask = np.array(
            [
                int(f) not in type4_bus_numbers and int(t) not in type4_bus_numbers
                for f, t in zip(branch_from, branch_to)
            ]
        )
        branch_filtered = branch_array[branch_mask]

        ppc = {
            "version": "2",
            "baseMVA": baseMVA,
            "bus": bus_filtered,
            "gen": gen_filtered,
            "branch": branch_filtered,
        }

        net = pypsa.Network()
        net.import_from_pypower_ppc(ppc)

        # Now audit field coverage
        coverage_results = {}
        tier_summary = {
            "dcpf_critical": {"total": 0, "present": 0, "missing": []},
            "acpf_critical": {"total": 0, "present": 0, "missing": []},
            "informational": {"total": 0, "present": 0, "missing": []},
        }

        tier_labels = {1: "dcpf_critical", 2: "acpf_critical", 3: "informational"}

        for table_name, fields in FIELD_COVERAGE.items():
            table_results = []
            for field_name, tier, component, candidates in fields:
                present, note = _check_attribute(net, component, candidates)

                tier_key = tier_labels[tier]
                tier_summary[tier_key]["total"] += 1
                if present:
                    tier_summary[tier_key]["present"] += 1
                else:
                    tier_summary[tier_key]["missing"].append(
                        f"{table_name}.{field_name} -> {component}.{candidates}"
                    )

                table_results.append(
                    {
                        "field": field_name,
                        "tier": tier,
                        "tier_label": tier_key,
                        "pypsa_component": component,
                        "candidates_checked": candidates,
                        "present": present,
                        "note": note,
                    }
                )

            coverage_results[table_name] = table_results

        # Compute coverage percentages
        for tier_key in tier_summary:
            total = tier_summary[tier_key]["total"]
            present = tier_summary[tier_key]["present"]
            tier_summary[tier_key]["coverage_pct"] = (
                round(100.0 * present / total, 1) if total > 0 else 0.0
            )

        t_total = time.perf_counter() - t0

        # DCPF-critical must be 100%
        dcpf_coverage = tier_summary["dcpf_critical"]["coverage_pct"]
        passed = dcpf_coverage == 100.0

        # Also list actual columns per component
        component_columns = {}
        for comp_name in [
            "buses",
            "generators",
            "lines",
            "transformers",
            "loads",
            "shunt_impedances",
        ]:
            comp_df = getattr(net, comp_name, None)
            if comp_df is not None and len(comp_df) > 0:
                component_columns[comp_name] = sorted(comp_df.columns.tolist())

        return {
            "status": "pass" if passed else "fail",
            "wall_clock_seconds": round(t_total, 3),
            "details": {
                "tool_version": pypsa.__version__,
                "tier_summary": tier_summary,
                "coverage_by_table": coverage_results,
                "component_columns": component_columns,
            },
            "errors": errors,
            "workarounds": workarounds,
        }

    except Exception as e:
        errors.append({"error": str(e), "traceback": traceback.format_exc()})
        return {
            "status": "error",
            "wall_clock_seconds": 0.0,
            "details": {},
            "errors": errors,
            "workarounds": workarounds,
        }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
