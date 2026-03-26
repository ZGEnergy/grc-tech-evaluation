---
test_id: G-FNM-1
tool: matpower
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: "62aeab18"
status: fail
failure_reason: psse_parse_error
workaround_class: null
ingestion_path: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T12:00:00Z"
---

# G-FNM-1: Two-check gate -- PSS/E format compatibility + record count fidelity

## Result: FAIL

## Approach

G-FNM-1 has two sub-checks:

**(a) PSS/E format compatibility:** Determine whether MATPOWER can ingest the
intermediate CSV tables (17 tables representing PSS/E v31 record types: bus, load,
fixed_shunt, generator, branch, transformer, area, two_terminal_dc, vsc_dc,
impedance_correction, multi_terminal_dc, multi_section_line, zone, interarea_transfer,
owner, facts, switched_shunt).

**(b) Record count fidelity:** If CSV loading succeeds, compare ingested record
counts against `manifest.json` expected counts.

MATPOWER's data import API was systematically surveyed in the 8.1 source tree. The
tool provides exactly two data ingestion paths:

1. **`loadcase()`** -- reads MATPOWER case format (`.m` script files or `.mat`
   binary files) containing an MPC struct with `bus`, `branch`, `gen`, and
   `gencost` matrices. The `help loadcase` output explicitly states it supports
   only `.m` and `.mat` files.
2. **`psse2mpc()`** -- parses PSS/E RAW format files (`.raw`) and converts them
   to the MPC struct format.

No built-in function exists for importing CSV tables. A search of the MATPOWER 8.1
`lib/` directory for any file or function containing "csv" returned zero results.
Candidate function names (`csv2mpc`, `importcsv`, `load_csv`, `readcsv`) do not
exist in the MATPOWER function library.

This is confirmed by the research-version.md capability table which states:
"CSV Data Import: no -- `loadcase()` supports only `.m` and `.mat` files natively;
CSV requires custom parsing scripts."

## Output

### Sub-check (a): PSS/E format compatibility

| Check | Result |
|-------|--------|
| `loadcase()` available | Yes (`.m`/`.mat` only) |
| `psse2mpc()` available | Yes (`.raw` only) |
| CSV table import function available | No |
| Can parse intermediate CSV tables | No |

MATPOWER cannot parse the intermediate CSV tables. The intermediate format is a
tool-neutral tabular representation of PSS/E v31 records. Reconstructing an MPC
struct from these CSVs would require writing a complete custom importer that:

1. Reads all 17 CSV tables via Octave's `csvread()` or `dlmread()`
2. Maps PSS/E v31 field names to MATPOWER column indices
3. Merges `branch.csv` and `transformer.csv` into the unified MATPOWER branch matrix
4. Converts PSS/E bus type codes to MATPOWER conventions
5. Handles transformer tap ratio encoding (PSS/E 0.0 = unity tap)
6. Constructs the `gencost` matrix from generator cost data

This is not a minor API workaround -- it is building a new importer from scratch,
equivalent in scope to `psse2mpc()` itself. [tool-specific: no CSV/tabular import API]

**Sub-check (a) result: FAIL** (`psse_parse_error`)

### Sub-check (b): Record count fidelity

**BLOCKED** -- CSV parsing failed in sub-check (a). Record count fidelity cannot
be evaluated.

### Fallback Path

The MATPOWER fallback path (`data/fnm/reference/cleaned/fnm_main_island.mat`) is
available for G-FNM-3, G-FNM-4, and G-FNM-5. This `.mat` file contains the
pre-cleaned FNM network in MATPOWER's native format.

## Workarounds

None possible within MATPOWER's API. CSV table ingestion would require building a
complete custom importer (hundreds of lines of Octave code) to map 17 CSV tables to
the MPC struct format. This is a fundamental architectural limitation of MATPOWER's
data model, which uses position-indexed numeric matrices rather than named-column
tabular data.

## Timing

- **Wall-clock:** null (API capability survey only, no data processing attempted)
- **Timing source:** null
- **Peak memory:** null (no data loaded)

## Test Script

No test script was executed. The determination that MATPOWER cannot parse intermediate
CSV tables was made by:

1. Inspecting `help loadcase` output confirming only `.m`/`.mat` support
2. Searching the MATPOWER 8.1 `lib/` directory for any CSV-related functions (zero results)
3. Reviewing the research-version.md capability table confirming `CSV Data Import: no`
