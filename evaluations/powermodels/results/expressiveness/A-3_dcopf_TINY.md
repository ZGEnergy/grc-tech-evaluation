---
test_id: A-3
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: c29ae4d0
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.007
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 354
solver: HiGHS
timestamp: 2026-03-13T12:00:00Z
---

# A-3: DC OPF with Modified Tiny Data

## Result: PASS

## Approach

Loaded `case39.m` using `PowerModels.parse_file`. Applied two Modified Tiny augmentations:

1. **Differentiated costs** from `data/timeseries/case39/gen_temporal_params.csv`: replaced homogeneous `$0.30/MWh` generator costs with fuel-type-specific quadratic cost curves (hydro $5, nuclear $10, coal $25, gas CC $40 $/MWh), applied as polynomial model 2 with coefficients `[c2*baseMVA^2, c1*baseMVA, 0]`.

2. **70% branch derating**: multiplied all `rate_a`, `rate_b`, `rate_c` values by 0.70 to produce binding congestion.

Solved DC OPF using:

```julia

result = PowerModels.solve_dc_opf(
    data, highs_opt;
    setting = Dict("output" => Dict("duals" => true))
)

```

**API note:** `solve_dc_opf` takes `(data, optimizer; kwargs...)` — only two positional arguments. The `setting` kwarg enables dual variable extraction. The third-argument formulation type (`DCPPowerModel`) is implicit.

**LMPs:** Extracted from `result["solution"]["bus"][id]["lam_kcl_r"]`. Conversion: `LMP $/MWh = -lam_kcl_r / baseMVA`. The negative sign is because the KCL dual for a cost-minimization problem is negative.

**Branch flows and shadow prices:** Directly available in `result["solution"]["branch"][id]["pf"]` (per-unit). `mu_sm_fr` and `mu_sm_to` contain branch flow shadow prices when branches are binding.

## Output

| Metric | Value |
|--------|-------|
| Termination status | OPTIMAL |
| Objective | $215,211/h |
| Solver time | 0.0011s (HiGHS solve only) |
| Wall clock | 0.007s (warm run; first invocation ~1.9s with JIT) |
| Total generation | 6,254 MW |
| Binding branches | 5 / 46 |
| LMP min | $7.76/MWh (bus 2) |
| LMP max | $290.11/MWh (bus 3) |
| LMP spread | $282.36/MWh |

Generator dispatch:

| Gen | Bus | Dispatch (MW) | Pmax (MW) | Cost ($/MWh) |
|-----|-----|--------------|-----------|-------------|
| 1 | 30 | 275.6 | 1040.0 | $5 (hydro) |
| 2 | 31 | 646.0 | 646.0 | $10 (nuclear) |
| 3 | 32 | 630.0 | 725.0 | $10 (nuclear) |
| 4 | 33 | 592.0 | 652.0 | $25 (coal) |
| 5 | 34 | 508.0 | 508.0 | $25 (coal) |
| 6 | 35 | 630.0 | 687.0 | $10 (nuclear) |
| 7 | 36 | 580.0 | 580.0 | $40 (gas CC) |
| 8 | 37 | 564.0 | 564.0 | $10 (nuclear) |
| 9 | 38 | 840.0 | 865.0 | $10 (nuclear) |
| 10 | 39 | 988.6 | 1100.0 | $40 (gas CC) |

Binding branches (at or near thermal limit after 70% derating):

| Branch | From→To | Flow (MW) | Limit (MW) |
|--------|---------|-----------|-----------|
| 3 | 2→3 | 350.0 | 350.0 |
| 20 | 10→32 | -630.0 | 630.0 |
| 27 | 16→19 | -420.0 | 420.0 |
| 37 | 22→35 | -630.0 | 630.0 |
| 46 | 29→38 | -840.0 | 840.0 |

LMP sample (first 10 buses):

| Bus | LMP ($/MWh) |
|-----|------------|
| 1 | 77.13 |
| 2 | 7.76 |
| 3 | 290.11 |
| 4 | 249.63 |
| 5 | 232.93 |
| 6 | 232.04 |
| 7 | 225.43 |
| 8 | 222.12 |
| 9 | 161.05 |
| 10 | 236.63 |

The large LMP spread ($282/MWh) is driven by the 5 binding branches creating price separation between load and generation buses. The pattern is economically consistent: low-cost hydro (bus 30, gen 1) and nuclear generators export power through congested corridors, raising LMPs at receiving buses.

## Workarounds

None required. `solve_dc_opf` with `setting=Dict("output"=>Dict("duals"=>true))` provides:
- Optimal dispatch directly in `result["solution"]["gen"]`
- LMPs via `lam_kcl_r` in `result["solution"]["bus"]`
- Branch flows via `pf` in `result["solution"]["branch"]`
- Termination status as JuMP `TerminationStatusCode` (OPTIMAL)

## Timing

- **Wall-clock:** 0.007s (warm run; first invocation ~1.9s including JIT compilation for JuMP/HiGHS)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver time (HiGHS only):** 0.0011s
- **CPU cores used:** 1 (HiGHS configured with `threads=1`)

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a3_dcopf_tiny.jl`

Key API calls:

```julia

data = PowerModels.parse_file("../../data/networks/case39.m")

# Apply differentiated costs (from gen_temporal_params.csv)
gen["model"] = 2; gen["ncost"] = 3
gen["cost"] = [c2 * base_mva^2, c1 * base_mva, 0.0]

# Apply 70% branch derating
branch["rate_a"] *= 0.70

# Solve DC OPF — two positional args + setting kwarg
highs_opt = optimizer_with_attributes(HiGHS.Optimizer, "output_flag"=>false, "threads"=>1)
result = PowerModels.solve_dc_opf(data, highs_opt;
    setting = Dict("output" => Dict("duals" => true)))

# Extract LMP: -lam_kcl_r / baseMVA gives $/MWh
lmp = -result["solution"]["bus"][bus_id]["lam_kcl_r"] / base_mva

# Branch flow (per-unit, multiply by baseMVA for MW)
pf_mw = result["solution"]["branch"][br_id]["pf"] * base_mva

```
