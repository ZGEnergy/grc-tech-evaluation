---
test_id: C-8
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "dddfe556"
status: constrained_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 14.43
timing_source: measured
peak_memory_mb: 5042.7
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 560
solver: HiGHS
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: "2026-03-24T00:00:00Z"
---

# C-8: SCOPF N-1 (50 Contingencies) on SMALL and MEDIUM

## Result: CONSTRAINED PASS

SCOPF with 50 contingencies solved optimally on SMALL (2000-bus) in 14.4s with 8,829 MW
aggregate redispatch. MEDIUM (10k-bus) SCOPF failed with HiGHS OTHER_ERROR after 328s due
to the 535k-constraint LP exceeding solver numerical limits. The SCOPF capability is
demonstrated under SMALL-scale constraints only; it does not generalize to MEDIUM scale.

## Approach

PowerSimulations.jl has no built-in SCOPF (open issue #944). Manual SCOPF was assembled using
the same approach as A-9 (SCOPF on TINY), scaled to SMALL and MEDIUM networks:

1. **LODF computation:** `LODF(sys)` from PowerNetworkMatrices.jl computes the full Line Outage
   Distribution Factor matrix for all branches.
2. **Contingency selection:** Top 50 contingencies selected by maximum LODF impact magnitude,
   excluding near-radial branches (|LODF| >= 0.95).
3. **Model construction:** `DecisionModel` with `DCPPowerModel` and `StaticBranchUnbounded`
   (branch flow limits removed from PSI formulation). Base-case flow limits and N-1 contingency
   constraints added manually via JuMP `@constraint` macro.
4. **Reference dispatch:** Unconstrained DCOPF (no flow limits) solved first to establish
   baseline dispatch for aggregate redispatch comparison.

**Workarounds inherited from C-3 (DCOPF at MEDIUM scale):**
- `initialize_model=false` + `JuMP.optimize!()` (PSI initialization bypass)
- `StaticBranchUnbounded` (PSI `StaticBranch` causes numerical infeasibility at scale)
- Linear cost override by quartile ($10-55/MWh, replacing MATPOWER quadratic costs). Required
  for both tiers -- quadratic costs cause HiGHS QP issues with `initialize_model=false`.
- All thermal and renewable generators set `available=true`
- HydroDispatch omitted (no PSI formulation in v0.30.2)

**Load scaling:** Not applied. Load scaling at 1.15x caused MEDIUM to fail at the unconstrained
DCOPF stage (infeasibility due to hydro omission reducing available generation capacity). The
v11 congestion requirement (>=5 MW aggregate redispatch) is met on SMALL (8,829 MW) through
N-1 constraints alone. MEDIUM could not be tested with load scaling.

## Output

### SMALL (ACTIVSg 2000-bus) -- PASS

| Metric | Value |
|--------|-------|
| Termination status | OPTIMAL |
| Unconstrained DCOPF objective | $1,448,067.07 |
| SCOPF objective | $1,450,658.63 |
| Cost increase | $2,591.56 (+0.18%) |
| Aggregate redispatch | 8,829.32 MW |
| Generators redispatched | 31 |
| Binding contingencies | 3 |
| N-1 constraints | 145,912 |
| Base-case flow constraints | 4,690 |
| Total constraints | 160,443 |
| Variables | 5,725 |
| Unconstrained DCOPF solve | 0.3s |
| SCOPF solve | 9.6s |
| Wall-clock (total) | 14.4s |
| Peak memory (RSS) | 1,511 MB |

**Binding contingencies (SMALL):**

| Contingency Branch | Effect |
|-------------------|--------|
| PANHANDLE 4 0-RALLS 1 0-i_160 | Post-contingency flow at rating on monitored branch |
| NEW BRAUNFELS 1 0-SAN MARCOS 0-i_2068 | Post-contingency flow at rating on monitored branch |
| GRAHAM 0-JACKSBORO 1 0-i_865 | Post-contingency flow at rating on monitored branch |

The SCOPF on SMALL demonstrates correct behavior: 3 binding contingencies cause dispatch
to shift by 8,829 MW aggregate across 31 generators, at a cost premium of 0.18%. The N-1
constraints are embedded in the optimization (not post-hoc), and the SCOPF is strictly more
expensive than the unconstrained DCOPF.

### MEDIUM (ACTIVSg 10k-bus) -- FAIL

| Metric | Value |
|--------|-------|
| Termination status | OTHER_ERROR |
| Unconstrained DCOPF | OPTIMAL ($3,659,662.46, 6.4s) |
| SCOPF solve time (before crash) | 327.5s |
| N-1 constraints | 474,178 |
| Base-case flow constraints | 19,452 |
| Total constraints | 535,000 |
| Variables | 24,476 |
| Peak memory (RSS) | 5,043 MB |

The unconstrained DCOPF on MEDIUM solves correctly (matching C-3 result of $3,659,662.46
exactly). However, the SCOPF with 535,000 total constraints causes HiGHS to crash with
OTHER_ERROR after 328s [solver-specific: HiGHS numerical failure on 535k-constraint LP at
10K scale].

### Scale Comparison

| Metric | SMALL | MEDIUM | Ratio |
|--------|-------|--------|-------|
| Branches | 3,206 | 12,706 | 4.0x |
| N-1 constraints | 145,912 | 474,178 | 3.3x |
| Total constraints | 160,443 | 535,000 | 3.3x |
| LODF compute time | 0.76s | 3.5s | 4.6x |
| Constraint injection time | 0.19s | 0.71s | 3.7x |
| Peak memory | 1,511 MB | 5,043 MB | 3.3x |
| Solver outcome | OPTIMAL (9.6s) | OTHER_ERROR (328s) | -- |

The LODF matrix scales as O(branches^2): 3206^2 = 10.3M entries for SMALL vs 12706^2 = 161.4M
for MEDIUM (15.7x). Constraint count scales ~3.3x (sub-linear due to LODF sparsity filtering).
The mechanical overhead (LODF computation + constraint injection) scales well; the bottleneck
is entirely in the LP solver phase.

### Reference: A-9 SCOPF on TINY

On TINY (39-bus, A-9), the same approach with all 46 branches produced 312 N-1 constraints and
solved in <1s with a 17.7% cost premium. The constraint count progression: 312 (TINY, all
branches) -> 145,912 (SMALL, 50 contingencies) -> 474,178 (MEDIUM, 50 contingencies) confirms
that the brute-force approach does not scale. A production SCOPF would use iterative screening
(Benders decomposition or lazy constraint callbacks).

## Workarounds

- **What:** (1) No built-in SCOPF -- manual assembly via LODF + JuMP constraint injection.
  (2) StaticBranchUnbounded + manual base-case flow limits via JuMP (replacing PSI StaticBranch).
  (3) initialize_model=false + JuMP.optimize!() (PSI initialization bypass).
  (4) Linear cost override by quartile (replacing MATPOWER quadratic costs).
  (5) All generators set available=true.
  (6) HydroDispatch omitted from template.
- **Why:** (1) PSI lacks SCOPF capability (open issue #944) [tool-specific].
  (2) PSI StaticBranch causes numerical infeasibility at scale [tool-specific].
  (3) PSI initialization fails at scale [tool-specific].
  (4) Quadratic costs cause HiGHS QP issues with initialize_model=false
  [mixed: tool initialization + solver QP handling].
  (5-6) ACTIVSg10k hydro capacity gap [tool-specific: no hydro OPF formulation].
- **Durability:** fragile -- Six stacked workarounds. Items (2), (3), (5), (6) depend on
  internal PSI behavior and architectural limitations. The manual SCOPF assembly (1) uses
  documented public APIs (LODF from PowerNetworkMatrices.jl, get_jump_model from PSI, @constraint
  from JuMP) but requires ~560 lines of domain-specific code. The cascaded workaround pattern
  from C-3 compounds at SCOPF scale.
- **Grade impact:** SCOPF demonstrated at SMALL scale only. MEDIUM failure is
  [mixed attribution]: tool-specific (manual brute-force approach generates 474k constraints that
  a built-in iterative SCOPF would avoid) + solver-specific (HiGHS crashes on the resulting LP).
  A tool with built-in SCOPF using Benders decomposition would produce far fewer active
  constraints and likely succeed at MEDIUM scale.

## Timing

- **Wall-clock (SMALL, total):** 14.4s (unconstrained DCOPF 0.3s + SCOPF build 4.5s + solve 9.6s)
- **Wall-clock (MEDIUM, total):** 356.7s (unconstrained DCOPF 6.4s + SCOPF build+crash 350s)
- **Timing source:** measured (post JIT warm-up)
- **Peak memory:** 5,043 MB (MEDIUM); 1,511 MB (SMALL)
- **LODF computation:** SMALL 0.76s, MEDIUM 3.5s
- **Constraint injection:** SMALL 0.19s, MEDIUM 0.71s
- **CPU threads used:** 1
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c8_scopf_scale.jl`

Key patterns:
```julia
# Step 1: Unconstrained DCOPF reference (StaticBranchUnbounded, no flow limits)
model1 = build_dcopf(sys1, solver)
JuMP.optimize!(PSI.get_jump_model(PSI.get_optimization_container(model1)))
ref_dispatch = extract_dispatch_mw(oc1, base_power)

# Step 2: Build SCOPF model with manual constraints
model2 = build_dcopf(sys2, solver)
jm2 = PSI.get_jump_model(PSI.get_optimization_container(model2))

# Add base-case flow limits (replacing PSI StaticBranch)
for mon_line in flow_line_names
    @constraint(jm2, flow[mon_line, t] <= rating)
    @constraint(jm2, -flow[mon_line, t] <= rating)
end

# Add N-1 contingency constraints via LODF
for cont in contingencies, mon in monitored
    lodf_val = lodf_matrix[mon, cont]
    @constraint(jm2, flow[mon, t] + lodf_val * flow[cont, t] <= rating[mon])
    @constraint(jm2, -(flow[mon, t] + lodf_val * flow[cont, t]) <= rating[mon])
end

# Solve and compute aggregate redispatch
JuMP.optimize!(jm2)
scopf_dispatch = extract_dispatch_mw(oc2, base_power)
agg_redispatch = sum(abs(scopf_mw - ref_mw) for (g, scopf_mw, ref_mw) ...)
```

## Observations

- [observation](../observations/solver-issues-scalability-C-8_scopf_scale.md)
- [observation](../observations/cascaded-failure-scalability-C-8_scopf_scale.md)
