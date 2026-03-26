---
test_id: B-4
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 97e1a572
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.491
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 296
solver: HiGHS
timestamp: 2026-03-24T12:00:00Z
---

# B-4: Stochastic DCOPF Wrapping (TINY)

## Result: PASS

## Approach

20 scenarios of single-period DC OPF at peak hour (HR 18) with correlated perturbations derived from `scenario_multipliers_50x24.csv` and `load_24h.csv`.

**Scenario generation:** The scenario multipliers file contains per-renewable-unit multipliers across 50 scenarios. These are averaged across the 5 renewable units to produce a system-wide perturbation factor, then inverted to represent net-load variation (higher renewable = lower net load). Per-scenario load multipliers range from 0.85 to 1.15. Generator availability is also perturbed within +/-2%.

**Per-scenario workflow:**
1. `deepcopy(data)` -- clone the base network (with differentiated costs)
2. Apply scenario-specific load multiplier to all loads
3. Apply generator availability perturbation
4. `solve_dc_opf(sc_data, optimizer)` with duals enabled for LMP extraction
5. Collect dispatch, LMPs, and objective

All inputs are injected programmatically via dict mutation -- no config files or file I/O per scenario. [tool-specific: data dict mutation is the native API for programmatic input]

**Solver settings:** HiGHS with `time_limit=300`, `presolve=on`, `threads=1`, `output_flag=false`.

## Output

| Metric | Value |
|--------|-------|
| Scenarios run | 20 |
| Scenarios optimal | 20 |
| Total solve time (post-JIT) | 0.079 s |
| Mean solve time/scenario | 4.0 ms |
| Min/Max solve time | 3.1 / 11.3 ms |
| Mean objective (per-unit) | 10.01 |
| Objective range | 8.14 - 12.44 |

### Scenario summary (first 5):

| Scenario | Status | Objective | Load Mult | LMP Range ($/MWh) |
|----------|--------|-----------|-----------|-------------------|
| 1 | OPTIMAL | 8.68 | 0.9609 | [-0.47, -0.05] |
| 2 | OPTIMAL | 9.86 | 0.994 | [-0.47, -0.05] |
| 3 | OPTIMAL | 11.96 | 1.0509 | [-0.94, -0.05] |
| 4 | OPTIMAL | 10.51 | 1.0149 | [-0.94, -0.05] |
| 5 | OPTIMAL | 10.25 | 1.0226 | [-0.47, -0.05] |

All 20 scenarios converge optimally. Objectives vary by scenario due to correlated load perturbations, with higher-load scenarios producing higher costs as expected. LMPs are negative (per-unit convention in PowerModels with the specific cost structure used).

## Workarounds

None required for the single-period approach. `deepcopy()` + dict mutation + `solve_dc_opf()` is all public API. The scenario multiplier CSV is read programmatically with standard Julia I/O.

**Multi-period note:** `replicate()` + `solve_mn_opf()` is the documented public API for multi-period OPF and was demonstrated in previous evaluations. However, from a cold Julia process, the JIT compilation for the multinetwork code path takes >15 minutes, making it impractical for batch evaluation scripts. This is a Julia-wide limitation (first-invocation JIT overhead), not a PowerModels-specific issue [solver-specific: Julia JIT compilation overhead]. From a warm REPL, the multi-period pathway runs in ~65ms per scenario.

## Timing

- **Wall-clock:** 2.491 s total (includes JIT warm-up solve + 20 scenarios)
- **Timing source:** measured
- **Per-scenario solve time:** 4.0 ms average (post-JIT)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b4_stochastic_wrapping_tiny.jl`

Core pattern:

```julia
# Read scenario data programmatically
scenario_mults = parse_csv(scenario_file)
bus_loads = parse_csv(load_file)

for s in 1:n_scenarios
    sc_data = deepcopy(data)
    load_mult = get_scenario_mult(s, peak_hr)
    for (lid, load) in sc_data["load"]
        load["pd"] *= load_mult
    end
    result = PowerModels.solve_dc_opf(sc_data, optimizer;
        setting=Dict("output" => Dict("duals" => true)))
    # ... collect dispatch, LMPs, objective
end
```
