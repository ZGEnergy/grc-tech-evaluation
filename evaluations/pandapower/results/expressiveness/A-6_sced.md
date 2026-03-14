---
test_id: A-6
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "5577e704"
status: fail
workaround_class: blocking
blocked_by: A-5
wall_clock_seconds: 0.75
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 73
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# A-6: Fix commitment from A-5, solve economic dispatch

## Result: FAIL

**Failure reason:** `unsupported_in_installed_version`
**Blocked by:** A-5 (SCUC)

## Approach

A-6 depends on A-5 to provide a generator commitment schedule. Since pandapower 3.4.0 does not support SCUC (A-5 fails), no commitment schedule is available to fix as input for economic dispatch.

Additionally, pandapower lacks native SCED capability independent of the A-5 dependency:

- **Multi-period economic dispatch** — `rundcopp()` solves a single time step; no temporal coupling
- **Ramp rate constraints** — no inter-period dispatch rate limits to enforce between consecutive intervals
- **Fixed commitment schedule input** — no mechanism to fix a subset of generators as "on" or "off" while dispatching the rest (generators can be taken out of service via `in_service=False`, but this is not a UC-aware dispatch workflow)
- **N-1 security constraints** — OPF does not embed contingency constraints

The two-stage UC/ED workflow (commit then dispatch) is not achievable with pandapower's API.

## Output

No SCED solution was produced. The test confirmed:

1. A-5 prerequisite is unmet (no SCUC capability)
2. Even if a commitment schedule were provided externally, pandapower cannot solve multi-period economic dispatch with ramp rate constraints

## Workarounds

- **What:** No workaround exists within pandapower's API
- **Why:** Both the prerequisite (SCUC from A-5) and the test's own requirements (multi-period ED with ramp constraints) are outside pandapower's design scope
- **Durability:** blocking — achieving SCED would require a complete external optimization model
- **Grade impact:** Blocked by A-5; also independently infeasible due to missing SCED capabilities

## Timing

- **Wall-clock:** 0.75 s (import and capability check only — no solve attempted)
- **Timing source:** measured
- **Peak memory:** not measured (no solve)

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a6_sced.py`
