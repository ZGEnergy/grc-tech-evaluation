---
test_id: G-FNM-2
tool: gridcal
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: "b2c7738b"
status: skip
workaround_class: null
blocked_by: G-FNM-1
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
ingestion_path: null
test_category: null
timestamp: 2026-03-24T00:00:00Z
---

# G-FNM-2: Field coverage audit against criticality matrix

## Result: SKIP

Blocked by G-FNM-1 failure. GridCal cannot parse the intermediate CSV tables,
so field coverage audit against the criticality matrix cannot be performed on
the CSV-ingested data.

G-FNM-2 requires successful PSS/E CSV parsing (G-FNM-1 sub-check (a)) to
audit field-level coverage. Since GridCal has no CSV network import capability,
this test is skipped.

The MATPOWER fallback path (used by G-FNM-3/4/5) does not provide sufficient
field granularity for the criticality matrix audit, as MATPOWER format loses
PSS/E-specific fields (transformer tap control modes, switched shunt steps,
FACTS parameters, area interchange data, etc.).
