---
test_id: P2-2
tool: matpower
dimension: p2_readiness
network: N/A
protocol_version: v11
skill_version: v2
test_hash: "f7b76d2b"
status: informational
workaround_class: null
timestamp: 2026-03-24T12:00:00Z
---

# P2-2: Piecewise-Linear Cost Curve Support

## Capability: YES -- native first-class support

## Formulation Type

MATPOWER natively supports piecewise-linear (PWL) cost curves via the `gencost` matrix with
`MODEL = 1` (the `PW_LINEAR` constant from `idx_cost`). The `gencost` row format is:

```
[1  startup  shutdown  n  p1 f1  p2 f2  ...  pn fn]
```

where `n` is the number of breakpoints and each `(pi, fi)` pair specifies a power (MW) and
cost ($) breakpoint. The OPF linearizes this as a set of linear cost segments with auxiliary
variables and constraints -- the standard LP/QP formulation for PWL objectives.

Both `MODEL = 1` (PWL) and `MODEL = 2` (polynomial) cost types can coexist in the same case
(different generators can use different cost model types).

## Solver Compatibility

PWL costs are supported by all OPF solver backends:

| Solver | DC OPF (PWL) | AC OPF (PWL) |
|--------|-------------|-------------|
| MIPS (built-in) | yes | yes |
| GLPK | yes (LP only) | no |
| HiGHS | yes | no |
| Gurobi | yes | yes |
| CPLEX | yes | yes |
| MOSEK | yes | yes |
| IPOPT | yes | yes |
| Knitro | yes | yes |

The DC OPF with PWL costs reduces to an LP (or LP with helper variables), so any LP solver
works. AC OPF with PWL costs requires an NLP solver that handles the auxiliary linearization
variables.

## Functional Probe

Verified on IEEE 9-bus case with 3-segment PWL costs for all generators:

**DC OPF:** Converged successfully. Generators dispatched at breakpoints as expected
(130.00, 155.00, 30.00 MW). Total cost: $5,700.00.

**AC OPF:** Converged successfully with MIPS solver. Generators dispatched at
(130.00, 104.47, 83.01 MW). Total cost: $5,749.57 (higher than DC due to losses
and voltage constraints).

## Limitations

- PWL costs must be convex (monotonically increasing marginal cost) for the OPF to
  guarantee a global optimum. Non-convex PWL costs will still run but may find local optima.
- The number of breakpoints is unlimited but adds auxiliary variables and constraints to the
  optimization model (one helper variable per segment per generator).
- MATPOWER 8.0 release notes document a bug fix for "AC OPF initialization with
  piecewise-linear costs," indicating this edge case was previously problematic but is now
  resolved in 8.1.

## Sources

- `/workspace/evaluations/matpower/matpower8.1/lib/idx_cost.m` -- cost matrix format constants
- `/workspace/evaluations/matpower/matpower8.1/lib/caseformat.m` -- gencost specification
- MATPOWER User's Manual 8.1, Section 6 (Optimal Power Flow) -- PWL cost formulation
- Functional probe run in devcontainer on 2026-03-24
