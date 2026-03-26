---
test_id: A-1
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "05bc255c"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.0008
timing_source: measured
peak_memory_mb: 832.7
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 174
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# A-1: DC Power Flow (DCPF)

## Result: PASS

## Approach

Used `PowerFlows.jl` v0.9.0 `solve_powerflow(DCPowerFlow(), sys)` on the IEEE 39-bus
case loaded via `PowerSystems.System("/workspace/data/networks/case39.m")`. DCPF is a
direct (non-iterative) linear solve -- no external optimizer required.

The result is returned as a nested `Dict{Union{Char,String}, Dict{String,DataFrame}}`
with top-level key `"1"` containing `"bus_results"` and `"flow_results"` DataFrames.

**Observation (api-friction):** The DC power flow result structure differs from the AC
power flow result structure. DCPowerFlow nests results under a string key `"1"`, while
ACPowerFlow returns a flat `Dict{String, DataFrame}`. This inconsistency requires
defensive coding to handle both cases.

## Output

**Bus results** (39 buses, 9 columns):

| Column | Description |
|--------|-------------|
| bus_number | Bus ID |
| Vm | Voltage magnitude (pu) -- unchanged in DC |
| theta | Voltage angle (radians) |
| P_gen | Active power generation (pu, system base) |
| P_load | Active power load (pu) |
| P_net | Net injection (pu) |
| Q_gen, Q_load, Q_net | Reactive power (all zero in DC) |

- Voltage angles: min = -13.46 deg, max = 7.40 deg (38/39 nonzero, 1 slack at 0)
- Total generation: 6297.9 MW, Total load: 6254.2 MW (difference = losses modeled as slack absorption)
- 29 buses have nonzero net injection

**Branch results** (46 branches, 9 columns):

| Column | Description |
|--------|-------------|
| line_name | Branch identifier |
| bus_from, bus_to | Terminal buses |
| P_from_to, P_to_from | Active power flow (pu) |
| Q_from_to, Q_to_from | Reactive power flow (zero in DC) |
| P_losses, Q_losses | Losses (zero in lossless DC) |

- All 46 branches carry nonzero flow
- Flow range: -8.30 to +4.48 pu (-830 to +448 MW)
- Heaviest loaded branch: bus-39 to gen-10 (swing bus injection)

**Sample bus data:**

| Bus | Angle (deg) | P_gen (pu) | P_load (pu) |
|-----|------------|-----------|------------|
| 1 | -12.30 | 0.0 | 0.976 |
| 3 | -10.99 | 0.0 | 3.220 |
| 30 | 7.40 | 2.50 | 0.0 |
| 39 | 0.0 (ref) | 10.0 | 11.04 |

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.0008 s (second run, after JIT warm-up)
- **Timing source:** measured
- **Peak memory:** 832.7 MB (Julia process RSS including JIT cache)
- **Solver iterations:** N/A (direct linear solve)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a1_dcpf.jl`

Key API call:
```julia
sys = System("case39.m")
pf_result = solve_powerflow(DCPowerFlow(), sys)
bus_df = pf_result["1"]["bus_results"]
flow_df = pf_result["1"]["flow_results"]
```

## Observations

- **api-friction:** DC and AC power flow return different result nesting structures (DC nests under key `"1"`, AC returns flat Dict)
- **convergence-quality:** DCPF is a direct solve; no convergence metric applicable
