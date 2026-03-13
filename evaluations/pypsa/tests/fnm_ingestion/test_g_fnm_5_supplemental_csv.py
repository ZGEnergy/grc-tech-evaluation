"""G-FNM-5: Supplemental CSV Representability — LARGE FNM.

For each supplemental CSV at FNM_PATH, classify each field as:
  N (native) — PyPSA has a direct attribute
  E (extension) — can be stored via custom DataFrame column
  X (tool-external) — no representation path in PyPSA data model

Compare empirical classifications against analytical classifications from
supplemental-csvs.md. No hard pass/fail — evidence collection.

Tool: PyPSA
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

FNM_PATH = Path("/data/fnm-source")
PREFIX = "AUC_AN_2026_2026_S01_"

# Empirical field classification for each supplemental CSV
# Based on actual CSV column names (from FNM data) and PyPSA data model
CLASSIFICATIONS = {
    "LINE_AND_TRANSFORMER": {
        # Actual columns: Device Name, EMS Device Name, Device Type, From Bus Number,
        # From Bus Name, From Bus Substation, From Bus Zone, To Bus Number, To Bus Name,
        # To Bus Substation, To Bus Zone, Circuit ID, Status, Enforcement,
        # Normal Rating, Emergency Rating, Operating Normal Rating, Operating Emergency Rating, TOU
        "Device Name": ("E", "custom column on Lines/Transformers DataFrame"),
        "EMS Device Name": ("E", "custom column"),
        "Device Type": (
            "E",
            "custom column (LINE/TRANSFORMER distinguishable natively by component type)",
        ),
        "From Bus Number": ("N", "Line.bus0 / Transformer.bus0"),
        "From Bus Name": ("E", "custom column (bus names not imported via PPC)"),
        "From Bus Substation": ("E", "custom column"),
        "From Bus Zone": ("N", "Bus.zone (imported via PPC)"),
        "To Bus Number": ("N", "Line.bus1 / Transformer.bus1"),
        "To Bus Name": ("E", "custom column"),
        "To Bus Substation": ("E", "custom column"),
        "To Bus Zone": ("N", "Bus.zone (via bus1 lookup)"),
        "Circuit ID": ("E", "custom column (no native CKT field)"),
        "Status": ("N", "Line.active / Transformer.active"),
        "Enforcement": ("E", "custom column"),
        "Normal Rating": ("N", "Line.s_nom / Transformer.s_nom"),
        "Emergency Rating": ("E", "custom column (only 1 native rating tier: s_nom)"),
        "Operating Normal Rating": ("E", "custom column"),
        "Operating Emergency Rating": ("E", "custom column"),
        "TOU": ("E", "custom column (time-of-use period)"),
    },
    "TRADING_HUB": {
        # Actual columns: Trading Hub, APNode, Allocation Factor, TOU
        "Trading Hub": ("X", "no hub model in PyPSA"),
        "APNode": ("X", "no hub/settlement node model"),
        "Allocation Factor": ("X", "no hub allocation model"),
        "TOU": ("E", "custom column"),
    },
    "GEN_DISTRIBUTION_FACTOR": {
        # Actual columns: Generator Name, EMS Name, Distribution Factor, TOU
        "Generator Name": ("N", "Generator name (index)"),
        "EMS Name": ("E", "custom column"),
        "Distribution Factor": ("X", "no generator distribution factor attribute"),
        "TOU": ("E", "custom column"),
    },
    "CONTINGENCY": {
        # Actual columns: Contingency Name, Description, Device Name, EMS Device Name,
        # Device Type, Status, Action, Outage, TOU
        "Contingency Name": ("X", "no contingency model in PyPSA"),
        "Description": ("X", "no contingency model"),
        "Device Name": ("X", "no contingency model"),
        "EMS Device Name": ("X", "no contingency model"),
        "Device Type": ("X", "no contingency model"),
        "Status": ("X", "no contingency model"),
        "Action": ("X", "no contingency model"),
        "Outage": ("X", "no contingency model"),
        "TOU": ("E", "custom column"),
    },
    "INTERFACE": {
        # Actual columns: Interface Name, Positive Limit, Negative Limit,
        # Operating Positive Limit, Operating Negative Limit, Device Name,
        # EMS Device Name, Device Type, From Bus Name, From Bus Substation,
        # From Bus Zone, To Bus Name, To Bus Substation, To Bus Zone, Factor, Outage, TOU
        # Note: This CSV combines INTERFACE and INTERFACE_ELEMENT data
        "Interface Name": ("X", "no interface/flowgate model in PyPSA"),
        "Positive Limit": ("X", "no interface model"),
        "Negative Limit": ("X", "no interface model"),
        "Operating Positive Limit": ("X", "no interface model"),
        "Operating Negative Limit": ("X", "no interface model"),
        "Device Name": ("E", "custom column for element identification"),
        "EMS Device Name": ("E", "custom column"),
        "Device Type": ("E", "custom column"),
        "From Bus Name": ("E", "custom column (bus names not in PPC import)"),
        "From Bus Substation": ("E", "custom column"),
        "From Bus Zone": ("N", "Bus.zone"),
        "To Bus Name": ("E", "custom column"),
        "To Bus Substation": ("E", "custom column"),
        "To Bus Zone": ("N", "Bus.zone"),
        "Factor": ("X", "no interface direction coefficient model"),
        "Outage": ("X", "no interface contingency model"),
        "TOU": ("E", "custom column"),
    },
    "OUTAGE": {
        # Actual columns: OMS Outage ID, Duration In Hour, Action, Device Type,
        # Device Name, Device EMS Name, From Bus ID, To Bus ID,
        # Adjusted Base Limit, Adjusted Emergency Limit, TOU
        "OMS Outage ID": ("X", "no outage schedule model in PyPSA"),
        "Duration In Hour": ("X", "no outage schedule model"),
        "Action": ("X", "no outage schedule model"),
        "Device Type": ("X", "no outage schedule model"),
        "Device Name": ("X", "no outage schedule model"),
        "Device EMS Name": ("X", "no outage schedule model"),
        "From Bus ID": ("N", "Line.bus0 (if bus number)"),
        "To Bus ID": ("N", "Line.bus1 (if bus number)"),
        "Adjusted Base Limit": ("X", "no outage schedule model"),
        " Adjusted Emergency Limit": ("X", "no outage schedule model"),
        "TOU": ("E", "custom column"),
    },
    "RESOURCE": {
        # Actual columns: Generator Name, EMS Gen Name, Bus Name, EMS Bus Name,
        # Zone Name, Enforcement, Mw, TOU, PMax
        "Generator Name": ("N", "Generator name (index)"),
        "EMS Gen Name": ("E", "custom column"),
        "Bus Name": ("E", "custom column (bus names not in PPC import)"),
        "EMS Bus Name": ("E", "custom column"),
        "Zone Name": ("N", "Bus.zone (via generator bus)"),
        "Enforcement": ("E", "custom column"),
        "Mw": ("N", "Generator.p_set or Generator.p_nom"),
        "TOU": ("E", "custom column"),
        "PMax": ("N", "Generator.p_nom"),
    },
}

# Analytical tier from supplemental-csvs.md for cross-reference
# Only for the 7 documented CSVs, mapped to actual column names where possible
ANALYTICAL_TIERS = {
    "LINE_AND_TRANSFORMER": {
        "From Bus Number": "N",
        "To Bus Number": "N",
        "Circuit ID": "E",
        "Normal Rating": "N",
        "Emergency Rating": "E",
        "Status": "N",
    },
    "TRADING_HUB": {
        "Trading Hub": "X",
        "APNode": "N",  # BUS_NUMBER equivalent
        "Allocation Factor": "X",
    },
    "GEN_DISTRIBUTION_FACTOR": {
        "Generator Name": "N",
        "Distribution Factor": "X",
    },
    "CONTINGENCY": {
        "Contingency Name": "X",
    },
    "INTERFACE": {
        "Interface Name": "X",
        "Positive Limit": "X",
        "Negative Limit": "X",
    },
    "OUTAGE": {
        "From Bus ID": "N",
        "To Bus ID": "N",
    },
}


def run() -> dict:
    """Execute G-FNM-5 supplemental CSV representability test."""
    import pandas as pd
    import pypsa

    workarounds = []
    errors = []

    try:
        t0 = time.perf_counter()

        # Discover available CSVs
        csv_files = {}
        for p in sorted(FNM_PATH.iterdir()):
            if p.suffix == ".csv" and p.name.startswith(PREFIX):
                csv_key = p.name.replace(PREFIX, "").replace(".csv", "")
                csv_files[csv_key] = p

        csv_results = {}
        for csv_key, csv_path in sorted(csv_files.items()):
            try:
                df = pd.read_csv(csv_path, nrows=5)
                actual_columns = list(df.columns)
                n_rows_approx = sum(1 for _ in open(csv_path)) - 1
            except Exception as e:
                csv_results[csv_key] = {"error": str(e)}
                continue

            classifications = CLASSIFICATIONS.get(csv_key, {})
            analytical = ANALYTICAL_TIERS.get(csv_key, {})

            field_results = []
            for col in actual_columns:
                # Clean column name (some have leading spaces)
                col_clean = col.strip()

                if col in classifications:
                    tier, note = classifications[col]
                elif col_clean in classifications:
                    tier, note = classifications[col_clean]
                else:
                    tier, note = "E", "custom column (unclassified)"

                anal_tier = analytical.get(col) or analytical.get(col_clean)

                field_results.append(
                    {
                        "field": col,
                        "empirical_tier": tier,
                        "empirical_note": note,
                        "analytical_tier": anal_tier,
                        "match": (tier == anal_tier) if anal_tier else None,
                    }
                )

            n_fields = len(field_results)
            n_n = sum(1 for f in field_results if f["empirical_tier"] == "N")
            n_e = sum(1 for f in field_results if f["empirical_tier"] == "E")
            n_x = sum(1 for f in field_results if f["empirical_tier"] == "X")
            n_match = sum(1 for f in field_results if f["match"] is True)
            n_mismatch = sum(1 for f in field_results if f["match"] is False)

            csv_results[csv_key] = {
                "file": csv_path.name,
                "n_rows": n_rows_approx,
                "n_fields": n_fields,
                "summary": {
                    "native": n_n,
                    "extension": n_e,
                    "external": n_x,
                    "native_pct": round(100 * n_n / n_fields, 1) if n_fields else 0,
                    "extension_pct": round(100 * n_e / n_fields, 1) if n_fields else 0,
                    "external_pct": round(100 * n_x / n_fields, 1) if n_fields else 0,
                },
                "analytical_matches": n_match,
                "analytical_mismatches": n_mismatch,
                "fields": field_results,
            }

        t_total = time.perf_counter() - t0

        # Cross-CSV summary
        total_n = sum(r.get("summary", {}).get("native", 0) for r in csv_results.values())
        total_e = sum(r.get("summary", {}).get("extension", 0) for r in csv_results.values())
        total_x = sum(r.get("summary", {}).get("external", 0) for r in csv_results.values())
        total_f = total_n + total_e + total_x

        return {
            "status": "pass",  # Evidence collection, no hard pass/fail
            "wall_clock_seconds": round(t_total, 3),
            "details": {
                "tool_version": pypsa.__version__,
                "csvs_analyzed": len(csv_results),
                "cross_csv_summary": {
                    "total_fields": total_f,
                    "native": total_n,
                    "extension": total_e,
                    "external": total_x,
                    "native_pct": round(100 * total_n / total_f, 1) if total_f else 0,
                    "extension_pct": round(100 * total_e / total_f, 1) if total_f else 0,
                    "external_pct": round(100 * total_x / total_f, 1) if total_f else 0,
                },
                "per_csv": csv_results,
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
