---
test_id: G-FNM-1
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: 62aeab18
status: fail
failure_reason: psse_parse_error
workaround_class: null
blocked_by: null
ingestion_path: null
wall_clock_seconds: 1.873
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: 2026-03-24T12:00:00Z
---

# G-FNM-1: Intermediate Format Ingestion (Two-Check Gate)

## Result: FAIL

## Sub-check (a): PSS/E Compatibility

**Result: FAIL** -- `failure_reason: psse_parse_error`

PyPSA v1.1.2 has no native capability to read PSS/E-format data, whether in raw `.raw`
format or in the intermediate CSV format derived from PSS/E v31 record types. PyPSA's
complete set of import methods:

| Method | Format |
|--------|--------|
| `import_from_csv_folder` | PyPSA-native CSV (buses.csv, lines.csv, generators.csv, etc.) |
| `import_from_pypower_ppc` | PYPOWER PPC dictionary |
| `import_from_pandapower_net` | pandapower network object |
| `import_from_hdf5` | HDF5 (PyPSA format) |
| `import_from_netcdf` | NetCDF (PyPSA format) |
| `import_from_excel` | Excel (PyPSA format) |

None of these methods accept PSS/E record types. The intermediate CSV tables use PSS/E
v31 field names and semantics:

- **Bus table:** columns `I`, `NAME`, `BASKV`, `IDE`, `AREA`, `ZONE`, `OWNER`, `VM`, `VA`, `NVHI`, `NVLO`, `EVHI`, `EVLO`
- **Branch table:** columns `I`, `J`, `CKT`, `R`, `X`, `B`, `RATEA`, `RATEB`, `RATEC`, `GI`, `BI`, `GJ`, `BJ`, `ST`, `MET`, `LEN`
- **Transformer table:** 83 PSS/E v31 columns including `I`, `J`, `K`, `CKT`, `CW`, `CZ`, `CM`, `MAG1`, `MAG2`, `NMETR`, `NAME`, `STAT`

PyPSA's `import_from_csv_folder` expects PyPSA-native column schemas:

- **buses.csv:** `name`, `v_nom`, `type`, `x`, `y`, `carrier`, `v_mag_pu_set`, `v_mag_pu_min`, `v_mag_pu_max`
- **lines.csv:** `name`, `bus0`, `bus1`, `type`, `s_nom`, `x`, `r`, `b`, `g`
- **generators.csv:** `name`, `bus`, `control`, `type`, `p_nom`, `p_set`, `q_set`

These schemas are fundamentally incompatible. There is no column-name mapping, no
PSS/E field translator, and no import adapter in PyPSA's public API.

## Sub-check (b): Record Count Fidelity

**Result: SKIPPED** -- Sub-check (a) failed; record count verification requires
successful PSS/E CSV parsing.

For reference, the intermediate manifest expects:

| Table | Expected Records |
|-------|-----------------|
| bus | ~30,000 |
| load | ~15,000 |
| generator | ~5,800 |
| branch | ~24,000 |
| transformer | ~9,700 |
| area | 49 |
| zone | 90 |
| switched_shunt | ~3,100 |

## Approach

The test script enumerates all `import_from_*` methods on a PyPSA `Network` object,
verifies the intermediate CSV directory structure, compares PSS/E v31 column schemas
against PyPSA-native column expectations, and confirms the absence of any PSS/E
ingestion path. The test was executed inside the devcontainer against PyPSA v1.1.2.

## Output

```json
{
  "subcheck_a": {
    "result": "FAIL",
    "failure_reason": "psse_parse_error",
    "csv_import_attempted": false,
    "explanation": "PyPSA v1.1.2 has no import method that accepts PSS/E v31 intermediate CSV tables."
  },
  "subcheck_b": {
    "result": "SKIPPED"
  },
  "import_methods": [
    "import_from_csv_folder",
    "import_from_excel",
    "import_from_hdf5",
    "import_from_netcdf",
    "import_from_pandapower_net",
    "import_from_pypower_ppc"
  ]
}
```

## Workarounds

None attempted. The absence of PSS/E ingestion is a fundamental format gap, not a
configuration issue. A workaround would require writing a complete PSS/E-to-PyPSA
converter covering all 17 intermediate tables (bus, load, fixed_shunt, generator,
branch, transformer, area, two_terminal_dc, vsc_dc, impedance_correction,
multi_terminal_dc, multi_section_line, zone, interarea_transfer, owner, facts,
switched_shunt), which constitutes external tooling rather than a tool workaround.

## Implications

- G-FNM-1 fails with `psse_parse_error`, `ingestion_path: null`.
- G-FNM-2 (field fidelity) is blocked by G-FNM-1.
- G-FNM-3 through G-FNM-5 proceed via MATPOWER `.m` fallback path, which uses PyPSA's
  `import_from_pypower_ppc` method through the shared MATPOWER loader.

## Timing

- **Wall-clock:** 1.873 seconds (API enumeration and schema inspection)
- **Timing source:** measured
- **Peak memory:** not measured (no data ingestion occurred)

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_1_intermediate_format_ingestion.py`
