---
test_id: A-1
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: d473818c
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.003
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 250
solver: null
timestamp: 2026-03-24T12:00:00Z
---

# A-1: DC Power Flow (DCPF)

## Result: QUALIFIED PASS

## Approach

Loaded `case39.m` using `PowerModels.parse_file`. Solved DCPF using `PowerModels.compute_dc_pf(data)`, which bypasses JuMP and solves the linear system directly via Julia's backslash operator.

**API discovery:** `compute_dc_pf` returns `termination_status` as a `Bool` (not a JuMP `TerminationStatusCode`). The result dict's `"solution"` contains only `"bus"` (voltage angles `va`) -- no `"branch"` key. Branch flows must be computed manually from the bus angle solution.

**Workaround for branch flows:** Computed DC power flow line flows from angles using:

```julia
pf_pu = (va_from - va_to - shift) / (br_x * tap)
```

This is the standard DC PF formula using only public fields from the data dict (`br_x`, `tap`, `shift`). Results match expected values for IEEE 39-bus.

Nodal injections were derived directly from `data["gen"]` (pg values, in per-unit) and `data["load"]` (pd values).

## Output

| Metric | Value |
|--------|-------|
| Buses | 39 |
| Branches | 46 |
| Non-zero voltage angles | 38 / 39 (slack bus = 0 by definition) |
| Non-zero branch flows | 46 / 46 |
| Angle range | -0.219 to +0.109 rad (-12.6 to +6.3 deg) |
| Flow range (MW) | -518 to +432 MW |

Bus voltage angle sample (first 10):

| Bus | Va (rad) | Va (deg) |
|-----|----------|----------|
| 1 | -0.2056 | -11.78 |
| 2 | -0.1324 | -7.59 |
| 3 | -0.1814 | -10.39 |
| 4 | -0.1925 | -11.03 |
| 5 | -0.1697 | -9.72 |
| 6 | -0.1563 | -8.95 |
| 7 | -0.1978 | -11.33 |
| 8 | -0.2078 | -11.90 |
| 9 | -0.2192 | -12.56 |
| 10 | -0.1134 | -6.50 |

Branch flow sample (from angle-based calculation):

| Branch | From-To | Flow (MW) | Limit (MW) |
|--------|---------|-----------|-----------|
| 1 | 1-2 | -178.0 | 600.0 |
| 2 | 1-39 | 79.3 | 1000.0 |
| 3 | 2-3 | 323.9 | 500.0 |
| 4 | 2-25 | -412.8 | 500.0 |
| 5 | 2-30 | -243.9 | 900.0 |

## Workarounds

- **What:** `compute_dc_pf` does not populate `result["solution"]["branch"]`. Branch flows must be computed manually from bus voltage angles using the DC power flow formula `(va_from - va_to - shift) / (br_x * tap)`.
- **Why:** The `compute_dc_pf` function is a lightweight linear-algebra solver that only writes bus angles to the solution dict. It does not post-process branch flows.
- **Durability:** stable -- uses only documented public data dict fields (`br_x`, `tap`, `shift`, `f_bus`, `t_bus`). The DC PF formula is mathematically deterministic from these fields.
- **Grade impact:** Minor. The data is accessible, just requires ~10 lines of post-processing. Does not prevent extracting correct branch flows.

**Note on `termination_status`:** Returns a `Bool` (not a JuMP enum), which is undocumented in the official docs. Code must handle `result["termination_status"] == true` rather than checking for `"OPTIMAL"` or `"LOCALLY_SOLVED"`. This is an API inconsistency between `compute_dc_pf` (non-JuMP) and `solve_dc_opf` (JuMP-based). [tool-specific]

## Timing

- **Wall-clock:** 0.003s (warm run; first invocation ~0.50s including JIT compilation)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** N/A (direct linear algebra solve, no iterative solver)
- **Convergence residual:** N/A (exact linear solve)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a1_dcpf_tiny.jl`

Key API calls:

```julia
data = PowerModels.parse_file("../../data/networks/case39.m")
result = PowerModels.compute_dc_pf(data)

# termination_status is Bool, not JuMP enum
converged = result["termination_status"] == true

# Bus angles in solution
va = result["solution"]["bus"][bus_id]["va"]  # radians

# Branch flows NOT in solution -- compute manually
pf_pu = (va_from - va_to - shift) / (br_x * tap)
```
