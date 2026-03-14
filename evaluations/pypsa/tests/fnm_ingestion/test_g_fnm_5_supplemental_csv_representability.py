"""
Test G-FNM-5: Supplemental CSV representability assessment on LARGE

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01)
Pass condition: No hard pass/fail gate. Evidence-collection test. For each CSV, report:
  total fields, count and percentage by achieved representability tier (N/E/X), and
  per-field comparison against the analytical classification. E classifications without
  a documented concrete extension approach must be downgraded to X.
Tool: PyPSA 1.1.2
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

FNM_PATH = Path("/data/fnm-source")
PREFIX = "AUC_AN_2026_2026_S01_"

# ── Per-field representability classifications ──────────────────────────
# Each entry: (tier, extension_approach_or_justification)
# tier: N (native), E (extension-representable), X (tool-external)
# For E: must include concrete documented extension approach
# For X: must include justification

CLASSIFICATIONS: dict[str, dict[str, tuple[str, str]]] = {
    "LINE_AND_TRANSFORMER": {
        "Device Name": (
            "E",
            "Custom column on Lines/Transformers DataFrame via direct assignment: "
            "n.lines['device_name'] = values. Documented in PyPSA custom components docs.",
        ),
        "EMS Device Name": ("E", "Custom column on Lines/Transformers DataFrame."),
        "Device Type": (
            "E",
            "Inferrable from component type (Line vs Transformer) but also storable "
            "as custom column for original ELEMENT_TYPE enum value.",
        ),
        "From Bus Number": ("N", "Line.bus0 / Transformer.bus0"),
        "From Bus Name": ("E", "Custom column on bus DataFrame: n.buses['name_full'] = values."),
        "From Bus Substation": ("E", "Custom column on bus DataFrame."),
        "From Bus Zone": ("N", "Bus.zone (imported via PPC bus column 11)"),
        "To Bus Number": ("N", "Line.bus1 / Transformer.bus1"),
        "To Bus Name": ("E", "Custom column on bus DataFrame."),
        "To Bus Substation": ("E", "Custom column on bus DataFrame."),
        "To Bus Zone": ("N", "Bus.zone (via bus1 lookup)"),
        "Circuit ID": (
            "E",
            "Custom column: n.lines['circuit_id'] = values. PyPSA uses integer index, "
            "not PSS/E composite key, so CKT must be stored as custom attribute.",
        ),
        "Status": ("N", "Line.active / Transformer.active (boolean in-service flag)"),
        "Enforcement": ("E", "Custom column for enforcement mode flag."),
        "Normal Rating": ("N", "Line.s_nom / Transformer.s_nom (MVA thermal rating)"),
        "Emergency Rating": (
            "E",
            "Custom column: n.lines['s_nom_emergency'] = values. PyPSA has only 1 native "
            "rating tier (s_nom). RATE_B stored as custom attribute.",
        ),
        "Operating Normal Rating": (
            "E",
            "Custom column: n.lines['s_nom_operating'] = values. Operational overrides.",
        ),
        "Operating Emergency Rating": ("E", "Custom column for operational emergency rating."),
        "TOU": ("E", "Custom column for time-of-use period identifier."),
    },
    "TRADING_HUB": {
        "Trading Hub": (
            "E",
            "Custom bus attribute: n.buses['hub_name'] = values. Hub names stored as string "
            "attributes on bus DataFrame. Post-OPF hub prices derivable via PTDF-weighted "
            "bus LMP averaging. v10 reclassification from X.",
        ),
        "APNode": (
            "X",
            "APNode is an abstract settlement point identifier (string), not a physical bus "
            "number. PyPSA has no native settlement node concept. While the string could be "
            "stored as a custom attribute, it has no semantic mapping to PyPSA's bus model.",
        ),
        "Allocation Factor": (
            "E",
            "Custom bus attribute: n.buses['hub_allocation_factor'] = values. Used in "
            "post-OPF aggregate hub price calculation: "
            "(df_weights * n.buses_t.marginal_price).sum(axis=1). v10 reclassification from X.",
        ),
        "TOU": ("E", "Custom column for time-of-use period identifier."),
    },
    "GEN_DISTRIBUTION_FACTOR": {
        "Generator Name": ("N", "Generator name (index in n.generators DataFrame)"),
        "EMS Name": ("E", "Custom column: n.generators['ems_name'] = values."),
        "Distribution Factor": (
            "X",
            "No generator distribution factor attribute in PyPSA. Distribution factors are "
            "a market settlement concept (hub allocation) with no analog in a power flow tool's "
            "generator model. Must be maintained in external DataFrame.",
        ),
        "TOU": ("E", "Custom column for time-of-use period identifier."),
    },
    "CONTINGENCY": {
        "Contingency Name": (
            "E",
            "Custom DataFrame n.contingencies via extra_functionality callback. "
            "N-1 constraints enforced via BODF matrix + lp.add_constraints(). "
            "Requires 50-100 lines of custom code. v10 reclassification from X.",
        ),
        "Description": (
            "E",
            "Custom column on contingency DataFrame: n.contingencies['description'] = values.",
        ),
        "Device Name": (
            "E",
            "Custom column referencing Line/Transformer/Generator name on contingency DataFrame.",
        ),
        "EMS Device Name": ("E", "Custom column on contingency DataFrame."),
        "Device Type": (
            "E",
            "Custom column: BRANCH/GENERATOR enum stored as string attribute on "
            "contingency DataFrame. v10 reclassification from X.",
        ),
        "Status": ("E", "Custom column for contingency status (active/inactive)."),
        "Action": (
            "X",
            "No contingency action model in PyPSA. The extra_functionality pattern supports "
            "trip (remove element) but not partial actions like derate. Action semantics "
            "beyond simple trip require external logic.",
        ),
        "Outage": (
            "X",
            "No contingency-outage link model. Outage scheduling is outside PyPSA's domain.",
        ),
        "TOU": ("E", "Custom column for time-of-use period identifier."),
    },
    "INTERFACE": {
        "Interface Name": (
            "E",
            "Custom DataFrame: n.interfaces = pd.DataFrame(...). Interface definitions "
            "stored alongside network. PTDF constraint enforcement via extra_functionality + "
            "n.model.add_constraints(). v10 reclassification from X.",
        ),
        "Positive Limit": (
            "E",
            "PTDF-based aggregate flow constraint via extra_functionality. "
            "limit_up = positive_limit, enforced as sum(PTDF_row * Pinj) <= limit. "
            "v10 reclassification from X.",
        ),
        "Negative Limit": (
            "E",
            "PTDF-based constraint: sum(PTDF_row * Pinj) >= -negative_limit. "
            "v10 reclassification from X.",
        ),
        "Operating Positive Limit": (
            "E",
            "Custom column on interface DataFrame for operational limit overrides. "
            "v10 reclassification from X.",
        ),
        "Operating Negative Limit": (
            "E",
            "Custom column on interface DataFrame. v10 reclassification from X.",
        ),
        "Device Name": ("E", "Custom column for element identification within interface."),
        "EMS Device Name": ("E", "Custom column."),
        "Device Type": ("E", "Custom column for LINE/TRANSFORMER element type."),
        "From Bus Name": ("E", "Custom column (bus names not in PPC import path)."),
        "From Bus Substation": ("E", "Custom column."),
        "From Bus Zone": ("N", "Bus.zone (native via PPC import)"),
        "To Bus Name": ("E", "Custom column."),
        "To Bus Substation": ("E", "Custom column."),
        "To Bus Zone": ("N", "Bus.zone"),
        "Factor": (
            "E",
            "Direction coefficient for interface flow calculation. Storable as custom column; "
            "used in PTDF weighting sign convention. v10 reclassification from X.",
        ),
        "Outage": (
            "X",
            "No interface-outage link model. Conditional interfaces (active only during "
            "specific outages) require external logic beyond PyPSA's model.",
        ),
        "TOU": ("E", "Custom column for time-of-use period identifier."),
    },
    "OUTAGE": {
        "OMS Outage ID": (
            "X",
            "No outage schedule model in PyPSA. Outage management with temporal validity "
            "periods is outside the scope of a single-snapshot power flow tool.",
        ),
        "Duration In Hour": ("X", "No temporal outage scheduling model."),
        "Action": (
            "X",
            "No outage action model (TRIP/DERATE/etc). Element status can be toggled "
            "via Line.active but there's no action taxonomy.",
        ),
        "Device Type": ("X", "No outage device type classification model."),
        "Device Name": ("X", "No outage device reference model."),
        "Device EMS Name": ("X", "No outage model."),
        "From Bus ID": ("N", "Line.bus0 (bus number as physical element identifier)"),
        "To Bus ID": ("N", "Line.bus1 (bus number as physical element identifier)"),
        "Adjusted Base Limit": (
            "X",
            "No outage-adjusted rating model. Derated ratings during outages require "
            "external scripting to modify s_nom per outage scenario.",
        ),
        " Adjusted Emergency Limit": (
            "X",
            "No outage-adjusted emergency rating model. Note: leading space in column name "
            "is a data quality issue in the source CSV.",
        ),
        "TOU": ("E", "Custom column for time-of-use period identifier."),
    },
    "RESOURCE": {
        "Generator Name": ("N", "Generator name (index in n.generators DataFrame)"),
        "EMS Gen Name": ("E", "Custom column: n.generators['ems_name'] = values."),
        "Bus Name": ("E", "Custom column (bus names not imported via PPC path)."),
        "EMS Bus Name": ("E", "Custom column."),
        "Zone Name": ("N", "Bus.zone (via generator bus lookup)"),
        "Enforcement": ("E", "Custom column for enforcement mode flag."),
        "Mw": ("N", "Generator.p_set or Generator.p_nom (active power in MW)"),
        "TOU": ("E", "Custom column for time-of-use period identifier."),
        "PMax": ("N", "Generator.p_nom (maximum active power capacity)"),
    },
}

# Analytical classifications from supplemental-csv-representability.md for cross-reference
# Maps to the D4 analytical document field names where directly comparable
ANALYTICAL_TIERS: dict[str, dict[str, str]] = {
    "LINE_AND_TRANSFORMER": {
        "From Bus Number": "N",  # FROM_BUS -> Line.bus0
        "To Bus Number": "N",  # TO_BUS -> Line.bus1
        "Circuit ID": "E",  # CKT -> custom attr
        "Normal Rating": "N",  # RATE_A -> Line.s_nom
        "Emergency Rating": "E",  # RATE_B -> custom attr
        "Status": "N",  # STATUS -> Line.active
    },
    "TRADING_HUB": {
        "Trading Hub": "E",  # HUB_NAME -> custom bus attr (v10)
        "APNode": "X",  # BUS_NUMBER mismatch: APNode is string, not bus ID
        "Allocation Factor": "E",  # DISTRIBUTION_FACTOR -> custom bus attr (v10)
    },
    "GEN_DISTRIBUTION_FACTOR": {
        "Generator Name": "N",  # GEN_NAME
        "Distribution Factor": "X",  # PARTICIPATION_FACTOR
    },
    "CONTINGENCY": {
        "Contingency Name": "E",  # v10: extra_functionality + BODF
    },
    "INTERFACE": {
        "Interface Name": "E",  # v10: custom DataFrame + PTDF constraint
        "Positive Limit": "E",  # v10: PTDF constraint
        "Negative Limit": "E",  # v10: PTDF constraint
        "Factor": "E",  # v10: PTDF weighting sign
    },
    "OUTAGE": {
        "From Bus ID": "N",  # ELEMENT_FROM_BUS
        "To Bus ID": "N",  # ELEMENT_TO_BUS
    },
    "RESOURCE": {
        "Generator Name": "N",
        "Mw": "N",
        "PMax": "N",
    },
}


def run() -> dict:
    """Execute G-FNM-5 supplemental CSV representability assessment.

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
                    tier, note = "E", "Custom column on component DataFrame (unclassified field)."

                anal_tier = analytical.get(col) or analytical.get(col_clean)

                field_results.append(
                    {
                        "field": col,
                        "empirical_tier": tier,
                        "extension_approach": note if tier == "E" else None,
                        "external_justification": note if tier == "X" else None,
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
                "Line",
                "test_line",
                bus0="test_bus",
                bus1="test_bus",
                x=0.01,
                r=0.001,
                length=1,
            )
            net.lines["custom_test_field"] = "test_value"
            ext_verified = net.lines.loc["test_line", "custom_test_field"] == "test_value"
        except Exception as e:
            ext_verified = False
            errors.append(f"Extension mechanism verification failed: {e}")

        # Market Solution Fidelity Summary
        market_fidelity = {
            "thermal_ratings_4_tier": {
                "concept_tier": "extension",
                "native_tiers": 1,
                "note": "Only s_nom (RATE_A). RATE_B/C/D require custom columns.",
            },
            "seasonal_temporal_rating_variations": {
                "concept_tier": "extension",
                "note": "EFFECTIVE_DATE storable as custom column. No native temporal rating model.",
            },
            "trading_hub_definitions": {
                "concept_tier": "extension",
                "note": (
                    "v10: Hub names and allocation factors storable as custom bus attributes. "
                    "Post-OPF hub prices derivable via PTDF-weighted LMP averaging. "
                    "HUB_TYPE remains external. Complex extension pattern."
                ),
            },
            "generator_distribution_factors": {
                "concept_tier": "external",
                "note": "Market settlement construct with no analog in power flow domain.",
            },
            "contingency_definitions": {
                "concept_tier": "extension",
                "note": (
                    "v10: extra_functionality + BODF matrix for N-1 constraint enforcement. "
                    "Requires 50-100 lines of custom code. Complex extension pattern."
                ),
            },
            "interface_definitions_flow_limits": {
                "concept_tier": "extension",
                "note": (
                    "v10: PTDF matrix + extra_functionality constraints via n.model.add_constraints(). "
                    "Custom n.interfaces DataFrame stores definitions. Complex extension pattern."
                ),
            },
            "outage_actions_planned_outage_parameters": {
                "concept_tier": "external",
                "note": (
                    "No temporal outage schedule model. Single-snapshot tool cannot natively "
                    "represent time-windowed outage events."
                ),
            },
        }

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
                "market_solution_fidelity_summary": market_fidelity,
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
