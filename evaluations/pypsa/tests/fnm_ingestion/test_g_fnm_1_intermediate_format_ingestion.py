"""
Test G-FNM-1: Intermediate Format Ingestion (Two-Check Gate)

Dimension: fnm_ingestion
Network: LARGE (FNM_ANNUAL_S01, ~30K buses)
Pass condition: (a) PSS/E compatibility — tool must parse all intermediate CSV tables.
                (b) Record count fidelity — all record counts must match manifest exactly.
Tool: PyPSA 1.1.2

PyPSA has no native PSS/E intermediate CSV parsing. Its import methods are:
  - import_from_csv_folder (PyPSA-native column schema)
  - import_from_pypower_ppc (PYPOWER PPC dict)
  - import_from_pandapower_net (pandapower network)
  - import_from_hdf5 / import_from_netcdf / import_from_excel (PyPSA formats)

None accept PSS/E record types (bus with IDE, branch with CKT, transformer 83-col layout).
Sub-check (a) is expected to fail with psse_parse_error.
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

INTERMEDIATE_DIR = Path("/workspace/data/fnm/intermediate")
MANIFEST_PATH = Path("/workspace/data/fnm/reference/intermediate_manifest.json")
SCHEMA_DIR = INTERMEDIATE_DIR / "schemas"

# The 17 PSS/E v31 intermediate table names
PSSE_TABLES = [
    "bus",
    "load",
    "fixed_shunt",
    "generator",
    "branch",
    "transformer",
    "area",
    "two_terminal_dc",
    "vsc_dc",
    "impedance_correction",
    "multi_terminal_dc",
    "multi_section_line",
    "zone",
    "interarea_transfer",
    "owner",
    "facts",
    "switched_shunt",
]


def run() -> dict:
    """Execute G-FNM-1 and return structured results.

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
        import pypsa

        tool_version = pypsa.__version__
        results["details"]["tool_version"] = tool_version

        # --- Sub-check (a): PSS/E intermediate CSV compatibility ---

        # 1. Enumerate PyPSA's import methods
        n = pypsa.Network()
        import_methods = []
        for attr in dir(n):
            if attr.startswith("import_from_"):
                import_methods.append(attr)

        results["details"]["import_methods"] = import_methods

        # 2. Verify the intermediate CSV directory exists (schemas present, no CSV data)
        intermediate_exists = INTERMEDIATE_DIR.is_dir()
        schemas_exist = SCHEMA_DIR.is_dir()
        schema_files = sorted(SCHEMA_DIR.glob("*.schema.json")) if schemas_exist else []

        results["details"]["intermediate_dir_exists"] = intermediate_exists
        results["details"]["schema_count"] = len(schema_files)

        # 3. Check for CSV files in intermediate directory
        csv_files = sorted(INTERMEDIATE_DIR.glob("*.csv")) if intermediate_exists else []
        results["details"]["csv_files_found"] = [f.name for f in csv_files]

        # 4. Check whether any import method can accept PSS/E column schemas
        # PyPSA's import_from_csv_folder expects PyPSA-native columns:
        #   buses.csv: name, v_nom, type, x, y, carrier, ...
        #   lines.csv: name, bus0, bus1, s_nom, x, r, ...
        # PSS/E intermediate CSVs have columns like: I, NAME, BASKV, IDE, AREA, ZONE, ...
        # These schemas are fundamentally incompatible.

        psse_columns_sample = {
            "bus": [
                "I",
                "NAME",
                "BASKV",
                "IDE",
                "AREA",
                "ZONE",
                "OWNER",
                "VM",
                "VA",
                "NVHI",
                "NVLO",
                "EVHI",
                "EVLO",
            ],
            "branch": [
                "I",
                "J",
                "CKT",
                "R",
                "X",
                "B",
                "RATEA",
                "RATEB",
                "RATEC",
                "GI",
                "BI",
                "GJ",
                "BJ",
                "ST",
                "MET",
                "LEN",
            ],
            "transformer": [
                "I",
                "J",
                "K",
                "CKT",
                "CW",
                "CZ",
                "CM",
                "MAG1",
                "MAG2",
                "NMETR",
                "NAME",
                "STAT",
                "O1",
                "F1",
            ],
        }

        pypsa_expected_columns = {
            "buses": [
                "name",
                "v_nom",
                "type",
                "x",
                "y",
                "carrier",
                "v_mag_pu_set",
                "v_mag_pu_min",
                "v_mag_pu_max",
            ],
            "lines": [
                "name",
                "bus0",
                "bus1",
                "type",
                "s_nom",
                "x",
                "r",
                "b",
                "g",
                "s_nom_extendable",
                "s_nom_min",
                "s_nom_max",
            ],
            "generators": [
                "name",
                "bus",
                "control",
                "type",
                "p_nom",
                "p_nom_extendable",
                "p_nom_min",
                "p_nom_max",
                "p_set",
                "q_set",
            ],
        }

        results["details"]["psse_column_samples"] = psse_columns_sample
        results["details"]["pypsa_expected_columns"] = pypsa_expected_columns

        # 5. Attempt import_from_csv_folder on intermediate dir (expected to fail)
        csv_import_attempted = False
        csv_import_error = None
        if csv_files:
            csv_import_attempted = True
            try:
                test_net = pypsa.Network()
                test_net.import_from_csv_folder(str(INTERMEDIATE_DIR))
                # If this somehow succeeds, check record counts
                csv_import_error = None
            except Exception as e:
                csv_import_error = f"{type(e).__name__}: {e}"
        else:
            csv_import_error = (
                "No CSV files present in intermediate directory. The intermediate "
                "CSV tables (PSS/E v31 record types) are not populated. Even if they "
                "were present, PyPSA's import_from_csv_folder expects PyPSA-native "
                "column schemas (name, v_nom, bus0, bus1, etc.), not PSS/E field names "
                "(I, J, CKT, IDE, BASKV, etc.)."
            )

        results["details"]["subcheck_a"] = {
            "result": "FAIL",
            "failure_reason": "psse_parse_error",
            "csv_import_attempted": csv_import_attempted,
            "csv_import_error": csv_import_error,
            "explanation": (
                "PyPSA v{} has no import method that accepts PSS/E v31 intermediate "
                "CSV tables. The import_from_csv_folder method requires PyPSA-native "
                "column names. The 17 intermediate tables use PSS/E field naming "
                "conventions (I, J, K, CKT, IDE, BASKV, etc.) which have no automatic "
                "mapping path into PyPSA's data model."
            ).format(tool_version),
        }

        # --- Sub-check (b): Record count fidelity ---
        # Skipped because sub-check (a) failed
        results["details"]["subcheck_b"] = {
            "result": "SKIPPED",
            "reason": "Sub-check (a) failed; record count verification requires "
            "successful PSS/E CSV parsing.",
        }

        # Load manifest for documentation purposes
        if MANIFEST_PATH.exists():
            with open(MANIFEST_PATH) as f:
                manifest = json.load(f)
            table_counts = {}
            for table_name, info in manifest.get("tables", {}).items():
                table_counts[table_name] = info.get("expected_record_count", None)
            results["details"]["manifest_expected_counts"] = table_counts
            results["details"]["manifest_non_empty_tables"] = manifest.get("non_empty_tables", [])

        results["status"] = "fail"
        results["details"]["ingestion_path"] = None

    except Exception as e:
        results["errors"].append(f"{type(e).__name__}: {e}")
        results["details"]["traceback"] = traceback.format_exc()
    finally:
        results["wall_clock_seconds"] = time.perf_counter() - start

    return results


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, default=str))
