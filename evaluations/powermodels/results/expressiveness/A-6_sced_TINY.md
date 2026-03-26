---
test_id: A-6
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 6532b23f
status: qualified_pass
workaround_class: stable
blocked_by: A-5
wall_clock_seconds: 2.00
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 310
solver: HiGHS
sced_mode: ed_only
timestamp: 2026-03-24T18:00:00Z
---

# A-6: SCED (Security-Constrained Economic Dispatch)

## Result: QUALIFIED PASS

## Approach

Since A-5 (SCUC) failed as `unsupported_in_installed_version`, the UC stage is bypassed: all generators are assumed committed across all 24 periods. The ED stage is implemented as a 24-period multi-period DC OPF with ramp rate constraints enforced between consecutive intervals. This makes this test `ed_only` (no UC stage).

### Implementation:

1. Load network and augmented cost/load data from Modified Tiny (`gen_temporal_params.csv`, `load_24h.csv`)
2. Apply differentiated quadratic costs (c2 = c1 x 0.001) and 70% branch derating
3. Build 24-period multi-network: `PowerModels.replicate(data, 24)`
4. Set period-specific loads from `load_24h.csv` for each period
5. Instantiate model: `instantiate_model(mn_data, DCPPowerModel, build_mn_opf)`
6. Add ramp constraints between consecutive periods using `PowerModels.var(pm, t, :pg)` for period `t`
7. Solve: `optimize_model!(pm; optimizer=highs_opt, ...)`

#### Ramp constraint formulation:

```julia
pg_prev = PowerModels.var(pm, t-1, :pg)[gen_id]
pg_curr = PowerModels.var(pm, t, :pg)[gen_id]
ramp_pu = ramp_mw / base_mva
@constraint(pm.model, pg_curr - pg_prev <= ramp_pu)
@constraint(pm.model, pg_prev - pg_curr <= ramp_pu)
```

**Two-stage separation:** The UC stage (commitment decision) is bypassed. The ED stage is the multi-period LP solved in a single call. The separation is clean and explicit -- no UC variables or logic are present in the model.

## Output

| Metric | Value |
|--------|-------|
| Network | 39 buses, 46 branches, 10 gens, baseMVA=100 |
| Periods | 24 (1h resolution) |
| Solver status | OPTIMAL |
| Objective (total cost) | $3,115,622.56/day |
| Ramp constraints added | 460 (2 per gen per interval x 10 gens x 23 transitions) |
| Ramp violations found | 0 (verified post-solve across 230 checks) |
| Wall clock | ~2.0s (warm JIT) |
| LOC | 310 |

### Dispatch summary (select hours):

| Hour | Total Dispatch (MW) | Total Load (MW) |
|------|---------------------|-----------------|
| HR4 (valley) | 4,237.2 | 4,237.2 |
| HR12 (shoulder) | 5,623.4 | 5,623.4 |
| HR18 (peak) | 6,254.2 | 6,254.2 |

### Ramp enforcement evidence:

Post-solve check across all 230 consecutive-period pairs (10 gens x 23 transitions): 0 ramp violations.

### Ramp binding evidence (10% ramp rate re-run):

A second solve with ramp rates scaled to 10% of original values confirms that the constraints are active and affect the solution:

| Metric | Loose Ramps | Tight Ramps (10%) |
|--------|-------------|-------------------|
| Objective | $3,115,622.56 | $3,230,607.45 |
| Binding ramp constraints | 0 / 230 | 62 / 230 |
| Objective increase | -- | $114,984.89/h |

The tight-ramp solve produces a higher objective ($114,985 increase) and 62 binding ramp constraints, confirming that the ramp constraint mechanism is operative and correctly influences dispatch scheduling. [tool-specific]

## Workarounds

- **What:** A-5 (SCUC) is unsupported. A-6 implements ED only (commitment bypassed, all units assumed on).
- **Why:** PowerModels.jl has no binary commitment variables. UC stage requires a full MILP not supported by the tool.
- **Durability:** stable -- the workaround (skip UC) is a clean scope reduction. The ED implementation via `replicate` + multi-period LP is first-class PowerModels API.
- **Grade impact:** B-level. The two-stage architecture is cleanly separable. The ED stage is fully implemented via documented API. The UC gap is a hard capability boundary, not a modeling difficulty.

## Timing

- **Wall-clock:** 2.00s (warm JIT)
- **Multi-period LP solve (24 periods):** ~0.94s
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1 (HiGHS single-threaded)

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a6_sced_tiny.jl`

Key patterns:

```julia
# Build 24-period multi-network
mn_data = PowerModels.replicate(base_data, 24)

# Instantiate and augment with ramp constraints
pm = PowerModels.instantiate_model(mn_data, PowerModels.DCPPowerModel,
                                    PowerModels.build_mn_opf)
for t in 2:24
    pg_prev = PowerModels.var(pm, t-1, :pg)
    pg_curr = PowerModels.var(pm, t, :pg)
    for gen_id in valid_gen_ids
        @constraint(pm.model, pg_curr[gen_id] - pg_prev[gen_id] <=  ramp_pu[gen_id])
        @constraint(pm.model, pg_prev[gen_id] - pg_curr[gen_id] <=  ramp_pu[gen_id])
    end
end

# Solve
result = PowerModels.optimize_model!(pm; optimizer=highs_opt,
                                      solution_processors=[PowerModels.sol_data_model!])
```
