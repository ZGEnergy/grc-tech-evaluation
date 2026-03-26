---
test_id: G-FNM-2
tool: powersimulations
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: be3122c0
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
sced_mode: null
test_category: null
timestamp: "2026-03-24T00:00:00Z"
---

# G-FNM-2: Field coverage audit against criticality matrix

## Result: SKIP

## Finding

G-FNM-2 is blocked by G-FNM-1 failure. PowerSystems.jl v4.6.2 cannot parse the
PSS/E-derived intermediate CSV tables (no parser exists for this format), and PSS/E
RAW v31 direct parsing also fails. Field-level coverage against the criticality matrix
cannot be evaluated without successful ingestion of the intermediate format.

Field coverage via the MATPOWER fallback path is not meaningful for this test because
MATPOWER format already collapses many PSS/E-specific fields (e.g., switched shunt
discrete steps, transformer control modes, area interchange targets).

## Evidence

- G-FNM-1 status: fail (psse_parse_error)
- failure_reason: PowerSystems.jl has no parser for PSS/E-derived intermediate CSV tables
- No PSS/E-parsed or intermediate-CSV-parsed System object available for field inspection

## Implications

G-FNM-2 cannot produce a valid field coverage assessment. Downstream tests G-FNM-3/4/5
proceed via MATPOWER fallback but field fidelity is inherently limited by the MATPOWER
intermediate format.
