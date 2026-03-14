---
test_id: G-FNM-2
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: null
status: skip
failure_reason: null
workaround_class: null
blocked_by: G-FNM-1
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# G-FNM-2: Field fidelity

## Result: SKIP

## Finding

G-FNM-2 is blocked by G-FNM-1. PyPSA cannot parse the intermediate CSV tables
(PSS/E format), so field-level fidelity verification cannot be performed.

Per the G-FNM-1 pass condition: "If count check fails, skip G-FNM-2 through G-FNM-5."
However, since the failure is at sub-check (a) (PSS/E compatibility), only G-FNM-2
is blocked. G-FNM-3 through G-FNM-5 proceed via MATPOWER fallback.
