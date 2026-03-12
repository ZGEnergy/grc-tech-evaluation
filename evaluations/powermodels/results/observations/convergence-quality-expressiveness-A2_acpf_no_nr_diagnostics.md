---
tag: convergence-quality
source_dimension: expressiveness
source_test: A-2
tool: powermodels
severity: moderate
timestamp: 2026-03-12T03:24:30Z
---

# Convergence Quality: compute_ac_pf does not expose NR iteration count or residual

## Observation

`PowerModels.compute_ac_pf(data)` uses NLsolve for Newton-Raphson iteration internally but does not surface the NR iteration count or final convergence residual (mismatch) in the result dict. The pass condition for A-2 requires both to be reported.

The result dict contains only:
- `termination_status` — Bool (true/false)
- `solve_time` — wall-clock seconds
- `objective` — always 0.0 for PF
- `solution` — bus vm/va + gen pg/qg

No `iterations`, `final_mismatch`, or `residual_norm` key is present.

## Impact

This is a diagnostic quality gap. The solver runs correctly (voltages are non-flat, physically plausible), but the evaluator cannot verify the convergence criterion via the standard API. The protocol requires reporting these values; they are unavailable from `compute_ac_pf`.

### Convergence was verified indirectly:
1. Bool `termination_status == true`
2. 100% of PQ buses (29/29) have Vm ≠ 1.0 pu (flat start was va=0, vm=1.0)
3. 100% of non-slack buses (38/38) have Va ≠ 0.0 rad

## Workaround

No workaround available within the `compute_ac_pf` API. If iteration count is needed, use the lower-level `instantiate_model` + `optimize_model!` path with JuMP's Ipopt solver, which exposes solver statistics.

## Version

PowerModels.jl v0.21.5, Julia 1.10. This is a design characteristic of the `compute_*` functions (they bypass JuMP to avoid overhead) — the diagnostic gap is the tradeoff for speed.
