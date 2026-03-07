---
test_id: A-9
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.61
peak_memory_mb: null
loc: 175
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# A-9: Solve DC OPF with N-1 contingency flow constraints embedded in optimization

## Result: FAIL

## Approach

pandapower has no native SCOPF. The test explored whether N-1 contingency constraints could be embedded in the optimization through the PYPOWER `userfcn` callback system.

### Steps Taken

1. Loaded IEEE 39-bus network (39 buses, 46 branches = 35 lines + 11 trafos).
2. Solved base DC OPF for comparison (objective: 41,263.94).
3. Computed PTDF matrix using `pandapower.pypower.makePTDF` (46x39 matrix).
4. Computed LODF matrix from PTDF (46x46 matrix).
5. Verified `add_userfcn` is importable from `pandapower.pypower`.
6. Verified `pypower.opf` is importable.
7. Assessed feasibility of injecting contingency constraints.

### Assessment

The theoretical path to SCOPF via PYPOWER `userfcn` exists but is not viable:

1. **pandapower does not expose `userfcn` to `rundcopp()`** -- there is no parameter to pass callback functions or custom constraints.
2. **Using PYPOWER `opf()` directly** would bypass pandapower entirely, requiring manual construction of the PYPOWER `ppc` structure, running the solver, and mapping results back to pandapower DataFrames.
3. **The `userfcn` API** for adding linear constraints (`A*x <= b`) requires understanding PYPOWER's internal variable ordering (generator indices, bus angle indices in the optimization vector).
4. **No documentation exists** for this path in pandapower's context.

### What pandapower CAN do

- **Contingency screening:** `pandapower.contingency.run_contingency` runs power flow for each N-1 contingency and reports violations. This is post-hoc analysis, not embedded optimization.
- **PTDF/LODF computation:** The matrices needed for SCOPF constraint formulation can be computed. This is a building block but not sufficient.

## Output

| Metric | Value |
|--------|-------|
| Base DC OPF converged | Yes |
| Base DC OPF objective | 41,263.94 |
| Contingency set size | 46 branches |
| PTDF matrix shape | 46 x 39 |
| LODF matrix computed | Yes |
| Branches with ratings | 46 |
| PYPOWER userfcn importable | Yes |
| SCOPF achievable | No |

## Workarounds

- **What:** SCOPF via PYPOWER `userfcn` callbacks is theoretically possible but requires completely bypassing pandapower's API.
- **Why:** pandapower has no SCOPF formulation and does not expose the PYPOWER `userfcn` interface through its `rundcopp()` function.
- **Durability:** blocking -- requires bypassing pandapower entirely, manually constructing internal data structures, and deep knowledge of PYPOWER variable ordering. This is tantamount to using a different tool.
- **Grade impact:** Complete absence of SCOPF capability. The building blocks exist (PTDF, LODF, contingency screening) but cannot be assembled into an optimization-embedded solution through pandapower's API.

An iterative cutting-plane approach (solve OPF, check contingencies, add violated constraints, re-solve) was considered but does NOT meet the pass condition, which requires contingency constraints to be part of the optimization, not checked post-hoc.

## Timing

- **Wall-clock:** 0.61 s (base OPF + PTDF/LODF computation + capability checks)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a9_scopf.py`
