---
test_id: A-3
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 0.127
peak_memory_mb: null
loc: 135
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# A-3: Solve DC OPF with gen costs and line flow limits

## Result: QUALIFIED PASS

## Approach

Loaded IEEE 39-bus network via `from_mpc()`. Cost curves were imported from the MATPOWER case file (polynomial costs present for all 10 generators). Line limits were present from the import.

Solved DC OPF using `pp.rundcopp(net)`.

**Solver deviation:** The eval-config specifies HiGHS/GLPK as solvers, but pandapower's native `rundcopp()` uses PYPOWER's built-in interior point solver. There is no mechanism to swap in HiGHS or GLPK for the native OPF. The PowerModels.jl bridge would support external solvers but was not available/tested.

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Objective | 41,263.94 |
| Total generation | 6,254.23 MW |
| LMP range | 13.517 (nearly uniform) |
| LMP mean | 13.517 |

Generator dispatch (MW):

| Gen | p_mw |
|-----|------|
| 0 | 660.85 |
| 1 | 660.85 |
| 2 | 652.00 |
| 3 | 508.00 |
| 4 | 660.85 |
| 5 | 580.00 |
| 6 | 564.00 |
| 7 | 660.85 |
| 8 | 660.85 |
| ext_grid 0 | 646.00 |

LMPs are nearly uniform across all buses (13.517), indicating no binding line constraints on this network at the DC OPF solution.

LMPs are accessible via `net.res_bus["lam_p"]`.

## Workarounds

- **What:** Used PYPOWER interior point solver instead of HiGHS/GLPK.
- **Why:** pandapower's `rundcopp()` hard-codes the PYPOWER interior point solver. No API exists to swap solvers without using the PowerModels.jl bridge.
- **Durability:** stable -- this is the documented behavior of `rundcopp()`, not an undocumented workaround. However, it is a solver limitation relative to the evaluation requirements.
- **Grade impact:** The core functionality (DC OPF with costs, limits, and LMP extraction) works correctly. The solver limitation is a real architectural constraint of pandapower.

## Timing

- **Wall-clock:** 0.127 s
- **Peak memory:** not measured
- **Solver iterations:** not extracted

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a3_dcopf.py`
