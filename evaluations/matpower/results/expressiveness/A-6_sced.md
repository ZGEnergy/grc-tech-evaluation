---
test_id: A-6
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: "3343ccf1"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.06
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 554
solver: MIPS
cpu_threads_used: null
cpu_threads_available: null
ingestion_path: null
sced_mode: ed_only
test_category: null
timestamp: 2026-03-24T00:00:00Z
---

# A-6: Fix commitment from A-5, solve economic dispatch as LP/QP

## Result: PASS

## Approach

The SCED was implemented as a two-stage workflow demonstrating clean UC/ED separability:

1. **Stage 1 (UC):** The commitment schedule from A-5 was fixed externally. Gas CC G7 (bus 36, 650 MW) is off for hours 2-5, gas CC G10 (bus 39, 540 MW) is off for hours 3-4. All other generators remain committed for all 24 hours.

2. **Stage 2 (ED):** Per-period `rundcopf()` with:
   - `GEN_STATUS=0` for decommitted generators each period
   - Quadratic costs (c2 = c1 * 0.001) using MIPS QP solver
   - Ramp constraints enforced via Pmax/Pmin tightening: `Pmax(t) = min(Pmax, Pg(t-1) + ramp_limit)`, `Pmin(t) = max(Pmin, Pg(t-1) - ramp_limit)`
   - Ramp only applied when both current and previous periods are committed

The ramp constraints are implemented in the ED stage, not inherited from UC. MATPOWER's `rundcopf()` does not natively enforce inter-period ramp constraints (it solves single snapshots), so the evaluator must manually tighten Pmax/Pmin bounds based on the previous period's dispatch. MOST provides built-in inter-period ramp enforcement via `RAMP_10`/`RAMP_30`, but the per-period `rundcopf()` approach more clearly demonstrates the two-stage separability.

**sced_mode: ed_only** -- The approach uses single-period DC OPF per hour without embedded security constraints (N-1 contingencies). Network constraints (branch limits) are enforced but not contingency constraints.

## Output

### Dispatch Summary

All 24 periods solved successfully. Total solve time: 1.06 s (mean 0.044 s/period).

| Generator | Bus | Type | Dispatch Range (MW) |
|-----------|-----|------|---------------------|
| G1 | 30 | hydro | 836.9 - 900.0 |
| G2 | 31 | nuclear | 567.7 - 646.0 |
| G3 | 32 | nuclear | 573.1 - 725.0 |
| G4 | 33 | coal | 260.8 - 652.0 |
| G5 | 34 | coal | 203.2 - 508.0 |
| G6 | 35 | nuclear | 569.4 - 687.0 |
| G7 | 36 | gas_CC | 0.0 - 463.9 (off HR02-05) |
| G8 | 37 | nuclear | 307.7 - 540.5 |
| G9 | 38 | nuclear | 449.2 - 865.0 |
| G10 | 39 | gas_CC | 0.0 - 330.0 (off HR03-04) |

### Ramp Verification (Base Case, 60x ramps)

With original ramp rates (MW/min * 60), ramps are not binding (max ratio 0.43 for G7). Zero violations.

### Ramp Binding Evidence (15x vs 60x)

Tightening ramps from 60x to 15x produces:
- **Cost increase:** $6,454.32 (0.23%) -- demonstrates ramp constraints are active
- **3 generators bind on ramps:** G4 coal (ratio=1.000), G5 coal (ratio=1.000), G7 gas_CC (ratio=1.000)
- **9 generators show dispatch changes**, max change 235.28 MW (G9 nuclear)

### LMP Summary

LMPs range from $5-14/MWh (off-peak) to $13-93/MWh (peak HR18). LMP spreads increase with load, indicating congestion effects.

### Decommitment Verification

All decommitted generators dispatch exactly zero. 2 generators cycle in the commitment schedule.

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.06 s (24 periods of per-period DC OPF)
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **Solver:** MIPS (built-in QP solver)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a6_sced.m`

Key API demonstrating two-stage separability:
```matlab
%% Stage 1: External commitment
commit_sched = ones(ng, nt);
commit_sched(7, 2:5) = 0;  % Gas CC G7 off hours 2-5
commit_sched(10, 3:4) = 0; % Gas CC G10 off hours 3-4

%% Stage 2: Per-period ED with ramp enforcement
for t = 1:nt
    mpc.gen(g, GEN_STATUS) = commit_sched(g, t);  % fix commitment
    if t > 1 && committed(t) && committed(t-1)
        mpc.gen(g, PMAX) = min(PMAX, prev_pg + ramp_limit);  % ramp up
        mpc.gen(g, PMIN) = max(PMIN, prev_pg - ramp_limit);  % ramp down
    end
    result_t = rundcopf(mpc, mpopt);  % QP solve with quadratic costs
end
```
