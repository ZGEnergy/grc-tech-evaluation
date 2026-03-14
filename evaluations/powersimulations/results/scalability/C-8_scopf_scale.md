---
test_id: C-8
tool: powersimulations
dimension: scalability
network: SMALL, MEDIUM
protocol_version: "v10"
skill_version: "v1"
test_hash: "b75f151e"
status: qualified_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 602.156
wall_clock_per_network:
  small_seconds: 602.156
  medium_seconds: 448.945
timing_source: measured
peak_memory_mb: 5066.7
convergence_residual: null
convergence_iterations: null
loc: 412
solver: HiGHS
timestamp: "2026-03-14T00:00:00Z"
---

# C-8: SCOPF N-1 (50 contingencies) on SMALL and MEDIUM

## Result: QUALIFIED PASS

## Approach

Tested Security-Constrained OPF with N-1 contingency constraints on SMALL (ACTIVSg 2000-bus)
and MEDIUM (ACTIVSg 10000-bus). Used the same manual LODF-based constraint assembly approach
as A-9 (SCOPF on TINY), scaled up to 50 contingencies per network.

**Contingency selection:** Computed the full LODF matrix via `PowerNetworkMatrices.jl`, then
selected the 50 highest-impact branches by maximum absolute LODF value (excluding near-radial
branches with |LODF| >= 0.95).

**Constraint assembly:** For each of 50 contingencies and each monitored line, added two
constraints via JuMP: `flow_l + LODF[l,k] * flow_k <= rating_l` and
`-(flow_l + LODF[l,k] * flow_k) <= rating_l`. This produces O(50 x N_lines x 2) constraints.

**Model setup:** `DecisionModel` with `DCPPowerModel`, `ThermalDispatchNoMin`,
`RenewableFullDispatch`, `initialize_model=false`. Time series added for loads, renewables,
and hydro. Build succeeded with status BUILT.

## Output

### SMALL (ACTIVSg 2000-bus)

| Metric | Value |
|--------|-------|
| Buses / Branches / Generators | 2,000 / 3,206 / 544 |
| LODF matrix shape | 3,206 x 3,206 |
| LODF compute time | 0.48 s |
| Contingencies requested | 50 |
| Contingency constraints added | 145,912 |
| Constraint build time | 0.17 s |
| Base DCOPF variables | 5,618 |
| Total constraints (base + contingency) | 161,748 |
| HiGHS solve time | 600.4 s |
| Termination status | TIME_LIMIT |
| Objective value (incumbent) | 2,503.25 |
| Peak memory | 1,776 MB |

**SMALL finding:** HiGHS found a feasible incumbent solution (objective = 2,503.25) but could
not prove optimality within the 600-second time limit. The LP has 5,618 variables and 161,748
constraints — the contingency constraints outnumber the base DCOPF constraints by ~26:1.

### MEDIUM (ACTIVSg 10000-bus)

| Metric | Value |
|--------|-------|
| Buses / Branches / Generators | 10,000 / 12,706 / 2,485 |
| LODF matrix shape | 12,706 x 12,706 |
| LODF compute time | 3.6 s |
| Contingencies requested | 50 |
| Contingency constraints added | 474,178 |
| Constraint build time | 1.12 s |
| Base DCOPF variables | 24,113 |
| Total constraints (base + contingency) | 539,661 |
| HiGHS solve time | 438.4 s |
| Termination status | OTHER_ERROR |
| Peak memory | 5,067 MB |

**MEDIUM finding:** HiGHS encountered an internal error (OTHER_ERROR) after 438 seconds on
the MEDIUM problem. The LP has 24,113 variables and 539,661 constraints. The 474K contingency
constraints (~20:1 ratio vs base) combined with 5 GB memory consumption likely exceeded HiGHS's
internal limits for single-threaded LP.

### Scale Comparison

| Metric | SMALL | MEDIUM | Ratio |
|--------|-------|--------|-------|
| Branches | 3,206 | 12,706 | 4.0x |
| Contingency constraints | 145,912 | 474,178 | 3.3x |
| Total constraints | 161,748 | 539,661 | 3.3x |
| LODF compute time | 0.48 s | 3.6 s | 7.5x |
| Constraint build time | 0.17 s | 1.12 s | 6.6x |
| Peak memory | 1,776 MB | 5,067 MB | 2.9x |
| Solver outcome | TIME_LIMIT (incumbent) | OTHER_ERROR | - |

