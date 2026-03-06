---
test_id: P2-2
tool: pypsa
dimension: p2_readiness
status: informational
timestamp: 2026-03-05
---

# P2-2: Piecewise-Linear Cost Curve Support

## Finding

PyPSA does not currently support native piecewise-linear (PWL) cost curves in released versions (v1.1.2). However, an active pull request (#1603) adds PWL marginal_cost and capital_cost support, and marginal_cost can already be set per-snapshot as a time series.

## Evidence

**Current capabilities (v1.1.2):**

Generator cost-related attributes:
- `marginal_cost` -- scalar or time-varying (per-snapshot via `n.generators_t.marginal_cost`)
- `marginal_cost_quadratic` -- quadratic cost coefficient
- `capital_cost` -- investment cost (scalar)
- `start_up_cost`, `shut_down_cost`, `stand_by_cost` -- unit commitment costs

**Per-snapshot marginal cost (existing workaround):**
Setting `n.generators_t.marginal_cost` allows different marginal costs per time step, but this is not the same as a piecewise-linear function of output level. It varies cost by time, not by dispatch quantity.

Open PR #1603: **"feat: Add piecewise linear costs and constraints"**

- Status: Open (created 2026-03-04)
- Closes issue #1473
- Adds PWL `marginal_cost` and `capital_cost` on Generators, StorageUnits, Stores, and Links
- Uses linear tangent constraints (not SOS2 yet -- SOS2 fallback is on the TODO list)
- API example from PR:

  ```python
  # Piecewise marginal cost (per-unit x-axis, fixed p_nom required)
  n.add("Generator", "gen", bus="bus0", p_nom=100,
        marginal_cost={0.0: 40.0, 0.5: 60.0, 1.0: 70.0})
  ```

- Open TODOs in the PR:
  - PWL efficiencies and rates (not yet implemented)
  - Convexity checking with SOS2 fallback
  - Import/export support for segment data

**SOS2 constraints:**
- Issue #431 ("Endogenous technological learning with SOS2 constraints") was closed on 2026-03-04, suggesting SOS2 infrastructure is being built
- linopy supports SOS constraints via the underlying solver (HiGHS supports SOS2)

## Implications

PWL cost curves are not available in the current stable release but are under active development with a concrete PR. For Phase 2:
- The per-snapshot marginal_cost workaround can approximate step-function bid curves by segment
- Full PWL support will likely land in an upcoming release (v1.2.0 or similar)
- The quadratic cost coefficient (`marginal_cost_quadratic`) provides convex cost curve support as an alternative
- SOS2-based PWL modeling is feasible via linopy's constraint system even without native PyPSA support
