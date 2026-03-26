---
test_id: G-FNM-2
tool: powermodels
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: 2ae0204c
status: skip
blocked_by: G-FNM-1
workaround_class: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
ingestion_path: null
cpu_threads_used: null
cpu_threads_available: null
sced_mode: null
test_category: null
timestamp: "2026-03-24T00:00:00Z"
---

# G-FNM-2: Field Coverage Audit

## Result: SKIP

Skipped because G-FNM-1 failed. The field coverage audit requires successful ingestion
of intermediate CSV tables, which PowerModels cannot perform. The PSS/E intermediate CSV
format is not supported (no CSV parser exists in PowerModels.jl).

G-FNM-2 audits field-level coverage of the ingested data model against the intermediate
schema's field criticality matrix. Since the intermediate CSV format cannot be ingested,
the audit has no data to evaluate.

## Blocked By

**G-FNM-1** -- PSS/E intermediate CSV format not supported (`failure_reason: psse_parse_error`).
