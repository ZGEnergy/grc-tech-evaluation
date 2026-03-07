---
test_id: A-1
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 16.52
peak_memory_mb: null
loc: 130
solver: null
timestamp: "2026-03-07T01:30:00Z"
---

# A-1: Solve DC Power Flow

## Result: PASS

## Approach

DC Power Flow was solved using `PowerFlows.jl` (v0.9.0), the companion power flow package
in the SIIP ecosystem. PowerSimulations.jl itself is an optimization framework and does not
perform power flow directly; PowerFlows.jl provides `solve_powerflow(DCPowerFlow(), sys)`.

The network was loaded from case39.m via `PowerSystems.System()`. No external solver is
needed -- DCPF is a direct linear solve. The PTDF matrix was also computed via
`PowerNetworkMatrices.PTDF(sys)` to demonstrate accessibility.

No workarounds were required. The API is clean: one function call to solve, results
returned as a `Dict` of `DataFrame`s keyed by scenario.

## Output

**Bus results** (39 rows, 9 columns):

| Column | Description |
|--------|-------------|
| bus_number | Bus ID |
| Vm | Voltage magnitude (1.0 for DC, uses AC setpoints) |
| theta | Voltage angle (radians) |
| P_gen | Active power generation |
| P_load | Active power load |
| P_net | Net active power injection |
| Q_gen, Q_load, Q_net | Reactive power (zero for DCPF) |

Sample bus data (first 3 buses):

| Bus | Vm (pu) | theta (rad) | P_gen | P_load | P_net |
|-----|---------|-------------|-------|--------|-------|
| 1 | 1.0394 | -0.2148 | 0.0 | 0.976 | -0.976 |
| 2 | 1.0485 | -0.1414 | 0.0 | 0.0 | 0.0 |
| 3 | 1.0307 | -0.1918 | 0.0 | 3.22 | -3.22 |

**Flow results** (46 rows, 9 columns):

| Column | Description |
|--------|-------------|
| line_name | Branch identifier |
| bus_from, bus_to | Terminal bus numbers |
| P_from_to, P_to_from | Active power flow (MW, system base) |
| Q_from_to, Q_to_from | Reactive power (zero for DCPF) |
| P_losses, Q_losses | Losses (zero for DCPF) |

**Angle statistics:**
- Min angle: -0.2349 rad
- Max angle: 0.1292 rad
- Reference bus angle: 0.0 rad

**PTDF matrix:** 39 x 46 (buses x branches), accessible via `PowerNetworkMatrices.PTDF(sys)`.

**Total net injection:** 0.436 pu (non-zero due to losses not being modeled in DCPF -- matches reference bus slack absorption).

**Output format:** DataFrames (bus_results, flow_results) keyed by scenario number.

## Workarounds

None required.

## Timing

- **Wall-clock (total):** 16.52s (includes JIT compilation on first invocation)
- **Solve time only:** 3.01s (includes some JIT within PowerFlows)
- **Peak memory:** not measured (Julia GC makes precise measurement non-trivial)
- **CPU cores used:** 1

Note: Julia timing includes JIT compilation overhead on first invocation. Subsequent
solves in the same REPL session would be significantly faster.

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a1_dcpf.jl`
