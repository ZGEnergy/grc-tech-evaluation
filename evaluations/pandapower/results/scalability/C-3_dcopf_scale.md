---
test_id: C-3
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: 8.494
peak_memory_mb: 1530.9
loc: 113
solver: "PYPOWER interior point"
timestamp: 2026-03-06T00:00:00Z
---

# C-3: DC OPF at scale with multiple solvers

## Result: QUALIFIED PASS

## Approach

Loaded the ACTIVSg10k (~10,000-bus) MEDIUM network with 2,485 polynomial cost curves imported from the MATPOWER case. Solved DC OPF using `pp.rundcopp(net)`.

**Solver limitation:** The eval-config specifies "HiGHS, GLPK" for multi-solver comparison, but pandapower's `rundcopp()` only supports the PYPOWER built-in interior point solver. There is no parameter to swap solvers. External solver support would require the PowerModels.jl bridge (not tested here). Only the single PYPOWER IP solver was tested.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Generators | 1,727 (+ 1 ext_grid) |
| Cost curves | 2,485 polynomial |
| Converged | Yes |
| Objective | 2,437,763.82 |
| Total generation | 134,323.8 MW |
| LMP max | 20.738 |
| LMP min | 20.738 |
| LMP mean | 20.738 |
| LMPs extractable | Yes |

The uniform LMP values across all buses indicate that no line flow constraints are binding in this DC OPF solution (all LMPs equal the marginal generator cost).

### Solver comparison (requested but not possible)

| Solver | Status | Wall-clock (s) | Objective |
|--------|--------|----------------|-----------|
| PYPOWER IP | Converged | 8.229 | 2,437,763.82 |
| HiGHS | N/A -- not available | -- | -- |
| GLPK | N/A -- not available | -- | -- |

## Workarounds

- **What:** Only PYPOWER interior point solver tested; cannot compare across solvers
- **Why:** pandapower `rundcopp()` has no solver selection parameter; it exclusively uses PYPOWER's built-in interior point method
- **Durability:** blocking -- no workaround exists within pandapower's native OPF interface
- **Grade impact:** Cannot verify solver consistency (part of pass condition). Qualified pass because convergence is demonstrated but multi-solver comparison is impossible.

## Timing

- **Wall-clock:** 8.494 s (total), solve-only: 8.229 s
- **Peak memory:** 1,530.9 MB
- **CPU user time:** 75.19 s (reflects internal solver computation)

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c3_dcopf_scale.py`
