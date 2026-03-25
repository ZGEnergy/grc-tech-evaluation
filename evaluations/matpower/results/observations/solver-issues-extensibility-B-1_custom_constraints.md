---
tag: solver-issues
source_dimension: extensibility
source_test: B-1
tool: matpower
severity: high
timestamp: 2026-03-24T00:00:00Z
---

# Observation: MIPS solver fails with user constraints (mpc.A) on DC OPF

## Finding

MATPOWER's built-in MIPS solver fails to converge when user constraints are injected via the documented `mpc.A/l/u` mechanism, even for QP problems with quadratic costs. Switching to GLPK resolves the issue but requires linearizing quadratic costs to piecewise linear (GLPK handles LP only). HiGHS (LP/QP) is not available in the Octave devcontainer.

## Context

B-1 tested custom constraint injection for DC OPF using `mpc.A`, `mpc.l`, `mpc.u` -- the documented public API for adding linear constraints. The constraint limited generator output. MIPS failed to converge with user constraints. Switching to GLPK (with PWL-linearized costs) resolved the issue for both binding and non-binding cases. The same MIPS limitation was observed in A-9 (SCOPF with LODF-based N-1 constraints).

## Implications

This is a significant solver limitation for the scalability dimension (C-8 SCOPF at scale will likely face the same issue). The MIPS limitation with user constraints means:
1. Custom constraints are practically limited to LP formulations with GLPK in the Octave environment
2. QP formulations with user constraints require HiGHS or a commercial solver, neither available in the devcontainer
3. Any test requiring SCOPF-style constraint injection at scale will need a non-MIPS solver
