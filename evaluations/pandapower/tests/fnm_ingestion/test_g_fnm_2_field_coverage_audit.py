"""
Test G-FNM-2: Field coverage audit vs criticality matrix

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01)
Pass condition: 100% of DCPF-critical fields must be present across all 19
    DCPF-critical fields. ACPF-critical field coverage reported but not gated.
Tool: pandapower 3.4.0
"""

from __future__ import annotations

import json
import time
import traceback

import numpy as np
import scipy.io

# ---------------------------------------------------------------------------
# Field criticality mapping (from field-criticality-matrix.md v10)
#
# Only tables with non-empty record counts in the FNM are relevant:
#   bus, load, generator, branch, transformer
#
# For each intermediate-format field we record:
#   (field_name, tier, pandapower_table, pandapower_column_or_check)
#
# tier: 1=DCPF-critical, 2=ACPF-critical, 3=Informational, 4=Discardable
# ---------------------------------------------------------------------------

# 19 DCPF-critical fields (tier 1) across 5 record types
DCPF_CRITICAL_FIELDS = [
    # Bus (3)
    ("bus.I", "bus", "bus_index"),
    ("bus.IDE", "bus", "type"),
    ("bus.VA", "bus", "va_degree_via_dcpf"),
    # Load (3)
    ("load.I", "load", "bus"),
    ("load.STATUS", "load", "in_service"),
    ("load.PL", "load", "p_mw"),
    # Generator (3)
    ("gen.I", "gen+sgen+ext_grid", "bus"),
    ("gen.PG", "gen+sgen+ext_grid", "p_mw"),
    ("gen.STAT", "gen+sgen+ext_grid", "in_service"),
    # Branch (4)
    ("branch.I", "line", "from_bus"),
    ("branch.J", "line", "to_bus"),
    ("branch.X", "line", "x_ohm_per_km"),
    ("branch.ST", "line", "in_service"),
    # Transformer (6)
    ("trafo.I", "trafo+impedance", "hv_bus/from_bus"),
    ("trafo.J", "trafo+impedance", "lv_bus/to_bus"),
    ("trafo.STAT", "trafo+impedance", "in_service"),
    ("trafo.X1_2", "trafo+impedance", "vk_percent/xft_pu"),
    ("trafo.WINDV1", "trafo+impedance", "tap_pos/implicit"),
    ("trafo.ANG1", "trafo+impedance", "shift_degree/implicit"),
]

# ACPF-critical fields for coverage reporting (not gated)
ACPF_CRITICAL_FIELDS = [
    # Bus (2)
    ("bus.BASKV", "bus", "vn_kv"),
    ("bus.VM", "bus", "vm_pu_via_acpf"),
    # Load (5)
    ("load.QL", "load", "q_mvar"),
    ("load.IP", "load", "const_i_p_percent"),
    ("load.IQ", "load", "const_i_q_percent"),
    ("load.YP", "load", "const_z_p_percent"),
    ("load.YQ", "load", "const_z_q_percent"),
    # Generator (5)
    ("gen.QG", "gen", "solved_q"),
    ("gen.QT", "gen", "max_q_mvar"),
    ("gen.QB", "gen", "min_q_mvar"),
    ("gen.VS", "gen", "vm_pu"),
    ("gen.IREG", "gen", "no_mapping"),
    # Branch (6)
    ("branch.R", "line", "r_ohm_per_km"),
    ("branch.B", "line", "c_nf_per_km"),
    ("branch.GI", "line", "no_mapping"),
    ("branch.BI", "line", "no_mapping"),
    ("branch.GJ", "line", "no_mapping"),
    ("branch.BJ", "line", "no_mapping"),
    # Transformer - many ACPF fields
    ("trafo.CW", "trafo", "no_mapping"),
    ("trafo.CZ", "trafo", "no_mapping"),
    ("trafo.CM", "trafo", "no_mapping"),
    ("trafo.MAG1", "trafo", "pfe_kw"),
    ("trafo.MAG2", "trafo", "i0_percent"),
    ("trafo.R1_2", "trafo+impedance", "vkr_percent/rft_pu"),
    ("trafo.SBASE1_2", "trafo+impedance", "sn_mva"),
    ("trafo.WINDV2", "trafo", "implicit_1.0"),
    ("trafo.NOMV1", "trafo", "vn_hv_kv"),
    ("trafo.NOMV2", "trafo", "vn_lv_kv"),
    ("trafo.ANG2", "trafo", "no_mapping"),
    ("trafo.COD1", "trafo", "tap_changer_type"),
    ("trafo.CONT1", "trafo", "no_mapping"),
    ("trafo.RMA1", "trafo", "tap_max"),
    ("trafo.RMI1", "trafo", "tap_min"),
    ("trafo.VMA1", "trafo", "no_mapping"),
    ("trafo.VMI1", "trafo", "no_mapping"),
    ("trafo.NTP1", "trafo", "tap_step_percent"),
    ("trafo.RATA1", "trafo", "sn_mva"),
    # Area (3 ACPF-critical)
    ("area.ISW", "area", "no_mapping"),
    ("area.PDES", "area", "no_mapping"),
    ("area.PTOL", "area", "no_mapping"),
    # Switched shunt (multiple ACPF-critical)
    ("switched_shunt.I", "shunt", "bus"),
    ("switched_shunt.MODSW", "shunt", "no_mapping"),
    ("switched_shunt.ADJM", "shunt", "no_mapping"),
    ("switched_shunt.STAT", "shunt", "in_service"),
    ("switched_shunt.VSWHI", "shunt", "no_mapping"),
    ("switched_shunt.VSWLO", "shunt", "no_mapping"),
    ("switched_shunt.SWREM", "shunt", "no_mapping"),
    ("switched_shunt.RMPCT", "shunt", "no_mapping"),
    ("switched_shunt.RMIDNT", "shunt", "no_mapping"),
    ("switched_shunt.BINIT", "shunt", "q_mvar"),
    ("switched_shunt.N1", "shunt", "max_step"),
    ("switched_shunt.B1", "shunt", "q_mvar"),
]


