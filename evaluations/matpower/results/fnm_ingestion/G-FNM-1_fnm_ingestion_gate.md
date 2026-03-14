---
test_id: G-FNM-1
tool: matpower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v10"
skill_version: "v1"
test_hash: "7827a912"
status: fail
failure_reason: psse_parse_error
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 0.001
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 30
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# G-FNM-1: Two-check gate — PSS/E format compatibility + record count fidelity

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

MATPOWER's data import API was systematically surveyed. The tool provides exactly
two data ingestion paths:

1. **`loadcase()`** — reads MATPOWER case format (`.m` script files or `.mat`
   binary files) containing an MPC struct with `bus`, `branch`, `gen`, and
   `gencost` matrices.
2. **`psse2mpc()`** — parses PSS/E RAW format files (`.raw`) and converts them
   to the MPC struct format.

No built-in function exists for importing CSV tables. A search for candidate
functions (`csv2mpc`, `importcsv`, `load_csv`, `readcsv`) returned no matches
in the MATPOWER 8.1 function library.

## Output

### Sub-check (a): PSS/E format compatibility

| Check | Result |
|-------|--------|
| `psse2mpc()` available | Yes |
| CSV table import function available | No |
| Can parse intermediate CSV tables | No |

MATPOWER cannot parse the intermediate CSV tables. The intermediate format is a
tool-neutral tabular representation of PSS/E v31 records. Reconstructing an MPC
struct from these CSVs would require writing a complete custom importer that:

1. Reads all 17 CSV tables via Octave's `csvread()` or `dlmread()`
2. Maps PSS/E v31 field names to MATPOWER column indices
3. Merges `branch.csv` (24,117 records) and `transformer.csv` (9,723 records)
   into the unified MATPOWER branch matrix (33,840 rows)
4. Converts PSS/E bus type codes to MATPOWER conventions
5. Handles transformer tap ratio encoding (PSS/E 0.0 = unity tap)
6. Constructs the `gencost` matrix from generator cost data

This is not a minor API workaround -- it is building a new importer from scratch,
equivalent in scope to `psse2mpc()` itself.

**Sub-check (a) result: FAIL** (`psse_parse_error`)

### Sub-check (b): Record count fidelity

**BLOCKED** -- CSV parsing failed in sub-check (a). Record count fidelity cannot
be evaluated.

Reference counts from `intermediate_manifest.json` (for documentation):

| Table | Expected Records |
|-------|-----------------|
| bus | 30,307 |
| load | 15,062 |
| fixed_shunt | 0 |
| generator | 5,768 |
| branch | 24,117 |
| transformer | 9,723 |
| area | 49 |
| zone | 90 |
| switched_shunt | 3,114 |

### Fallback Path

The MATPOWER fallback path (`data/fnm/reference/cleaned/fnm_main_island.mat`) is
available for G-FNM-3, G-FNM-4, and G-FNM-5. This `.mat` file contains the
pre-cleaned FNM network in MATPOWER's native format.

## Workarounds

- **What:** No workaround is possible within MATPOWER's API. CSV table ingestion
  would require building a complete custom importer (hundreds of lines of Octave
  code) to map 17 CSV tables to the MPC struct format.
- **Why:** MATPOWER's data model is designed around its own case format and PSS/E
  RAW files. It has no generic tabular data import capability.
- **Durability:** blocking -- requires building a new importer from scratch, not
  using an existing API in a non-obvious way.
- **Grade impact:** G-FNM-1 fails, blocking G-FNM-2. G-FNM-3/4/5 proceed via
  the MATPOWER fallback path (`.mat` file).

## Timing

- **Wall-clock:** 0.001 seconds (API survey only, no data processing)
- **Timing source:** measured
- **Peak memory:** not measured (no data loaded)

## Test Script

**Path:** `evaluations/matpower/tests/fnm_ingestion/test_g_fnm_1_fnm_ingestion_gate.m`

Key verification code:

```matlab
% Confirm psse2mpc exists (reads RAW, not CSV)
has_psse2mpc = exist('psse2mpc', 'file') > 0;  % returns 1

% Search for any CSV import function
csv_funcs = {'csv2mpc', 'importcsv', 'load_csv', 'readcsv'};
% All return 0 — no CSV import capability exists
```
