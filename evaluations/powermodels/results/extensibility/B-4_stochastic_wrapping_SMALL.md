---
test_id: B-4
tool: powermodels
dimension: extensibility
network: SMALL
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 281.58
peak_memory_mb: null
loc: 220
solver: HiGHS
timestamp: "2026-03-07T00:00:00Z"
---

# B-4: Stochastic Wrapping (SMALL, ACTIVSg 2000-bus)

## Result: PASS

## Approach

Generated 20 scenarios of 12-hour multi-period DCOPF on the ACTIVSg 2000-bus network
(544 generators, 3,206 branches). Each scenario applies load-level perturbations only
(generator pmax is kept constant because ACTIVSg2000 has tight generation margins --
even small pmax reductions cause infeasibility).

Load perturbation per scenario:
- Common load scaling factor (sigma=0.01)
- Per-bus noise (sigma=0.002)
- 12-hour diurnal load profile with peak multiplier 0.95 (all multipliers <= 1.0)

Workflow per scenario: `deepcopy(data)` to clone the base case,
`PowerModels.replicate(data, 12)` to create a 12-period multi-network,
apply hourly load profiles with scenario perturbations to each period's loads, then
`PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)` to solve.

Costs were linearized (quadratic term set to 0) for HiGHS LP compatibility, since
HiGHS QP fails on ACTIVSg2000.

## Output

- **Scenarios optimal:** 20 / 20
- **Total solve time:** 281.58s across all 20 scenarios
- **Mean solve time per scenario:** 14.08s
- **Min / Max solve time:** 12.0s / 15.41s
- **Objective range:** 11,731,592 to 12,143,354 (spread: 411,762)
- **Mean objective:** 11,876,046

## Observations

1. **Tight margins:** ACTIVSg2000 has only 21% generation capacity margin over base load.
   Perturbations to generator pmax (even 3% sigma) cause widespread infeasibility.
   The TINY test (39-bus) had sufficient margin for both load and gen perturbations.

2. **Solve time scaling:** Each 12-period mn_opf on 2000-bus takes ~12-15s with HiGHS LP,
   compared to ~0.11s on 39-bus. The 120x increase reflects the LP problem size
   (2000 buses x 12 periods vs 39 buses x 12 periods).

3. **HiGHS QP limitation:** Quadratic costs must be linearized. This affects the dispatch
   order but does not affect the scalability demonstration.

## Workarounds

None for the API workflow. The same `deepcopy + replicate + solve_mn_opf` pattern from
TINY works identically at SMALL scale. The only adaptation is reducing perturbation
magnitude and linearizing costs for solver compatibility.

## Timing

- Wall-clock: 281.58s (excludes Julia/package load and warm-up solve)
- Per-scenario: 12.0-15.4s

## Test Script

Path: `evaluations/powermodels/tests/test_small_b4_c6.jl`
