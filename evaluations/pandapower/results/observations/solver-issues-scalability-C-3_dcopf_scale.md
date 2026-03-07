---
test_id: C-3
tool: pandapower
dimension: scalability
protocol_version: "v4"
observation_type: solver-issues
timestamp: 2026-03-06T00:00:00Z
---

# Solver Issues: C-3 DC OPF at Scale

## Observation

pandapower's native DC OPF (`rundcopp()`) is locked to the PYPOWER built-in interior point solver. There is no parameter or API to select an alternative solver (HiGHS, GLPK, SCIP, Ipopt, or any other). This is a fundamental architectural limitation, not a configuration issue.

## Evidence

- `pp.rundcopp(net)` accepts no `solver` parameter
- The function internally calls PYPOWER's `pips()` (Python Interior Point Solver)
- The PowerModels.jl bridge (`pp.runpm_dc_opf()`) can use Julia solvers but requires a separate Julia installation and is outside the native Python API
- C-7 (solver swap) fails completely due to this limitation

## Impact

- Cannot verify solver consistency (C-3 pass condition partially unmet)
- Cannot benchmark solver performance comparisons (C-7 fails)
- Users cannot switch to potentially faster solvers for large-scale problems
- The PYPOWER IP solver showed 8.2s solve time on the 10,000-bus network and 1,530 MB peak memory -- a dedicated LP solver like HiGHS would likely be faster for this DC (linear) problem

## Related Tests

- C-3: Qualified pass (single solver only)
- C-7: Fail (no solver swap possible)
- A-3: Qualified pass (same limitation on TINY)
