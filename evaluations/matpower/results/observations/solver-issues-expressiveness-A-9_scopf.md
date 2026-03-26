---
tag: solver-issues
source_dimension: expressiveness
source_test: A-9
tool: matpower
severity: high
timestamp: 2026-03-24T00:00:00Z
---

# Observation: MIPS solver numerical instability with user constraints; 70%-derated case39 is N-1 infeasible

## Finding

MATPOWER's SCOPF attempt reveals two compounding issues: (1) the 70%-derated case39 network is inherently N-1 infeasible, making the SCOPF problem unsolvable regardless of solver choice, and (2) MIPS encounters numerical singularity when user constraints (mpc.A/l/u) are combined with quadratic costs. GLPK handles LP-only and also reports infeasibility when N-1 constraints are added. The Benders iteration completed 2 iterations before detecting infeasibility.

## Context

Test A-9 (SCOPF) required injecting post-contingency flow constraints via `mpc.A/l/u`. Benders iteration 1 identified 83 post-contingency violations (worst: 403.1% overload on branch 6->11 under outage of branch 33). At iteration 2, both GLPK (with linear costs) and MIPS (with quadratic costs) report infeasibility. HiGHS was unavailable in the devcontainer; MIPS is the only available QP solver.

## Implications

- **Scalability (C-8):** SCOPF feasibility depends on network configuration, not just solver capability. A less aggressively derated network would be needed to demonstrate SCOPF capability.
- **Extensibility (B-1):** The `mpc.A/l/u` user constraint interface works mechanically (constraints are injected), but the MIPS solver struggles numerically with large constraint sets even when the problem is feasible.
- **Accessibility (D-4):** MIPS reports "matrix singular to machine precision" without indicating root cause. The infeasibility diagnosis path is clearer with GLPK.
