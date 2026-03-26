---
test_id: A-12
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 5a44a78c
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 5.85
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 310
solver: "SCIP (MIQP phase 1); HiGHS (LP phase 2 for LMPs)"
timestamp: 2026-03-24T18:00:00Z
---

# A-12: 24-Hour Multi-Period DCOPF with Renewables, BESS Cyclic SoC, Quadratic Costs

## Result: PASS

All three behavioral pass conditions met.

## Approach

### Network augmentation (Modified Tiny):
- IEEE 39-bus, 10 existing generators with differentiated costs (c1 from `gen_temporal_params.csv`, c2 = c1 x 0.001)
- 70% branch derating applied to all `rate_a`/`rate_b`/`rate_c`
- 5 renewable generators added (zero marginal cost, hourly pmax from `wind_forecast_24h.csv` and `solar_forecast_24h.csv`)
- BESS at bus 5: 150 MW / 600 MWh, eta_charge=0.92, eta_discharge=0.95, initial SoC = 300 MWh (50%), max SoC = 540 MWh (90%)

### Multi-period model:
`PowerModels.replicate(data, 24)` creates a 24-period multi-network dict. Per-period load and RE limits are applied via `mn_data["nw"][string(t)]`.

### Solver required -- SCIP (MIQP):
`PowerModels.build_mn_opf_strg` (invoked via `instantiate_model`) introduces `ZeroOne` binary complementarity constraints for the storage charge/discharge decision variables, making this a MIQP. HiGHS rejects MIQP with `OTHER_ERROR`. Ipopt rejects `ZeroOne` constraints. SCIP handles MIQP via branch-and-bound. [solver-specific: HiGHS and Ipopt cannot handle this formulation's integer constraints]

### Cyclic SoC via manual constraint injection:
`solve_mn_opf_strg` does not natively enforce cyclic SoC. `constraint_storage_state_initial` pins `se[1]` relative to the `energy` field (initial state before period 1). For a true 24-hour cycle, the terminal state must equal the pre-period-1 state:

```julia
pm = PowerModels.instantiate_model(mn_data, PowerModels.DCPPowerModel,
                                   PowerModels.build_mn_opf_strg)
nw_ids_sorted = sort(collect(PowerModels.nw_ids(pm)))
n_last = nw_ids_sorted[end]
for strg_id in PowerModels.ids(pm, :storage, nw=1)
    energy_init_pu = mn_data["nw"]["1"]["storage"][string(strg_id)]["energy"]
    se_last = PowerModels.var(pm, n_last)[:se][strg_id]
    JuMP.@constraint(pm.model, se_last == energy_init_pu)
end
result = PowerModels.optimize_model!(pm; optimizer=scip_opt)
```

### Two-phase LMP extraction:
SCIP (MIP solver) cannot return LP duals after solving an integer program. Phase 2 fixes the storage dispatch from SCIP, removes storage from the single-period data dict, and adds a fixed-injection generator (`pmin=pmax=sd-sc`) at the BESS bus. HiGHS then solves 24 LP snapshots with `duals=true` to extract LMPs. This is a standard fix-and-price approach.

Note: The Phase 2 snapshot must be built by deepcopying the full base `data` dict (which has all required top-level keys including `per_unit`, `version`, `baseMVA`) and overwriting period-specific fields -- NOT by copying `mn_data["nw"][t]` which lacks these top-level keys.

## Output

### Pass condition results:

| Condition | Result | Detail |
|-----------|--------|--------|
| (1) Congestion: >=2 hours with >=2 binding branches | PASS | 24/24 hours congested; 4-6 binding branches per hour |
| (2) BESS arbitrage: mean discharge LMP > mean charge LMP | PASS | discharge: $74.98/MWh, charge: $45.34/MWh |
| (3) SoC feasibility: max energy balance error < 1.0 MWh | PASS | max error = 0.000000e+00 MWh |

### BESS dispatch summary:

| Period | SC (MW) | SD (MW) | SE (MWh) | LMP bus 5 ($/MWh) |
|--------|---------|---------|----------|---------------------|
| 1-2 | 0 | 0 | 300.0 | 44.63-41.12 |
| 3-5 | 67-150 | 0 | 362-540 | 40.27 (charging at low-price hours) |
| 6-16 | 0 | 0 | 540.0 | 42.25-68.32 (full, waiting) |
| 17-20 | 0 | 105-150 | 430-0 | 69.17-81.89 (discharging at peak) |
| 21 | 0 | 0 | 0 | 62.37 |
| 22-24 | 26-150 | 0 | 24-300 | 46.53-53.91 (recharging to 300 MWh) |

- Charge hours: 3, 4, 5, 22, 23, 24 -- mean LMP $45.34/MWh
- Discharge hours: 17, 18, 19, 20 -- mean LMP $74.98/MWh
- Terminal SoC at end of hour 24: 300 MWh = initial SoC (cyclic constraint satisfied)
- Objective: $2,555,620/h
- SCIP solve time: ~3.37s; Phase 2 (24 LP solves): ~2.5s

### Congestion detail:
Binding branches by hour: [5, 4, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 5, 5, 5]

All 24 hours have 4-6 binding branches. LMP spread confirmed across all hours (LMP spread > $0.01/MWh in all 24 hours).

## Workarounds

Three workarounds were required, all classified as stable:

### 1. Solver switch (SCIP instead of HiGHS/Ipopt)
- **What:** `solve_mn_opf_strg` must be solved with SCIP, not HiGHS or Ipopt.
- **Why:** PowerModels `build_mn_opf_strg` introduces `ZeroOne` binary complementarity constraints for charge/discharge exclusivity. HiGHS rejects MIQP (`OTHER_ERROR`). Ipopt rejects `ZeroOne` constraints (`UnsupportedConstraint`). SCIP handles MIQP.
- **Durability:** stable -- SCIP is a supported solver in the evaluation stack. The binary complementarity formulation is documented behavior of `solve_mn_opf_strg`. Users must know to use SCIP for storage OPF.
- **Grade impact:** Moderate. Requires solver knowledge. HiGHS (the default LP/QP solver) cannot be used for multi-period storage OPF.

### 2. Cyclic SoC via manual JuMP constraint injection
- **What:** `instantiate_model` + `JuMP.@constraint(pm.model, se[T] == energy_initial)`.
- **Why:** `solve_mn_opf_strg` does not natively enforce `se[T] == initial_energy`. Without this constraint, SCIP optimally chooses to deplete the battery with no incentive to recharge.
- **Durability:** stable -- `instantiate_model` and `PowerModels.var(pm, nw)[:se]` are documented PowerModels APIs. The approach is non-obvious but fully supported.
- **Grade impact:** Minor. The API exists; the pattern requires domain knowledge about how PowerModels structures multi-network variables.

### 3. Two-phase LMP extraction
- **What:** SCIP solves MIQP, then fix storage dispatch, then HiGHS re-solves 24 LP snapshots for duals.
- **Why:** SCIP (MIP solver) does not return LP duals (`GetAttributeNotAllowed{ConstraintDual}`). LMPs require LP dual variables.
- **Durability:** stable -- This is a standard fix-and-price technique. The limitation of MIP solvers not returning LP duals is universally documented.
- **Grade impact:** Minor. The approach is correct and produces valid LMPs. No fundamental loss of capability.

## Timing

- **Wall-clock:** 5.85s
- **Timing source:** measured (warm JIT; SCIP phase ~3.37s, Phase 2 LP ~2.5s)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a12_multiperiod_dcopf_storage_tiny.jl`

Key implementation notes:
- Phase 2 snapshot must deepcopy full `data` dict (not `mn_data["nw"][t]`) to preserve top-level keys
- PowerModels storage sign convention: `ps = sc - sd` (positive ps = charging, negative = discharging)
- Cyclic SoC: `se[T] == energy_initial` (not `se[T] == se[1]` which is off by one period)
