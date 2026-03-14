---
test_id: A-3
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: 33025f4d
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 2.134
timing_source: measured
peak_memory_mb: 4.16
convergence_residual: null
convergence_iterations: 26
loc: 283
solver: HiGHS
timestamp: 2026-03-13T23:09:44Z
---

# A-3: Solve DC OPF with gen costs and line flow limits on TINY (Modified Tiny data)

## Result: PASS

## Approach

Loaded IEEE 39-bus network via the shared MATPOWER loader, then applied
Modified Tiny augmentation:

1. **Differentiated generator costs** from `data/timeseries/case39/gen_temporal_params.csv`:
   mapped each generator's `tech_class_key` to marginal cost (hydro $5, nuclear $10,
   coal $25, gas CC $40). This produces 4 distinct cost tiers across 10 generators.

2. **70% branch derating**: multiplied all line and transformer `s_nom` by 0.7 to
   tighten thermal limits and produce binding congestion.

Solved via `n.optimize(solver_name='highs')` with HiGHS settings per
`solver-config.md` (time_limit=300, presolve=on, threads=1).

LMPs extracted from `n.buses_t.marginal_price` (populated automatically by
`n.optimize()`). Shadow prices on binding branch constraints extracted from
the linopy model's constraint duals (`n.model.constraints[name].dual`).

## Output

| Metric | Value |
|--------|-------|
| Solver status | optimal |
| Objective | $126,125.17 |
| Total generation | 6,254.23 MW |
| Total load | 6,254.23 MW |
| HiGHS iterations | 26 (simplex) |
| Binding branches | 5 (2 lines + 3 transformers) |
| LMP max | $94.22/MWh (bus 3) |
| LMP min | $5.00/MWh (buses 2, 30) |
| LMP spread | $89.22/MWh |

**Generator dispatch:**

| Generator | Bus | Tech | Cost ($/MWh) | Dispatch (MW) | Capacity (MW) |
|-----------|-----|------|--------------|---------------|---------------|
| G0 | 30 | hydro | 5 | 235.5 | 1,040 |
| G1 | 31 | nuclear | 10 | 646.0 | 646 |
| G2 | 32 | nuclear | 10 | 630.0 | 725 |
| G3 | 33 | coal | 25 | 630.0 | 652 |
| G4 | 34 | coal | 25 | 470.0 | 508 |
| G5 | 35 | nuclear | 10 | 630.0 | 687 |
| G6 | 36 | gas CC | 40 | 580.0 | 580 |
| G7 | 37 | nuclear | 10 | 564.0 | 564 |
| G8 | 38 | nuclear | 10 | 840.0 | 865 |
| G9 | 39 | gas CC | 40 | 1,028.7 | 1,100 |

Cheap generators (hydro, nuclear) dispatch at or near capacity. Expensive
gas CC units are marginal. The dispatch order follows economic merit.

**Binding branch constraints (shadow prices):**

| Branch | Constraint | Shadow Price ($/MWh) |
|--------|-----------|---------------------|
| L2 (2-3) | upper limit | -111.77 |
| L21 (16-19) | lower limit | 51.02 |
| T2 (10-32) | lower limit | 66.98 |
| T8 (22-35) | lower limit | 66.02 |
| T10 (29-38) | lower limit | 34.43 |

Five binding constraints (>= 2 required). Lines L2 and L21 are at 100%
utilization; three transformers also bind.

**Line utilization (top 5):**

| Line | Utilization |
|------|-------------|
| L2 | 100.0% |
| L21 | 100.0% |
| L26 | 96.2% |
| L11 | 94.7% |
| L29 | 92.1% |

## Workarounds

- **What:** Shadow prices extracted from `n.model.constraints` (linopy model
  dual values) rather than `n.lines_t.mu_upper` / `n.lines_t.mu_lower`.
- **Why:** After `n.optimize()` in PyPSA v1.1.2, the `mu_upper`/`mu_lower`
  DataFrames are empty. The solver log confirms: "The shadow-prices of the
  constraints ... were not assigned to the network." The linopy model object
  retains constraint duals and is accessible as a public attribute (`n.model`).
- **Durability:** stable -- `n.model` and `n.model.constraints` are part of
  linopy's documented public API. The constraint names (`Line-fix-s-upper`,
  `Transformer-fix-s-lower`, etc.) follow a systematic naming convention that
  has been stable across PyPSA 1.0.x-1.1.x.
- **Grade impact:** Minor. LMPs are available directly via
  `n.buses_t.marginal_price` without any workaround. Only the per-branch
  shadow prices require the linopy path.

## Timing

- **Wall-clock:** 2.134s (including network loading and model construction)
- **Solve-only:** 1.127s (includes linopy model build + HiGHS solve)
- **HiGHS solve time:** <0.01s (per solver log)
- **Timing source:** measured
- **Peak memory:** 4.16 MB (solve only, via tracemalloc)
- **Solver iterations:** 26 (dual simplex)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a3_dcopf.py`
