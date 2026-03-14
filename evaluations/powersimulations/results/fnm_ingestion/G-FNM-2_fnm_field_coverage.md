---
test_id: G-FNM-2
tool: powersimulations
dimension: fnm_ingestion
network: LARGE
status: fail
workaround_class: null
blocked_by: G-FNM-1
timestamp: "2026-03-14T13:15:56Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "21c38623"
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
input_path: null
---

# G-FNM-2: Field coverage audit against criticality matrix

## Result: FAIL

## Finding

G-FNM-2 is blocked by G-FNM-1 failure. PowerSystems.jl v4.6.2 cannot parse the
PSS/E RAW v31 file, so field-level coverage against the criticality matrix cannot
be evaluated on the native RAW ingestion path.

Field coverage via the MATPOWER fallback path is not meaningful for this test because
MATPOWER format already collapses many PSS/E-specific fields (e.g., switched shunt
discrete steps, transformer control modes, area interchange targets).

## Evidence

- G-FNM-1 status: fail (psse_parse_error)
- No PSS/E-parsed System object available for field inspection

## Implications

G-FNM-2 cannot produce a valid field coverage assessment. Downstream tests G-FNM-3/4/5
proceed via MATPOWER fallback but field fidelity is inherently limited by the MATPOWER
intermediate format.
