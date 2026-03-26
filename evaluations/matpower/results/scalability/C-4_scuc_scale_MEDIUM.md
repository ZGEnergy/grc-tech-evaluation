---
test_id: C-4
tool: matpower
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: "19c1d696"
status: skip
blocked_by: C-4
workaround_class: null
wall_clock_seconds: null
timestamp: "2026-03-24T19:00:00Z"
---

# C-4: SCUC 24hr on MEDIUM — SKIPPED

## Result: SKIP

C-4 MEDIUM is gated by C-4 SMALL per v11 Suite C tier gate semantics.
C-4 SMALL failed due to GLPK exit flag mapping issue in MATPOWER's `miqps_glpk.m` wrapper.
MILP MEDIUM tests are skipped when C-4 SMALL fails.
