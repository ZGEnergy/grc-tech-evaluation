"""
Test G-FNM-5: Supplemental CSV Representability

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01)
Pass condition: No hard pass/fail. Evidence collection. For each CSV: total
  fields, N/E/X classification. Compare against analytical classifications
  from supplemental-csv-representability.md.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

FNM_PATH = Path("/data/fnm-source")
PREFIX = "AUC_AN_2026_2026_S01_"

# Empirical field classification for each supplemental CSV
# Based on actual CSV column names (from FNM data) and PyPSA data model
# Tier: N (native), E (extension-representable), X (tool-external)
CLASSIFICATIONS: dict[str, dict[str, tuple[str, str]]] = {
    "LINE_AND_TRANSFORMER": {
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
        "Trading Hub": ("X", "no hub model in PyPSA"),
        "APNode": (
            "X",
            "no hub/settlement node model — actual field is APNode string, not bus number",
        ),
        "Allocation Factor": ("X", "no hub allocation model"),
        "TOU": ("E", "custom column"),
    },
    "GEN_DISTRIBUTION_FACTOR": {
        "Generator Name": ("N", "Generator name (index)"),
        "EMS Name": ("E", "custom column"),
        "Distribution Factor": ("X", "no generator distribution factor attribute"),
        "TOU": ("E", "custom column"),
    },
    "CONTINGENCY": {
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
        # Combined INTERFACE + INTERFACE_ELEMENT data in single CSV
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
        "OMS Outage ID": ("X", "no outage schedule model in PyPSA"),
        "Duration In Hour": ("X", "no outage schedule model"),
        "Action": ("X", "no outage schedule model"),
        "Device Type": ("X", "no outage schedule model"),
        "Device Name": ("X", "no outage schedule model"),
        "Device EMS Name": ("X", "no outage schedule model"),
        "From Bus ID": ("N", "Line.bus0 (if bus number)"),
        "To Bus ID": ("N", "Line.bus1 (if bus number)"),
        "Adjusted Base Limit": ("X", "no outage schedule model"),
        " Adjusted Emergency Limit": (
            "X",
            "no outage schedule model — note leading space in column name",
        ),
        "TOU": ("E", "custom column"),
    },
    "RESOURCE": {
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

# Analytical tier from supplemental-csv-representability.md for cross-reference
# Maps actual CSV column names to analytical classification where directly comparable
ANALYTICAL_TIERS: dict[str, dict[str, str]] = {
    "LINE_AND_TRANSFORMER": {
        "From Bus Number": "N",  # FROM_BUS
        "To Bus Number": "N",  # TO_BUS
        "Circuit ID": "E",  # CKT
        "Normal Rating": "N",  # RATE_A
        "Emergency Rating": "E",  # RATE_B (only 1 native tier)
        "Status": "N",  # STATUS
    },
    "TRADING_HUB": {
        "Trading Hub": "X",  # HUB_NAME
        "APNode": "N",  # BUS_NUMBER — analytical assumes integer bus ID
        "Allocation Factor": "X",  # DISTRIBUTION_FACTOR
    },
    "GEN_DISTRIBUTION_FACTOR": {
        "Generator Name": "N",  # GEN_NAME
        "Distribution Factor": "X",  # PARTICIPATION_FACTOR
    },
    "CONTINGENCY": {
        "Contingency Name": "X",  # CONTINGENCY_NAME
    },
    "INTERFACE": {
        "Interface Name": "X",  # INTERFACE_NAME
        "Positive Limit": "X",  # NORMAL_LIMIT_MW
        "Negative Limit": "X",  # negative direction
    },
    "OUTAGE": {
        "From Bus ID": "N",  # ELEMENT_FROM_BUS
        "To Bus ID": "N",  # ELEMENT_TO_BUS
    },
}


def run() -> dict:
    """Execute G-FNM-5 supplemental CSV representability test.

    Returns:
        dict with keys:
        - status: "informational" (evidence collection, no hard pass/fail)
        - wall_clock_seconds: float
        - details: per-CSV classification results
        - errors: list of error messages
        - workarounds: list of workaround descriptions
    """
    import pandas as pd
    import pypsa

    workarounds: list[str] = []
    errors: list[str] = []

    try:
        t0 = time.perf_counter()

        # Discover available CSVs
        csv_files: dict[str, Path] = {}
        if FNM_PATH.exists():
            for p in sorted(FNM_PATH.iterdir()):
                if p.suffix == ".csv" and p.name.startswith(PREFIX):
                    csv_key = p.name.replace(PREFIX, "").replace(".csv", "")
                    csv_files[csv_key] = p

        csv_results: dict[str, dict] = {}
        for csv_key, csv_path in sorted(csv_files.items()):
            try:
                df = pd.read_csv(csv_path, nrows=5)
                actual_columns = list(df.columns)
                # Count rows (subtract 1 for header)
                n_rows_approx = sum(1 for _ in open(csv_path)) - 1
            except Exception as e:
                csv_results[csv_key] = {"error": str(e)}
                continue

            classifications = CLASSIFICATIONS.get(csv_key, {})
            analytical = ANALYTICAL_TIERS.get(csv_key, {})

            field_results = []
            for col in actual_columns:
                col_clean = col.strip()

                if col in classifications:
                    tier, note = classifications[col]
                elif col_clean in classifications:
                    tier, note = classifications[col_clean]
                else:
                    # Default: Extension-representable via custom column
                    tier, note = "E", "custom column (unclassified field)"

                anal_tier = analytical.get(col) or analytical.get(col_clean)

                field_results.append(
                    {
                        "field": col,
                        "empirical_tier": tier,
                        "empirical_note": note,
                        "analytical_tier": anal_tier,
                        "match": (tier == anal_tier) if anal_tier is not None else None,
                    }
                )

            n_fields = len(field_results)
            n_n = sum(1 for f in field_results if f["empirical_tier"] == "N")
            n_e = sum(1 for f in field_results if f["empirical_tier"] == "E")
            n_x = sum(1 for f in field_results if f["empirical_tier"] == "X")
            n_match = sum(1 for f in field_results if f["match"] is True)
            n_mismatch = sum(1 for f in field_results if f["match"] is False)
            n_cross_ref = sum(1 for f in field_results if f["match"] is not None)

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
                "analytical_cross_reference": {
                    "fields_compared": n_cross_ref,
                    "matches": n_match,
                    "mismatches": n_mismatch,
                },
                "fields": field_results,
            }

        t_total = time.perf_counter() - t0

        # Cross-CSV summary
        total_n = sum(
            r.get("summary", {}).get("native", 0) for r in csv_results.values() if "summary" in r
        )
        total_e = sum(
            r.get("summary", {}).get("extension", 0) for r in csv_results.values() if "summary" in r
        )
        total_x = sum(
            r.get("summary", {}).get("external", 0) for r in csv_results.values() if "summary" in r
        )
        total_f = total_n + total_e + total_x

        total_matches = sum(
            r.get("analytical_cross_reference", {}).get("matches", 0)
            for r in csv_results.values()
            if "analytical_cross_reference" in r
        )
        total_mismatches = sum(
            r.get("analytical_cross_reference", {}).get("mismatches", 0)
            for r in csv_results.values()
            if "analytical_cross_reference" in r
        )

        # Verify extension mechanism empirically
        try:
            net = pypsa.Network()
            net.add("Bus", "test_bus", v_nom=230)
            net.add(
                "Line", "test_line", bus0="test_bus", bus1="test_bus", x=0.01, r=0.001, length=1
            )
            net.lines["custom_test_field"] = "test_value"
            ext_verified = net.lines.loc["test_line", "custom_test_field"] == "test_value"
        except Exception as e:
            ext_verified = False
            errors.append(f"Extension mechanism verification failed: {e}")

        return {
            "status": "informational",
            "wall_clock_seconds": round(t_total, 3),
            "details": {
                "tool_version": pypsa.__version__,
                "csvs_found": len(csv_files),
                "csvs_analyzed": sum(1 for r in csv_results.values() if "summary" in r),
                "extension_mechanism_verified": ext_verified,
                "cross_csv_summary": {
                    "total_fields": total_f,
                    "native": total_n,
                    "extension": total_e,
                    "external": total_x,
                    "native_pct": round(100 * total_n / total_f, 1) if total_f else 0,
                    "extension_pct": round(100 * total_e / total_f, 1) if total_f else 0,
                    "external_pct": round(100 * total_x / total_f, 1) if total_f else 0,
                    "analytical_matches": total_matches,
                    "analytical_mismatches": total_mismatches,
                },
                "per_csv": csv_results,
            },
            "errors": errors,
            "workarounds": workarounds,
        }

    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")
        errors.append(traceback.format_exc())
        return {
            "status": "error",
            "wall_clock_seconds": 0.0,
            "details": {},
            "errors": errors,
            "workarounds": workarounds,
        }


if __name__ == "__main__":
    import json as _json

    result = run()
    print(_json.dumps(result, indent=2, default=str))
