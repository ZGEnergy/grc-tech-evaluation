---
test_id: G-FNM-2
tool: matpower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v10"
skill_version: "v1"
test_hash: "2396d6a5"
status: skip
workaround_class: null
blocked_by: G-FNM-1
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# G-FNM-2: Field coverage audit against criticality matrix

## Result: SKIP

## Finding

G-FNM-2 is blocked by G-FNM-1 failure. MATPOWER cannot parse the intermediate CSV
tables (failure_reason: `psse_parse_error`), so field coverage against the criticality
matrix cannot be evaluated.

G-FNM-2 requires successful CSV ingestion to audit whether DCPF-critical fields
(19 fields across bus, branch, transformer, generator, and load tables) are
preserved during import. Since MATPOWER has no CSV import capability, this test
cannot proceed.

## Implications

The field coverage audit is not applicable to MATPOWER when using the intermediate
CSV format. When MATPOWER ingests data via its native `.m`/`.mat` format or
`psse2mpc()`, field coverage is determined by the MATPOWER case format specification,
which preserves all DCPF-critical fields by design.
