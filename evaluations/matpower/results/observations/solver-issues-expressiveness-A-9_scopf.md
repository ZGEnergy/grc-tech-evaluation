---
tag: solver-issues
source_dimension: expressiveness
source_test: A-9
tool: matpower
severity: high
timestamp: 2026-03-13T00:00:00Z
---

# Observation: MIPS solver numerical instability with user constraints + quadratic costs

## Finding

MATPOWER's built-in MIPS solver encounters numerical singularity when user constraints (mpc.A/l/u) are combined with quadratic cost functions in DC OPF. Even a single user constraint causes convergence failure. With linear costs, up to 5 user constraints work, but the full N-1 constraint set still fails.

## Context

Test A-9 (SCOPF) required injecting post-contingency flow constraints into the DC OPF via MATPOWER's documented `mpc.A/l/u` user constraint interface. The constraint formulation is mathematically correct (LODF-based flow coefficients on the Va variable subvector). HiGHS was unavailable in the evaluation environment; MIPS is the only available solver for QP problems.

## Implications

This finding affects multiple evaluation dimensions:
- **Scalability (C-8):** SCOPF at MEDIUM scale will fail with MIPS. Solver swap to HiGHS/GLPK is needed.
- **Extensibility (B-1):** Custom constraint injection via mpc.A works for simple cases but breaks under numerical stress.
- **Accessibility (D-4):** The MIPS singularity warning message ("matrix singular to machine precision") does not indicate the root cause or suggest remediation.
