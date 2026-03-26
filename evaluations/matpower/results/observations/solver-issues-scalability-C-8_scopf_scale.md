---
tag: solver-issues
source_dimension: scalability
source_test: C-8
tool: matpower
severity: high
timestamp: 2026-03-24T00:00:00Z
---

# Observation: MIPS and GLPK fail with LODF-based user constraints on MEDIUM (10k-bus)

## Finding

Both MIPS and GLPK solvers fail when LODF-based post-contingency flow constraints are injected via `mpc.A/l/u` on the ACTIVSg10k network. MIPS encounters numerical singularity (rcond ~5e-17) with as few as 15 user constraints. GLPK either reports infeasibility or times out.

## Context

The Benders SCOPF approach works correctly on iteration 1 (unconstrained DC OPF solves, violations detected, constraints built). The failure occurs on iteration 2 when the augmented problem is solved. The constraint coefficients are dense row vectors derived from `Bf + LODF * Bf`, which are numerically valid on smaller networks (case39 SCOPF succeeds through multiple Benders iterations).

The 10k-bus network creates a KKT system that exceeds MIPS's numerical precision when user constraints are added. This is consistent with the MIPS solver being a pure MATLAB/Octave implementation without sophisticated preconditioning or scaling. A commercial solver (e.g., CPLEX, Gurobi) or HiGHS (unavailable in Octave) might handle this, but cannot be tested in the current environment.

## Implications

MATPOWER's SCOPF-via-user-constraints approach does not scale to MEDIUM (10k-bus) with the available open-source solvers in Octave. This is a [mixed: tool lacks native SCOPF, and available solvers cannot handle the manual constraint injection at scale] limitation. The tool's extensibility mechanism (`mpc.A/l/u`) is correctly designed but is limited by solver numerical capabilities at this scale.

This finding affects the scalability grade for SCOPF capability. The API building blocks (`makePTDF`, `makeLODF`, `mpc.A/l/u`) exist and work, but the end-to-end SCOPF workflow cannot complete at MEDIUM scale.
