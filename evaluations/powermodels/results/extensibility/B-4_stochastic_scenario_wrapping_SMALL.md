---
test_id: B-4
tool: powermodels
dimension: extensibility
network: SMALL
protocol_version: "v9"
skill_version: v1
test_hash: 50ef59c5
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 281.58
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 233
solver: HiGHS
timestamp: 2026-03-11T00:00:00Z
---

# B-4: Stochastic Scenario Wrapping — SMALL

## Result: PASS

## Approach

20 scenarios × 12-hour multi-period DC OPF on the ACTIVSg 2000-bus network (544 generators,
3,206 branches). Each scenario applies load-only perturbations:

- Common load scaling factor: ±1% (σ=0.01)
- Per-bus load noise: ±0.2% (σ=0.002)
- Conservative 12-hour diurnal profile: peak multiplier 0.95 (all ≤ 1.0)

**Note on generator perturbations:** ACTIVSg2000 has only 21% generation capacity margin above
base load. Even small pmax reductions (3–8%) cause widespread infeasibility. Load-only
scenarios are used — this is a documented network characteristic, not a tool limitation.

Workflow per scenario:
1. `deepcopy(data)` — clone preprocessed base case
2. `PowerModels.replicate(data, 12)` — create 12-period multi-network
3. Apply hourly load profiles with scenario perturbations to each period
4. `PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)` — solve
5. Extract period-1 dispatch and objective

**Preprocessing applied:** zero-reactance fix (`br_x=0 → 0.0001`), zero-RATE_A fix (`rate_a=0 → 9999 MVA`), generator cost linearization (`c2=0` for HiGHS LP compatibility).

## Output

| Metric | Value |
|--------|-------|
| Scenarios optimal | 20 / 20 |
| Total solve time | 281.58s |
| Mean solve time per scenario | 14.08s |
| Min solve time | 12.00s |
| Max solve time | 15.41s |
| Objective range | 11,731,592 – 12,143,354 |
| Objective spread | 411,762 |
| Mean objective | 11,876,046 |
| Accepts timeseries programmatically | YES |
| Results collectable (dispatch/prices) | YES |
| Per-scenario overhead | deepcopy + replicate (no file I/O) |

**API pattern works identically to TINY** — same `deepcopy + replicate + solve_mn_opf` pattern scales to 2000-bus without modification. The only adaptation is reduced perturbation magnitude and cost linearization for solver compatibility.

**Pass condition:** Tool accepts timeseries inputs programmatically (not from config files only). Scenario loop is expressible without excessive per-scenario overhead. Results (prices, dispatch) collectable in a structured format. All three criteria met.

## Workarounds

- **What:** Generator costs linearized (`c2=0`) for HiGHS LP compatibility on ACTIVSg2000.
- **Why:** HiGHS QP (quadratic cost objectives) returns `OTHER_ERROR` on this network. Linearization makes it a pure LP.
- **Durability:** stable — 2 lines of preprocessing, does not affect LP physics or the stochastic wrapping demonstration.
- **Grade impact:** None — the API workflow (deepcopy + replicate + solve_mn_opf loop) is the pass criterion. Cost linearization is a preprocessing detail.

## Timing

- **Wall-clock:** 281.58s (scenario loop only; excludes Julia startup/JIT and warm-up solve)
- **Timing source:** measured (REPL-based run, eliminates per-subprocess JIT overhead)
- **Per-scenario:** 12.0–15.4s — reflects LP solve for 2000-bus × 12-period multi-network (~13,000 variables, ~38,000 constraints)
- **Peak memory:** not measured
- **CPU cores used:** 1

**Timing methodology note:** Per-scenario times measured from REPL (warm JIT). When run as a
fresh subprocess (`julia script.jl`), JIT recompilation applies per scenario, yielding 160–310s
per scenario. The REPL measurement is the correct comparison baseline for solver performance.
The subprocess overhead is documented in observation `api-friction-scalability-b4_c6_mn_opf_slow_small.md`.

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b4_stochastic_scenario_wrapping_small.jl`

Key API pattern — scenario loop with programmatic timeseries:

```julia

for s in 1:N_scenarios
    sc_data = deepcopy(data)
    mn_data = PowerModels.replicate(sc_data, T)  # T=12 periods

    # Apply per-period load profiles
    for t in 1:T
        nw = mn_data["nw"][string(t)]
        for (lid, load) in nw["load"]
            mult = sc["hourly_load"][t] * get(sc["bus_noise"], lid, 1.0)
            load["pd"] *= mult
            load["qd"] *= mult
        end
    end

    mn_result = PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)
    # Collect results
    dispatch = Dict(gid => gen["pg"] for (gid, gen) in mn_result["solution"]["nw"]["1"]["gen"])
end

```
