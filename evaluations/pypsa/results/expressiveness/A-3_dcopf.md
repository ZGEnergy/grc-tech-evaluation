---
test_id: A-3
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 150da706
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 3.30
timing_source: measured
peak_memory_mb: 4.16
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
max_branch_loading: 1.000000
binding_branches: 5
lmp_spread: 89.22
loc: 271
solver: highs
timestamp: 2026-03-24T12:02:00Z
---

# A-3: Solve DC OPF with gen costs and line flow limits on TINY

## Result: PASS

## Approach

Loaded IEEE 39-bus network via the shared MATPOWER loader (`load_pypsa`). Applied
Modified Tiny data:

1. **Differentiated generator costs** loaded from `data/timeseries/case39/gen_temporal_params.csv`
   using the `tech_class_key` field mapped to the cost table from the README:
   - hydro: $5/MWh
   - nuclear: $10/MWh
   - coal_large: $25/MWh
   - gas_CC: $40/MWh

2. **70% branch derating** applied to all lines (`n.lines.s_nom *= 0.7`) and
   transformers (`n.transformers.s_nom *= 0.7`).

Ran `n.optimize(solver_name="highs")` with HiGHS solver settings per solver-config.md
(time_limit=300, presolve=on, threads=1). The optimization uses PyPSA's linopy-based
LP formulation for DC OPF.

## Output

### Solver

| Metric | Value |
|--------|-------|
| Solver | HiGHS 1.13.1 |
| Status | ok (optimal) |
| Simplex iterations | 26 |
| Objective value | $126,125.17 |

### Dispatch

| Generator | Tech Class | Marginal Cost | Dispatch (MW) |
|-----------|-----------|---------------|---------------|
| G0 | hydro | $5/MWh | 235.54 |
| G1 | nuclear | $10/MWh | 646.00 |
| G2 | nuclear | $10/MWh | 630.00 |
| G3 | coal_large | $25/MWh | 630.00 |
| G4 | coal_large | $25/MWh | 470.00 |
| G5 | nuclear | $10/MWh | 630.00 |
| G6 | gas_CC | $40/MWh | 580.00 |
| G7 | nuclear | $10/MWh | 564.00 |
| G8 | nuclear | $10/MWh | 840.00 |
| G9 | gas_CC | $40/MWh | 1028.69 |

Total generation: 6254.23 MW = Total load: 6254.23 MW (balanced).

### LMPs

| Metric | Value |
|--------|-------|
| LMP max | $94.22/MWh (bus 3) |
| LMP min | $5.00/MWh (bus 2, 30) |
| LMP spread | $89.22/MWh |

LMPs show strong spatial differentiation driven by congestion. Buses behind
binding constraints (e.g., bus 3 at $94.22/MWh) have elevated prices, while
buses near cheap generators (bus 2, 30 at $5.00/MWh) reflect marginal cost
of the local hydro unit.

### Branch Constraints (Hard Enforcement Verified)

| Metric | Value |
|--------|-------|
| Binding branches | 5 (2 lines + 3 transformers) |
| Max branch loading | 1.000000 (hard constraints enforced) |
| Lines at >95% utilization | 3 |

**Binding branches with shadow prices:**

| Branch | Shadow Price ($/MWh) | Type |
|--------|---------------------|------|
| L2 | -111.77 | Line (upper) |
| L21 | 51.02 | Line (lower) |
| T2 | 66.98 | Transformer |
| T8 | 66.02 | Transformer |
| T10 | 34.43 | Transformer |

**Hard constraint verification:** Max branch loading is exactly 1.000000
(no branch exceeds its derated thermal limit). This confirms PyPSA enforces
branch flow limits as hard LP constraints, not soft penalties.

**Shadow price extraction:** Shadow prices were extracted from linopy model
constraint duals (`n.model.constraints[cname].dual`). The standard PyPSA
accessors `n.lines_t.mu_upper` and `n.lines_t.mu_lower` are empty after
`n.optimize()` in v1.1.2. The PyPSA INFO log confirms: "The shadow-prices
of the constraints ... were not assigned to the network." The linopy model's
constraint duals provide the same information via the linopy public API.

**Top 5 line utilization:**

| Line | Utilization |
|------|------------|
| L2 | 100.0% |
| L21 | 100.0% |
| L26 | 96.2% |
| L11 | 94.7% |
| L29 | 92.1% |

## Workarounds

Shadow prices extracted from `n.model.constraints` (linopy dual values) rather
than `n.lines_t.mu_upper`. The `mu_upper`/`mu_lower` DataFrames are empty after
`n.optimize()` in PyPSA v1.1.2; the linopy model's constraint duals provide the
same information via public linopy API. This is a documented public API path on
the linopy model object, not an undocumented internal -- classified as no
workaround needed (the linopy `Model.constraints[name].dual` property is a
documented part of linopy's API).

## Timing

- **Wall-clock:** 3.30 s (including network loading and cost assignment)
- **Solve only:** 1.57 s
- **Timing source:** measured
- **Peak memory:** 4.16 MB (tracemalloc, solve phase only)

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a3_dcopf.py`
