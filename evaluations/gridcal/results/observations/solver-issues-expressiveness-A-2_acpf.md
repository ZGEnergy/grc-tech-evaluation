---
tag: solver-issues
source_dimension: expressiveness
source_test: A-2
tool: gridcal
severity: medium
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: GridCal has no Ipopt integration for AC power flow

## Finding

GridCal (VeraGridEngine v5.6.28) does not integrate Ipopt or any external NLP solver for
AC power flow. It uses its own native Newton-Raphson implementation (`SolverType.NR`). The
eval-config specifies Ipopt as the ACPF solver, but this is not applicable to GridCal.

## Context

During A-2 (ACPF on TINY), the test was configured to use `SolverType.NR` instead of Ipopt.
The native NR solver converged in 4 iterations with a residual of 3.32e-11 -- well within
tolerance. The solver is performant and accurate on the TINY network.

GridCal's AC OPF (nonlinear OPF) also uses a custom interior-point solver rather than Ipopt,
meaning Ipopt is absent from the entire tool.

## Implications

- For scalability assessment: AC power flow convergence behavior on larger networks (SMALL,
  MEDIUM) should be tested with GridCal's native NR. Convergence properties may differ from
  Ipopt-based tools.
- For accessibility assessment: The absence of Ipopt integration means users cannot leverage
  Ipopt's extensive documentation, tuning options, or warm-start features for difficult AC
  convergence cases. However, GridCal provides 14+ alternative solver algorithms (HELM,
  Fast Decoupled, Levenberg-Marquardt, etc.) as fallbacks.
- Cross-tool comparison of AC solver performance is not solver-controlled for GridCal vs.
  tools that use Ipopt.
