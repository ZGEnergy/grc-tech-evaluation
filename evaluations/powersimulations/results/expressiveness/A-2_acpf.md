---
test_id: A-2
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "fca7353e"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.0007
timing_source: measured
peak_memory_mb: 902.7
convergence_residual: null
convergence_iterations: null
loc: 213
solver: "PowerFlows.jl built-in Newton-Raphson"
timestamp: "2026-03-14T00:00:00Z"
---

# A-2: AC Power Flow (Newton-Raphson)

## Result: QUALIFIED PASS

## Approach

Used `PowerFlows.jl` v0.9.0 `solve_powerflow(ACPowerFlow(), sys)` on IEEE 39-bus.
`ACPowerFlow()` uses a built-in Newton-Raphson solver (not Ipopt). No external
optimizer configuration is needed. Flat-start initialization (Vm=1.0, Va=0.0) is the
default.

The result is a flat `Dict{String, DataFrame}` with `"bus_results"` and
`"flow_results"` keys (different nesting than DCPowerFlow -- see A-1 observations).

**Qualification:** PowerFlows.jl v0.9.0 does not expose Newton-Raphson iteration count
or convergence residual in its public return value. Convergence quality is verified
indirectly through non-trivial voltage profiles.

## Output

**Bus results** (39 buses):

| Metric | Value |
|--------|-------|
| Vm min | 0.982 pu |
| Vm max | 1.064 pu |
| Vm mean | 1.026 pu |
| Buses with Vm != 1.0 | 39/39 (100%) |
| Va min | -14.54 deg |
| Va max | 4.47 deg |
| Nonzero angles | 38/39 |

All 39 buses have voltage magnitudes differing from the flat-start value of 1.0 pu,
well exceeding the 95% threshold. This confirms a genuine AC solution was computed.

**Sample bus voltages:**

| Bus | Vm (pu) | Va (deg) | P_gen (MW) | P_load (MW) |
|-----|---------|---------|-----------|------------|
| 1 | 1.039 | -13.54 | 0.0 | 97.6 |
| 3 | 1.031 | -12.28 | 0.0 | 322.0 |
| 30 | 1.048 | 4.47 | 250.0 | 0.0 |
| 36 | 1.064 | 0.79 | 560.0 | 0.0 |

**Branch active power flows:**
- Range: -824.8 to 453.8 MW (from-to direction)
- All 46 branches carry nonzero P and Q flow

**Branch reactive power flows:**
- Range: -156.7 to 113.1 Mvar

**Losses:**
- Total active power losses: 43.64 MW (0.7% of total generation)
- Total reactive power losses: varies by branch (transformers show large Q through-flow)
- 42/46 branches have nonzero P losses

Note: The `P_losses` column in the flow results already computes `P_from + P_to` per
branch. Some transformer branches (e.g., bus-2-bus-30) show near-zero P losses but
large Q through-flow, as expected for ideal transformers in the AC model.

## Workarounds

- **What:** Cannot report NR iteration count or convergence residual
- **Why:** PowerFlows.jl v0.9.0's `solve_powerflow` returns only bus/flow DataFrames.
  The internal NR solver's iteration history and final mismatch are not exposed in the
  public API.
- **Durability:** stable -- the limitation is architectural (return type design), not a
  bug. A future PowerFlows release could add diagnostic metadata to the return Dict.
- **Grade impact:** Qualifies the pass. All required output quantities (V, theta, P, Q,
  losses) are present and physically reasonable. The only missing items are solver
  diagnostics (iteration count, residual), which are convergence-quality findings rather
  than functional failures.

## Timing

- **Wall-clock:** 0.0007 s (second run, after JIT warm-up)
- **Timing source:** measured
- **Peak memory:** 902.7 MB (Julia process RSS)
- **Solver iterations:** not reported by PowerFlows.jl
- **Convergence residual:** not reported by PowerFlows.jl
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a2_acpf.jl`

Key API call:
```julia
sys = System("case39.m")
pf_result = solve_powerflow(ACPowerFlow(), sys)
bus_df = pf_result["bus_results"]  # flat Dict, not nested like DC
flow_df = pf_result["flow_results"]
```

## Observations

- **convergence-quality:** PowerFlows.jl does not expose NR iteration count or residual.
  Convergence is inferred from non-trivial Vm profile (100% of buses differ from 1.0 pu).
- **api-friction:** AC and DC power flow return different Dict nesting structures (flat
  vs. nested under key "1").
- **doc-gaps:** PowerFlows.jl documentation does not describe return value structure in
  detail. Column names must be discovered empirically.
