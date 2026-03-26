---
test_id: G-FNM-2
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: 64cf2500
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
timestamp: 2026-03-24T12:00:00Z
---

# G-FNM-2: Field Fidelity

## Result: SKIP

## Finding

G-FNM-2 is blocked by G-FNM-1. PyPSA v1.1.2 cannot parse the intermediate CSV tables
(PSS/E v31 format), so field-level fidelity verification cannot be performed.

## Evidence

G-FNM-1 failed sub-check (a) with `failure_reason: psse_parse_error`. PyPSA has no
import method that accepts PSS/E v31 record types. Without successful ingestion of the
intermediate CSV data, there is no tool-internal representation to compare against the
source field values.

## Implications

Field fidelity cannot be assessed for PyPSA via the intermediate CSV path. The MATPOWER
fallback path (used by G-FNM-3 through G-FNM-5) inherently loses PSS/E-specific fields
such as the 83-column transformer record, switched shunt discrete blocks, FACTS devices,
and multi-terminal DC data — these fields are not representable in the MATPOWER PPC
format that PyPSA's `import_from_pypower_ppc` consumes.
