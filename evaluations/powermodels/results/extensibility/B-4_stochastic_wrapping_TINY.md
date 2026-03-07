---
test_id: B-4
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 3.05
peak_memory_mb: null
loc: 220
solver: HiGHS
timestamp: 2026-03-07T00:00:00Z
---

# B-4: Stochastic Wrapping

## Result: PASS

## Approach
Generated 20 scenarios of 12-hour multi-period DCOPF on the IEEE 39-bus network.
Each scenario applies correlated perturbations by resource type:
- Load: common scaling factor (sigma=0.03) plus per-bus noise (sigma=0.005)
- Thermal generators (1-8): small pmax perturbation (sigma=0.03, floor 0.8)
- Renewable generators (9-10): moderate pmax perturbation (sigma=0.08, mean 0.9, floor 0.6)

Workflow per scenario: `deepcopy(data)` to clone the base case, modify generator pmax
for availability, `PowerModels.replicate(data, 12)` to create a 12-period multi-network,
apply hourly load profiles with scenario perturbations to each period's loads, then
`PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)` to solve.

Results are collected from the nested Dict returned by `solve_mn_opf`.

## Output
- 19 of 20 scenarios solved optimally (1 infeasible due to stochastic perturbation)
- Total solve time: 2.28s across all 20 scenarios
- Mean solve time per scenario: 0.114s
- Objective range: 313,771 to 390,160 (spread: 76,389)
- Mean objective: 365,543

## Workarounds
None. PowerModels natively supports multi-period networks via `replicate()` and
`solve_mn_opf()`. Timeseries data is injected programmatically by mutating the
data dict. No file I/O or custom serialization needed.

## Timing
- Wall-clock: 3.05s (excludes Julia/package load and warm-up solve)

## Test Script
Path: `evaluations/powermodels/tests/extensibility/test_b4_stochastic_wrapping.jl`
