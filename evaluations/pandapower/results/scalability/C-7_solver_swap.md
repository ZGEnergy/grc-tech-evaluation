---
test_id: C-7
tool: pandapower
dimension: scalability
network: N/A
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: "PYPOWER interior point"
timestamp: 2026-03-06T00:00:00Z
---

# C-7: Solver swap

## Result: FAIL

## Approach

**Cannot test.** pandapower's `rundcopp()` exclusively uses PYPOWER's built-in interior point solver. There is no parameter to select an alternative solver (HiGHS, GLPK, or any other). The pass condition requires that "solver swap requires only parameter change, not reformulation" -- but pandapower offers no solver swap mechanism at all for its native OPF.

The PowerModels.jl bridge (`pp.runpm_dc_opf()`) theoretically supports external solvers, but this requires a Julia installation and separate configuration, which is outside the native pandapower API.

As confirmed in C-3, only the single PYPOWER IP solver is available.

## Output

No test executed.

## Workarounds

None available within pandapower's native Python API.

## Timing

- **Wall-clock:** N/A
- **Peak memory:** N/A

## Test Script

No test script written (pandapower has no solver swap capability for OPF).
