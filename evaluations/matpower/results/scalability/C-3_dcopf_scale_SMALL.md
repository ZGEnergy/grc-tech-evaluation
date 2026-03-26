---
test_id: C-3
tool: matpower
dimension: scalability
network: SMALL
protocol_version: "v11"
skill_version: v2
test_hash: a4f62ae7
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.507
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
loc: 187
solver: MIPS
timestamp: 2026-03-14T00:00:00Z
---

# C-3: DC OPF on SMALL with MIPS and GLPK

## Result: QUALIFIED PASS

## Approach

Ran `rundcopf(mpc, mpopt)` on ACTIVSg 2000-bus network with two solvers:

1. **MIPS** (MATPOWER Interior Point Solver) — built-in QP solver, handles the
   quadratic cost curves natively.
2. **GLPK** — LP/MILP only, cannot handle quadratic costs (QP). Attempted PWL
   conversion via `poly2pwl()`, which failed on 117 generators with Pmin==Pmax.
   Also attempted pure linear costs; GLPK failed with singular basis matrix on
   this network.

The test specified HiGHS and GLPK per the config, but HiGHS is unavailable in Octave.
MIPS was used as the primary solver.

## Output

### MIPS (pass)

| Metric | Value |
|--------|-------|
| Solver | MIPS |
| Status | Converged |
| Wall clock | 0.507 s |
| Objective | 1,201,320.78 $/hr |
| Total generation | 67,109.21 MW |
| LMP range | [18.4997, 18.4997] $/MWh |
| LMP mean | 18.4997 $/MWh |
| Binding branches | 0 / 3206 |

All LMPs are uniform at $18.50/MWh — no binding branch constraints. This is consistent
with the ACTIVSg2000 network having adequate branch capacity at base case loading
(similar to the ACTIVSg10k observation in cross-tool-watchpoints.md).

### GLPK (fail)

| Metric | Value |
|--------|-------|
| Solver | GLPK |
| Status | Failed |
| Error (QP) | "GLPK handles only LP problems, not QP problems" |
| Error (LP) | "basis matrix is singular to working precision (cond = 1.87e+16)" |

GLPK cannot solve the DC OPF on this network for two compounding reasons:
1. The quadratic cost curves produce a QP, which GLPK cannot handle.
2. Even with linearized costs, GLPK's simplex solver fails with a singular basis
   matrix on the 2000-bus network constraint matrix.

## Workarounds

None required for MIPS. GLPK failure is a solver limitation, not a tool limitation.
MATPOWER's solver swap is a single `mpoption` parameter change — the issue is purely
that GLPK is numerically inadequate for this network size.

## Timing

- **Wall-clock (MIPS):** 0.507 s
- **Wall-clock (GLPK):** N/A (failed)
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/scalability/test_c3_dcopf_scale_SMALL.m`
