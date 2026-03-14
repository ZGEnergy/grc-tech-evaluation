---
test_id: C-5
tool: gridcal
dimension: scalability
network: MEDIUM
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "0980f797"
wall_clock_seconds: 2.865
timing_source: measured
peak_memory_mb: 127.17
convergence_residual: 4.818e-07
convergence_iterations: 5
loc: 394
solver: NR (native) for ACPF, HiGHS for DCOPF
timestamp: 2026-03-13T00:00:00Z
---

# C-5: AC feasibility with progressive relaxation (0%, 10%, 20%) on MEDIUM

## Result: PASS

## Approach

1. Solved DC OPF on ACTIVSg 10000-bus network using HiGHS (8.37 s)
2. Fixed generator dispatch to DC OPF values in the same model context
3. Ran ACPF with flat start using Newton-Raphson (converged in 5 iterations)
4. Assessed voltage and thermal violations at three relaxation levels

The ACPF converged on the first attempt (flat start) — no DC warm start or relaxed tolerance was needed.

## Output

### DC OPF Dispatch

| Metric | Value |
|--------|-------|
| DCOPF converged | Yes |
| DCOPF solve time | 8.37 s |
| Total dispatch | 150,916.88 MW |

### ACPF Convergence

| Metric | Value |
|--------|-------|
| Flat start converged | Yes |
| NR iterations | 5 |
| Convergence residual | 4.818e-07 |
| ACPF solve time | 2.865 s |
| Vm range | [0.927, 1.089] pu |
| Vm mean | 1.022 pu |
| Total losses | 2,891.3 MW |

### Progressive Relaxation Assessment

| Level | V bounds (pu) | Voltage violations | Thermal violations | Feasible |
|-------|--------------|-------------------|--------------------|----------|
| 0% | [0.950, 1.050] | 132 | 18 | No |
| 10% | [0.945, 1.055] | 83 | 18 | No |
| 20% | [0.940, 1.060] | 46 | 18 | No |

**First feasible relaxation level:** None — infeasible at all levels due to persistent thermal violations.

The 18 thermal violations remain constant across all relaxation levels because they are branch flow violations (loading > 100%), not voltage violations. The most severe overload is branch 20453_20471_1 at 1586.9% loading. Voltage violations decrease from 132 to 46 as the bounds widen.

The DC OPF dispatch creates an AC operating point with significant thermal violations, indicating that the DCOPF solution is not AC-feasible. This is expected for a large network where DC and AC solutions can diverge significantly.

### Sample Violations (0% level)

**Voltage (over):** TACOMA 1 1 (1.060 pu), LAKEWOOD 1 1 (1.059 pu), TACOMA 6 2 (1.064 pu)

**Thermal:** 20453_20471_1 (1586.9%), 23387_23449_1 (752.8%), 20461_20471_1 (507.2%)

## Workarounds

None required.

## Timing

- **Wall-clock:** 2.865 s (ACPF solve only)
- **Timing source:** measured
- **Peak memory:** 127.17 MB (tracemalloc, includes DCOPF + ACPF)
- **Solver iterations:** 5 (NR)
- **Convergence residual:** 4.818e-07
- **DCOPF time:** 8.37 s
- **Total script time:** 17.28 s

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c5_ac_feasibility_progressive_medium.py`