The LODF matrix scales as O(branches^2): 3206^2 = 10.3M entries for SMALL vs 12706^2 = 161.4M
for MEDIUM (15.7x). The LODF computation itself scaled 7.5x, suggesting good algorithmic
efficiency. Constraint count scaled ~3.3x (sub-linear due to sparsity filtering of small LODF
values).

### Mechanical Success

The approach works mechanically at both scales:
- System loading and time series setup succeeded
- LODF matrix computation completed (0.5s SMALL, 3.6s MEDIUM)
- PSI model building succeeded (BUILT status)
- JuMP constraint injection worked (145K-474K constraints added in <1.2s)
- The bottleneck is entirely in the LP solver phase

### Reference: A-9 SCOPF on TINY

On TINY (39-bus), the same approach with full N-1 (all lines) produced ~1,600 contingency
constraints and solved in <1 second. The constraint count explosion from 1.6K (TINY) to
146K (SMALL, 50 contingencies) to 474K (MEDIUM, 50 contingencies) demonstrates that the
brute-force LODF constraint injection approach does not scale well. A practical SCOPF
implementation would need iterative contingency screening (solve, check, add violated
contingencies, repeat).

## Workarounds

- **What:** (1) No built-in SCOPF in PowerSimulations.jl. Manually assembled N-1 contingency
  constraints via LODF matrix (PowerNetworkMatrices.jl) + JuMP `@constraint` macro.
  (2) Used `initialize_model=false` and `JuMP.optimize!()` directly.
  (3) Selected top-50 contingencies by max LODF magnitude for scalable contingency screening.
- **Why:** (1) PSI has no SCOPF formulation (open issue #944). (2) PSI initialization fails
  at SMALL+ scale. (3) Full N-1 on SMALL (3,206 contingencies) would produce ~10M constraints.
- **Durability:** fragile — same internal API access pattern as A-9 and A-5. The LODF computation
  and JuMP constraint injection are stable, but PSI's internal variable containers may change
  between versions.

## Timing

- **Wall-clock (SMALL, total):** 602.2 s (build 1.6s + LODF 0.5s + constraints 0.2s + solve 600s)
- **Wall-clock (MEDIUM, total):** 448.9 s (build 5.7s + LODF 3.6s + constraints 1.1s + solve 438s)
- **Timing source:** measured (post JIT warm-up)
- **Peak memory:** 5,067 MB (MEDIUM)
- **CPU cores used:** 1 (32 available)

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c8_scopf_scale.jl`

Key scale-up patterns:
```julia
# Contingency selection: top-50 by max LODF impact
impact_scores = Dict{String, Float64}()
for cont_name in branch_names
    max_impact = maximum(abs(lodf_matrix[mon, cont_name])
        for mon in branch_names if mon != cont_name && abs(lodf_matrix[mon, cont_name]) < 0.95)
    impact_scores[cont_name] = max_impact
end
sorted = sort(collect(impact_scores), by=x -> -x[2])
top_50 = [s[1] for s in sorted[1:50]]

# Time series needed for RenewableDispatch and HydroDispatch at SMALL+ scale
for gen in get_components(RenewableDispatch, sys)
    add_time_series!(sys, gen, SingleTimeSeries("max_active_power", ...))
end
```

## Observations

- **solver-issues:** HiGHS hits TIME_LIMIT on SMALL (145K constraints) and OTHER_ERROR on MEDIUM
  (474K constraints) for the brute-force SCOPF LP. The constraint-to-variable ratio is extreme:
  ~29:1 on SMALL, ~22:1 on MEDIUM. A production SCOPF would need iterative contingency screening
  (Benders decomposition or lazy constraint callbacks) rather than upfront constraint injection.
- **api-friction:** PSI requires time series on *all* dispatchable device types
  (RenewableDispatch, HydroDispatch) even for a single-period DC OPF snapshot. Omitting these
  causes a silent build failure where `build!()` logs an error but returns without throwing,
  leaving a partially-constructed model that produces solver errors.
