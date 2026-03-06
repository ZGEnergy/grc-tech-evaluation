---
test_id: P2-2
tool: powermodels
dimension: p2_readiness
status: pass
timestamp: 2026-03-05
---

# P2-2: Piecewise Linear Cost Functions

## Finding

PowerModels.jl fully supports piecewise linear (PWL) cost functions for generators and DC lines, using the lambda-model formulation. Both convex and non-convex PWL costs are handled -- convex costs use standard LP/QP constraints, while non-convex costs use SOS2 (Special Ordered Sets of type 2) constraints.

## Evidence

**PWL cost support** (from documentation at <https://lanl-ansi.github.io/PowerModels.jl/stable/objective>/):

- Cost functions are provided as either univariate polynomials or piecewise linear functions
- PWL costs follow MATPOWER data format conventions (model=1 in gen cost data)
- Costs are defined as a sequence of (power, cost) points: $(P_k, C_k)$ for $k \in \{1, \dots, K\}$ segments

**Formulation**: The lambda-model (also called the convex-combination or SOS2 formulation):
- Reference: "The Impacts of Convex Piecewise Linear Cost Formulations on AC Optimal Power Flow" (<https://arxiv.org/abs/2005.14087>)
- Implementation in `src/core/objective.jl`

**Non-convex cost handling**:
- SOS2 constraints are automatically applied when PWL data is non-convex
- SOS2 ensures at most two consecutive lambda variables are non-zero, correctly modeling non-convex piecewise linear functions
- Requires a solver supporting SOS2 constraints (most MIP solvers: HiGHS, SCIP, GLPK, Gurobi)

**Data preprocessing**:
- `calc_pwl_points()` preprocesses raw PWL data to ensure:
  - First and last points are strictly outside the Pmin-to-Pmax range
  - Pmin and Pmax occur in the first and last line segments

**Related issues**:
- Issue #287 "Non-Convex PWL Cost Functions" -- resolved, SOS2 support implemented
- Issue #316 "DC line model breaks PWL generator cost format" -- resolved

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/objective/,> <https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/core/objective.jl,> issues #287, #316

## Implications

PWL cost support is comprehensive and handles both the common convex case and the more challenging non-convex case via SOS2. The MATPOWER-compatible data format means PWL costs from existing MATPOWER case files work directly. For Phase 2, this capability is ready for use with real generator cost curves. The lambda-model formulation is mathematically well-characterized and widely used in power systems optimization literature.
