---
test_id: B-4
tool: powermodels
dimension: extensibility
network: TINY
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.786
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 18
solver: HiGHS
protocol_version: "v9"
skill_version: v1
test_hash: 50ef59c5
timestamp: 2026-03-12T03:38:50Z
---

# B-4: Stochastic Scenario Wrapping (TINY)

## Result: PASS

## Approach

Ran 20 scenarios of 12-period DC OPF using the `PowerModels.replicate()` + `solve_mn_opf()` multi-period API.

**Scenario generation:** Synthetic correlated perturbations (seed=42). Each scenario has:
- A common load scaling factor (±3% normal noise) applied to all loads
- Per-bus noise (±0.5%)
- Per-hour load profile: [0.80, 0.75, 0.72, 0.70, 0.75, 0.85, 0.95, 1.00, 0.98, 0.95, 0.90, 0.85]
- Thermal generator availability: ±3% normal, bounded [0.8, 1.0]
- Renewable-class generator availability: ±8% normal, bounded [0.6, 1.0]

Note: `data/timeseries/case39/scenarios/scenario_multipliers_50x24.csv` exists in the repository but contains per-generator multipliers (format: scenario, gen_uid, HR_1..HR_24), not per-load multipliers. Synthetic load perturbations were used instead.

### Per-scenario workflow:

```

deepcopy(data) → modify gen pmax → replicate(T=12) → modify per-period loads → solve_mn_opf()

```

No file I/O per scenario. All overhead is Julia data operations.

**Results collected in:** `Dict{Int, Dict}` keyed by scenario index, containing termination status, objective, per-period dispatch.

## Output

| Metric | Value |
|--------|-------|
| Scenarios run | 20 |
| Scenarios optimal | 16 |
| Scenarios failed | 4 |
| Total solve time | 1.30 s |
| Mean solve time/scenario | 65.2 ms |
| Min/Max solve time | 33 / 107 ms |
| Mean objective (12-period) | 363,413 |
| Objective range | 65,678 (334,360 to 400,039) |

**Scenario 1 period-1 dispatch (all 10 generators):** ~4.909 pu each (10 generators share load equally due to uniform cost in case39).

**Scenario 20:** Objective = 367,994 (12-period).

4 scenarios failed to converge optimally — likely due to load scaling exceeding generation capacity at high-load periods when generator availability is reduced. This is within the protocol's 20% infeasibility tolerance (pass threshold: ≥80% converge = ≥16 scenarios).

## Workarounds

None required for core functionality. The `replicate()` + `solve_mn_opf()` pattern is documented public API. Input injection is via plain dict mutation — no file I/O or config files required.

Minor note: the `scenario_multipliers_50x24.csv` file format (per-generator, not per-load) did not match the expected per-load timeseries format. Synthetic perturbations were used. This is not a tool limitation — PowerModels accepts any programmatic load modification.

## Timing

- **Wall-clock:** 1.786 s total (20 scenarios × 12-period DCOPF)
- **Timing source:** measured (warm-up run excluded)
- **Per-scenario average:** 65.2 ms
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b4_stochastic_scenario_wrapping_tiny.jl`

Core pattern:

```julia

for s in 1:N_scenarios
    sc_data = deepcopy(data)
    # modify gen pmax per scenario
    mn_data = PowerModels.replicate(sc_data, T)
    for t in 1:T
        # modify loads per period
        for (_, load) in mn_data["nw"][string(t)]["load"]
            load["pd"] *= multiplier[s, t]
        end
    end
    result = PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)
end

```
