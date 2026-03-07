---
test_id: C-7
tool: matpower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 11.86
peak_memory_mb: null
loc: 55
timestamp: "2026-03-06T16:00:00Z"
---

# C-7: Solver Swap (MEDIUM, ACTIVSg 10k)

## Result: PASS

## Approach

Repeat DC OPF on MEDIUM with each available open-source solver, changing only the `mpopt` parameter. Same `mpc` struct, same `rundcopf()` call.

## Output

| Solver | Converged | Objective ($/hr) | Time (s) | Notes |
|--------|-----------|-------------------|----------|-------|
| **MIPS** | Yes | 2,436,631.23 | **9.28s** | Native QP solver, quadratic costs |
| **GLPK** | No | N/A | 0.11s | LP-only — rejects QP problem |

### Solver Swap Mechanism

```matlab
% Only the solver option changes:
mpopt = mpoption(mpopt, 'opf.dc.solver', 'MIPS');   % or 'GLPK'
results = rundcopf(mpc, mpopt);
```

- **Reformulation required:** No. MATPOWER handles internal reformulation automatically.
- **API change:** Single parameter (`opf.dc.solver` string).
- GLPK cannot solve QP problems (quadratic generator costs). It requires PWL cost conversion first (as demonstrated in C-3). This is a solver limitation, not a MATPOWER limitation — MATPOWER's dispatch layer correctly detects the incompatibility.

## Timing

- MIPS: 9.28s (interior point, handles QP natively)
- GLPK: rejected immediately (LP-only, 0.11s)
- Total: 11.86s

## Notes

- Solver swap is a single parameter change — no reformulation, no data restructuring
- GLPK's LP-only limitation means PWL cost conversion is needed for GLPK (see C-3)
- MIPS is the only solver that handles the native quadratic cost formulation on Octave
- HiGHS (available in MATPOWER 8.1) would handle QP natively but requires MEX compilation

## Test Script

`evaluations/matpower/tests/scalability/test_c7_solver_swap_medium.m`