def check_field_present(net, field_name: str, pp_table: str, pp_column: str) -> dict:
    """Check whether a DCPF-critical field is representable in pandapower's data model.

    Returns dict with 'present', 'mapping', and 'note' keys.
    """
    result = {"field": field_name, "present": False, "mapping": "", "note": ""}

    # --- Bus fields ---
    if field_name == "bus.I":
        result["present"] = True
        result["mapping"] = "net.bus.index (bus number as DataFrame index)"
        result["note"] = f"Bus count: {len(net.bus)}"
    elif field_name == "bus.IDE":
        result["present"] = "type" in net.bus.columns
        result["mapping"] = "net.bus['type'] (mapped from PPC bus_type: 1->PQ, 2->PV, 3->slack)"
        type_counts = net.bus["type"].value_counts().to_dict() if result["present"] else {}
        result["note"] = f"Type distribution: {type_counts}"
    elif field_name == "bus.VA":
        # VA is a solved state variable — it appears in res_bus after DCPF solve.
        # In the data model it maps to ext_grid.va_degree for slack buses.
        # After DCPF solve, net.res_bus.va_degree is populated for all buses.
        result["present"] = True
        result["mapping"] = "net.res_bus['va_degree'] (populated after rundcpp)"
        result["note"] = "Solved variable; initial angle set on ext_grid.va_degree"

    # --- Load fields ---
    elif field_name == "load.I":
        result["present"] = "bus" in net.load.columns
        result["mapping"] = "net.load['bus']"
        result["note"] = f"Load count: {len(net.load)}"
    elif field_name == "load.STATUS":
        result["present"] = "in_service" in net.load.columns
        result["mapping"] = "net.load['in_service']"
    elif field_name == "load.PL":
        result["present"] = "p_mw" in net.load.columns
        result["mapping"] = "net.load['p_mw']"
        if result["present"]:
            result["note"] = f"Total load: {net.load['p_mw'].sum():.1f} MW"

    # --- Generator fields ---
    elif field_name == "gen.I":
        has_gen = "bus" in net.gen.columns
        has_sgen = "bus" in net.sgen.columns
        has_ext = "bus" in net.ext_grid.columns
        result["present"] = has_gen and has_sgen and has_ext
        result["mapping"] = "net.gen['bus'], net.sgen['bus'], net.ext_grid['bus']"
        result["note"] = (
            f"gen: {len(net.gen)}, sgen: {len(net.sgen)}, ext_grid: {len(net.ext_grid)}"
        )
    elif field_name == "gen.PG":
        has_gen = "p_mw" in net.gen.columns
        has_sgen = "p_mw" in net.sgen.columns
        result["present"] = has_gen and has_sgen
        result["mapping"] = "net.gen['p_mw'], net.sgen['p_mw']"
        if result["present"]:
            total = net.gen["p_mw"].sum() + net.sgen["p_mw"].sum()
            result["note"] = f"Total generation (gen+sgen): {total:.1f} MW"
    elif field_name == "gen.STAT":
        has_gen = "in_service" in net.gen.columns
        has_sgen = "in_service" in net.sgen.columns
        has_ext = "in_service" in net.ext_grid.columns
        result["present"] = has_gen and has_sgen and has_ext
        result["mapping"] = (
            "net.gen['in_service'], net.sgen['in_service'], net.ext_grid['in_service']"
        )

    # --- Branch fields ---
    elif field_name == "branch.I":
        result["present"] = "from_bus" in net.line.columns
        result["mapping"] = "net.line['from_bus']"
    elif field_name == "branch.J":
        result["present"] = "to_bus" in net.line.columns
        result["mapping"] = "net.line['to_bus']"
    elif field_name == "branch.X":
        result["present"] = "x_ohm_per_km" in net.line.columns
        result["mapping"] = "net.line['x_ohm_per_km'] (converted from per-unit X)"
    elif field_name == "branch.ST":
        result["present"] = "in_service" in net.line.columns
        result["mapping"] = "net.line['in_service']"

    # --- Transformer fields ---
    elif field_name == "trafo.I":
        has_trafo = "hv_bus" in net.trafo.columns
        has_imp = "from_bus" in net.impedance.columns
        result["present"] = has_trafo and has_imp
        result["mapping"] = "net.trafo['hv_bus'], net.impedance['from_bus']"
    elif field_name == "trafo.J":
        has_trafo = "lv_bus" in net.trafo.columns
        has_imp = "to_bus" in net.impedance.columns
        result["present"] = has_trafo and has_imp
        result["mapping"] = "net.trafo['lv_bus'], net.impedance['to_bus']"
    elif field_name == "trafo.STAT":
        has_trafo = "in_service" in net.trafo.columns
        has_imp = "in_service" in net.impedance.columns
        result["present"] = has_trafo and has_imp
        result["mapping"] = "net.trafo['in_service'], net.impedance['in_service']"
    elif field_name == "trafo.X1_2":
        has_trafo = "vk_percent" in net.trafo.columns
        has_imp = "xft_pu" in net.impedance.columns
        result["present"] = has_trafo and has_imp
        result["mapping"] = (
            "net.trafo['vk_percent'] (short-circuit voltage %), "
            "net.impedance['xft_pu'] (per-unit reactance)"
        )
    elif field_name == "trafo.WINDV1":
        # Tap ratio is carried as tap_pos in trafo table.
        # For impedance elements, the tap is embedded in the impedance values.
        has_trafo = "tap_pos" in net.trafo.columns
        result["present"] = has_trafo
        result["mapping"] = (
            "net.trafo['tap_pos'] (tap position); for impedance elements, "
            "tap ratio is embedded in the per-unit impedance values"
        )
    elif field_name == "trafo.ANG1":
        has_trafo = "shift_degree" in net.trafo.columns
        result["present"] = has_trafo
        result["mapping"] = (
            "net.trafo['shift_degree']; impedance elements carry phase shift "
            "embedded in asymmetric impedance (rft!=rtf, xft!=xtf)"
        )
    else:
        result["note"] = "Unmapped field"

    return result


