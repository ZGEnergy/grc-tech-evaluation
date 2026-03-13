---
test_id: G-FNM-5
tool: powermodels
dimension: fnm_ingestion
network: LARGE
status: fail
workaround_class: blocking
blocked_by: G-FNM-1
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "7ead4cfb"
wall_clock_seconds: null
timing_source: null
---

# G-FNM-5: Supplemental CSV Representability

## Result: FAIL (BLOCKED)

## Reason

G-FNM-1 (intermediate format ingestion gate) failed. This test is blocked.

## Evidence

- **G-FNM-1 failure reason:** PowerModels.jl's PSS/E v31 parser crashes on the FNM RAW file header format. The MATPOWER fallback loaded but showed a 42.7% load count discrepancy against the manifest (scope mismatch: cleaned island vs full model).
- **Downstream impact:** All G-FNM-2 through G-FNM-5 tests require successful G-FNM-1 completion.

## Implications

PowerModels.jl cannot ingest the FNM network in any format. PSS/E v31 parsing is broken for this specific RAW header format, and the MATPOWER cleaned fallback has significant count discrepancies. This is an Expressiveness finding: the tool cannot parse large utility-scale networks in standard interchange formats.
