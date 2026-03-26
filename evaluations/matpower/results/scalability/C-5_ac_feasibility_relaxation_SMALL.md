---
test_id: C-5
tool: matpower
dimension: scalability
network: SMALL
protocol_version: "v11"
skill_version: v2
test_hash: 15688fba
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.168
timing_source: measured
peak_memory_mb: 1.7
convergence_residual: 7.358e-12
convergence_iterations: 5
loc: 196
solver: NR
timestamp: 2026-03-14T00:00:00Z
---

# C-5: AC feasibility with progressive constraint relaxation on SMALL

## Result: PASS

## Approach

Ran ACPF (Newton-Raphson) on ACTIVSg 2000-bus network at three progressive relaxation
levels: 0%, 10%, and 20%. At each level, voltage limits were widened symmetrically and
branch flow limits were increased by the relaxation percentage. The convergence protocol
was applied: flat start first, then DC warm start fallback, then relaxed tolerance.

## Output

All three relaxation levels converged from flat start in 5 NR iterations. No DC warm
start or tolerance relaxation was needed at any level.

| Relaxation | Converged | Start Method | Wall Clock | NR Iters | Final Residual |
|------------|-----------|-------------|------------|----------|----------------|
| 0% | Yes | flat | 0.168 s | 5 | 7.358e-12 |
| 10% | Yes | flat | 0.109 s | 5 | 7.358e-12 |
| 20% | Yes | flat | 0.105 s | 5 | 7.358e-12 |

### Voltage and Thermal Violations (vs Original Limits)

| Relaxation | VM Range (pu) | V Over | V Under | Thermal Violations |
|------------|---------------|--------|---------|-------------------|
| 0% | [0.9723, 1.0400] | 0 | 0 | 0 / 3206 |
| 10% | [0.9723, 1.0400] | 0 | 0 | 0 / 3206 |
| 20% | [0.9723, 1.0400] | 0 | 0 | 0 / 3206 |

The AC solution is well within the original voltage and thermal limits at all relaxation
levels. The solution is identical across all three levels because the base case has no
binding constraints — the relaxation has no effect on the solution.

### System Summary

| Metric | Value |
|--------|-------|
| Total generation | 68,740.87 MW |
| Total load | 67,109.21 MW |
| Total P losses | 1,631.66 MW (2.37%) |
| Relaxation level achieved | 0% (no relaxation needed) |

## Workarounds

None required. The ACTIVSg 2000-bus network converges robustly from flat start with
no constraint violations, making progressive relaxation unnecessary. This is a strong
result for MATPOWER's Newton-Raphson solver on a SMALL-scale network.

## Timing

- **Wall-clock (0% relaxation):** 0.168 s
- **Timing source:** measured
- **Peak memory:** 1.7 MB
- **Solver iterations:** 5 (NR, consistent across all levels)
- **Convergence residual:** 7.358e-12
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/scalability/test_c5_ac_feasibility_relaxation_SMALL.m`
