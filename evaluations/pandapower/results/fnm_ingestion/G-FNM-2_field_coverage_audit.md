---
test_id: G-FNM-2
tool: pandapower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v11"
skill_version: "v2"
test_hash: "2941efff"
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
timestamp: 2026-03-24T12:00:00Z
---

# G-FNM-2: Field Coverage Audit vs Criticality Matrix

## Result: SKIP

G-FNM-2 is blocked by G-FNM-1 failure. pandapower cannot ingest the intermediate
CSV format (no PSS/E parser), so there is no intermediate-path network model to
audit for field coverage. The field coverage audit requires a successfully ingested
network model from the intermediate CSV tables.

## Blocked By

**G-FNM-1** failed because pandapower 3.4.0 has no native PSS/E CSV parser.
Without a network model produced from intermediate CSV ingestion, the field
coverage audit against the criticality matrix cannot be performed on the
intermediate ingestion path.

Note: Field coverage via the MATPOWER fallback path was assessed in the v10
evaluation and found 100% DCPF-critical coverage (19/19 fields), 55.8%
ACPF-critical coverage (29/52), and approximately 27.6% informational coverage
(24/87). That assessment remains valid for the MATPOWER fallback path used by
G-FNM-3/4/5 but does not satisfy the intermediate format ingestion requirement
of G-FNM-2.
