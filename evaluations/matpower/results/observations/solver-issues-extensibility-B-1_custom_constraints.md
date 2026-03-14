---
tag: solver-issues
source_dimension: extensibility
source_test: B-1
tool: matpower
severity: high
timestamp: 2026-03-13T00:00:00Z
---

# Observation: MIPS solver fails with user constraints (mpc.A) on DC OPF

## Finding

MATPOWER's built-in MIPS solver produces cascading numerical singularity errors when user constraints are injected via the documented `mpc.A/l/u` mechanism, even for LP problems (linear costs). The rcond value degrades from ~1e-17 to ~1e-35 across iterations, preventing convergence. This affects both binding and non-binding constraints with MIPS, but only binding constraints with GLPK.

## Context

B-1 tested custom constraint injection for DC OPF using `mpc.A`, `mpc.l`, `mpc.u` — the documented public API for adding linear constraints. The constraint limited combined generator output. MIPS failed for all constraint tightness levels (50%-90%). Switching to GLPK (LP only) resolved the issue for non-degenerate cases. The same MIPS singularity was observed in A-9 (SCOPF with LODF-based N-1 constraints).

## Implications

This is a significant solver limitation for the scalability dimension (C-8 SCOPF at scale will likely face the same issue). The MIPS singularity with user constraints means:
1. Custom constraints are practically limited to LP formulations with GLPK in the Octave environment
2. QP formulations with user constraints require HiGHS or a commercial solver, neither available in the devcontainer
3. Any test requiring SCOPF-style constraint injection at scale will need a non-MIPS solver