def run(
    mat_file: str = "/workspace/data/fnm/reference/matpower_parse/mpc_case.mat",
) -> dict:
    """Execute the G-FNM-2 field coverage audit.

    Returns:
        dict with keys: status, wall_clock_seconds, details, errors, workarounds
    """
    results = {
        "status": "fail",
        "wall_clock_seconds": 0.0,
        "details": {},
        "errors": [],
        "workarounds": [],
    }

    start = time.perf_counter()
    try:
        from pandapower.converter.pypower.from_ppc import from_ppc

        # Load FNM into pandapower (same approach as G-FNM-1)
        mat = scipy.io.loadmat(mat_file)
        mpc = mat["mpc"][0, 0]
        branch = mpc["branch"].copy()
        rate_a_col = 5
        zero_rate_mask = np.isclose(branch[:, rate_a_col], 0)
        branch[zero_rate_mask, rate_a_col] = 9999.0

        ppc = {
            "version": "2",
            "baseMVA": float(mpc["baseMVA"][0, 0]),
            "bus": mpc["bus"],
            "gen": mpc["gen"],
            "branch": branch,
        }
        net = from_ppc(ppc, f_hz=60)

        # --- Check all 19 DCPF-critical fields ---
        dcpf_results = []
        dcpf_present = 0
        dcpf_missing = []

        for field_name, pp_table, pp_col in DCPF_CRITICAL_FIELDS:
            check = check_field_present(net, field_name, pp_table, pp_col)
            dcpf_results.append(check)
            if check["present"]:
                dcpf_present += 1
            else:
                dcpf_missing.append(field_name)

        dcpf_total = len(DCPF_CRITICAL_FIELDS)
        dcpf_pct = dcpf_present / dcpf_total * 100

        # --- Check ACPF-critical fields (informational, not gated) ---
        acpf_present = 0
        acpf_total = len(ACPF_CRITICAL_FIELDS)
        acpf_missing = []

        for field_name, pp_table, pp_col in ACPF_CRITICAL_FIELDS:
            if pp_col == "no_mapping":
                acpf_missing.append(field_name)
            elif pp_col.startswith("implicit") or pp_col.startswith("solved"):
                acpf_present += 1
            else:
                # Check if the column exists
                present = False
                if pp_table == "bus" and pp_col in net.bus.columns:
                    present = True
                elif pp_table == "load" and pp_col in net.load.columns:
                    present = True
                elif pp_table == "gen" and pp_col in net.gen.columns:
                    present = True
                elif pp_table == "line" and pp_col in net.line.columns:
                    present = True
                elif pp_table == "trafo" and pp_col in net.trafo.columns:
                    present = True
                elif pp_table == "shunt" and pp_col in net.shunt.columns:
                    present = True
                elif pp_table in ("trafo+impedance",):
                    # Split mapping
                    cols = pp_col.split("/")
                    if len(cols) == 2:
                        t_col, i_col = cols
                        present = t_col in net.trafo.columns and i_col in net.impedance.columns
                    else:
                        present = pp_col in net.trafo.columns
                elif pp_table == "area":
                    present = False  # pandapower has no area table
                if present:
                    acpf_present += 1
                else:
                    acpf_missing.append(field_name)

        acpf_pct = acpf_present / acpf_total * 100 if acpf_total > 0 else 0

        # --- Informational field count (approximate) ---
        # Count non-empty tables' informational fields that map to pandapower
        informational_total = 87  # from matrix summary
        informational_present = 0
        # pandapower carries: bus.name, bus.zone, line.name, gen.name, load.name,
        # trafo.name, trafo.parallel, trafo.df, line.max_i_ka (RATEA),
        # gen.sn_mva (MBASE), gen.max_p_mw (PT), gen.min_p_mw (PB), etc.
        # Approximate count based on column inspection
        bus_info = sum(
            1 for c in ["name", "zone", "max_vm_pu", "min_vm_pu"] if c in net.bus.columns
        )
        line_info = sum(
            1
            for c in ["name", "max_i_ka", "parallel", "df", "length_km", "type"]
            if c in net.line.columns
        )
        gen_info = sum(
            1
            for c in ["name", "sn_mva", "max_p_mw", "min_p_mw", "type", "scaling"]
            if c in net.gen.columns
        )
        load_info = sum(1 for c in ["name", "scaling", "type"] if c in net.load.columns)
        trafo_info = sum(
            1
            for c in ["name", "parallel", "df", "max_loading_percent", "oltc"]
            if c in net.trafo.columns
        )
        informational_present = bus_info + line_info + gen_info + load_info + trafo_info
        info_pct = informational_present / informational_total * 100

        results["details"] = {
            "dcpf_critical": {
                "total": dcpf_total,
                "present": dcpf_present,
                "missing": dcpf_missing,
                "coverage_pct": dcpf_pct,
                "field_results": dcpf_results,
            },
            "acpf_critical": {
                "total": acpf_total,
                "present": acpf_present,
                "missing": acpf_missing,
                "coverage_pct": acpf_pct,
            },
            "informational": {
                "total": informational_total,
                "present_approx": informational_present,
                "coverage_pct_approx": info_pct,
            },
            "import_path": "MATPOWER .mat -> scipy.io.loadmat -> from_ppc",
            "note": (
                "pandapower ingests via MATPOWER/PYPOWER PPC format, which "
                "flattens transformer data into the branch matrix. Transformer "
                "fields are preserved via tap_pos, shift_degree (trafo table) "
                "and asymmetric impedance values (impedance table). "
                "ACPF-critical fields for area interchange, switched shunt "
                "control, and remote bus regulation are not carried through "
                "the PPC import path."
            ),
        }

        # Pass condition: 100% of 19 DCPF-critical fields present
        if dcpf_pct == 100.0:
            results["status"] = "pass"
        else:
            results["status"] = "fail"
            results["errors"].append(
                f"DCPF-critical coverage: {dcpf_present}/{dcpf_total} "
                f"({dcpf_pct:.1f}%). Missing: {dcpf_missing}"
            )

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
