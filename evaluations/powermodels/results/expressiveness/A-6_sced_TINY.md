---
test_id: A-6
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v9"
skill_version: v1
test_hash: 88fa3558
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 37.3
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 260
solver: HiGHS
timestamp: 2026-03-11T00:00:00Z
---

# A-6: SCED (Security-Constrained Economic Dispatch)

## Result: QUALIFIED PASS

## Approach

Since A-5 (SCUC) is a blocking fail, the UC stage is bypassed: all generators are assumed committed across all periods. The ED stage is implemented as a 24-period multi-period DC OPF with ramp rate constraints enforced between consecutive intervals.

### Implementation:

1. Load network and augmented cost/load data
2. Build 24-period multi-network: `PowerModels.replicate(data, 24)` creates a multi-network dict `mn_data["nw"]` keyed `"1"` through `"24"`
3. Set period-specific loads from `load_24h.csv` for each period
4. Instantiate model: `instantiate_model(mn_data, DCPPowerModel, build_mn_opf)`
5. Add ramp constraints between consecutive periods using `PowerModels.var(pm, t, :pg)` for period `t`
6. Solve: `optimize_model!(pm; ...)`

#### Ramp constraint formulation:

```julia

# For each gen g, between period t-1 and t:
pg_prev = PowerModels.var(pm, t-1, :pg)[gen_id]
pg_curr = PowerModels.var(pm, t, :pg)[gen_id]
ramp_pu = ramp_mw / base_mva
@constraint(pm.model, pg_curr - pg_prev <= ramp_pu)
@constraint(pm.model, pg_prev - pg_curr <= ramp_pu)

```

**Two-stage separation:** The UC stage (commitment decision) is bypassed. The ED stage is the multi-period LP solved in a single call. The separation is clean and explicit — no UC variables or logic are present in the model.

## Output

| Metric | Value |
|--------|-------|
| Network | 39 buses, 46 branches, 10 gens, baseMVA=100 |
| Periods | 24 (1h resolution) |
| Solver status | OPTIMAL |
| Objective (total cost) | 2,410,754.87 $/day |
| Ramp constraints added | 460 (2 per gen per interval × 10 gens × 23 transitions) |
| Ramp violations found | 0 (verified post-solve) |
| Wall clock | 37.3s (includes JIT) |
| LOC | 260 |

### Dispatch summary (period 1):

Multi-period ED produces differentiated dispatch across periods. The 70% branch derating applied to match A-3 reference conditions creates binding branch flow limits in peak load periods.

#### Ramp enforcement evidence:

Post-solve check across all 230 consecutive-period pairs (10 gens × 23 transitions):
- 0 ramp violations (max violation = 0.0)
- Ramp rates were active (binding) for the gas_CC and coal_large generators in high-load transitions

## Workarounds

- **What:** A-5 (SCUC) is unsupported. A-6 implements ED only (commitment bypassed, all units assumed on).
- **Why:** PowerModels.jl has no binary commitment variables. UC stage requires a full MILP not supported by the tool.
- **Durability:** stable — the workaround (skip UC) is a clean scope reduction. The ED implementation via `replicate` + multi-period LP is first-class PowerModels API.
- **Grade impact:** B-level. The two-stage architecture is cleanly separable. The ED stage is fully implemented via documented API. The UC gap is a hard capability boundary, not a modeling difficulty.

- **What:** `base_mva` returned as `Int` (not `Float64`) by `data["baseMVA"]`.
- **Why:** MATPOWER parser reads `100` as integer. Function signatures requiring `::Float64` fail.
- **Fix:** Changed all `base_mva::Float64` to `base_mva::Real` in function signatures.
- **Durability:** stable — `Real` is the correct type annotation. Not a brittleness risk.

## Timing

- **Wall-clock:** 37.3s total (first invocation, includes JIT)
- **Multi-period LP solve (24 periods):** ~1.5s
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1 (HiGHS single-threaded)

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a6_sced_tiny.jl`

Key patterns:

```julia

# Build 24-period multi-network
mn_data = PowerModels.replicate(base_data, 24)

# Set period-specific loads
for t in 1:24
    for (load_id, load) in mn_data["nw"][string(t)]["load"]
        load["pd"] = period_load_mw[t][load_id] / base_mva
    end
end

# Instantiate and augment
pm = PowerModels.instantiate_model(mn_data, PowerModels.DCPPowerModel,
                                    PowerModels.build_mn_opf)

# Add ramp constraints
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
