---
test_id: G-FNM-1
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: 1d40595a
status: fail
failure_reason: psse_parse_error
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# G-FNM-1: Intermediate format ingestion

## Result: FAIL

## Sub-check (a): PSS/E compatibility

**Result: FAIL** -- `failure_reason: psse_parse_error`

PyPSA v1.1.2 has no native capability to read PSS/E-format data, whether in raw `.raw`
format or in the intermediate CSV format derived from PSS/E v31 record types. PyPSA's
supported import methods are:

| Method | Format |
|--------|--------|
| `import_from_csv_folder` | PyPSA-native CSV (buses.csv, lines.csv, generators.csv, etc.) |
| `import_from_pypower_ppc` | PYPOWER PPC dictionary |
| `import_from_pandapower_net` | pandapower network object |
| `import_from_hdf5` | HDF5 (PyPSA format) |
| `import_from_netcdf` | NetCDF (PyPSA format) |
| `import_from_excel` | Excel (PyPSA format) |

None of these methods accept PSS/E record types (bus with IDE codes, branch with CKT
identifiers, transformer with 83-column PSS/E v31 layout, switched shunt discrete
blocks, FACTS devices, multi-terminal DC, etc.). The intermediate CSV tables use PSS/E
field names and semantics (I, J, K, CKT, IDE, STATUS, etc.) that have no mapping path
into any PyPSA import method.

The `import_from_csv_folder` method reads PyPSA's own tabular format where column names
correspond to PyPSA component attributes (e.g., `bus`, `v_nom`, `p_set`), not PSS/E
field names. Attempting to point it at the intermediate CSV directory would fail because
the column schemas are incompatible.

## Sub-check (b): Record count fidelity

**Result: SKIPPED** -- Sub-check (a) failed; record count verification requires
successful parsing.

## Approach

Verification was performed by inspecting PyPSA v1.1.2's public API surface inside the
devcontainer. All six `import_from_*` methods were enumerated and their signatures
inspected. None accept PSS/E-format input. This confirms that PyPSA cannot parse the
intermediate CSV tables without an external conversion layer.

## Workarounds

None attempted. The absence of PSS/E ingestion is a fundamental format gap, not a
configuration issue. A workaround would require writing a complete PSS/E-to-PyPSA
converter covering all 17 intermediate tables, which constitutes external tooling
rather than a tool workaround.

## Implications

- G-FNM-1 fails with `psse_parse_error`.
- G-FNM-2 (field fidelity) is blocked by G-FNM-1.
- G-FNM-3 through G-FNM-5 proceed via MATPOWER `.m` fallback path, which uses PyPSA's
  `import_from_pypower_ppc` method through the shared MATPOWER loader.

## Test Script

No test script was written. The verification was an API surface inspection confirming
the absence of any PSS/E ingestion path in PyPSA's public interface.
