---
test_id: A-4
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.2977
peak_memory_mb: null
loc: 100
timestamp: "2026-03-06T00:00:00Z"
---

# A-4: AC Feasibility Check on DC OPF Dispatch (TINY)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Depends on:** A-3 (DC OPF dispatch)
- **Converged:** Yes (AC PF converges on DC OPF dispatch)
- **Wall clock:** 0.2977 seconds

## Approach

1. Solve DC OPF: `results_dc = rundcopf(mpc, mpopt)`
2. Fix all non-slack generators to DC OPF dispatch by setting `PMIN = PMAX = PG`
3. Leave slack generator (gen #2, bus 31) free to absorb AC losses
4. Run AC PF: `results_ac = runpf(mpc_modified, mpopt)`
5. Check voltage violations (outside [0.95, 1.05]) and thermal violations

All done within the same model context -- no export/reimport needed. The `mpc` struct
is modified in-place (copy the struct, modify gen columns, call `runpf`).

## Voltage Violations

5 high-voltage violations detected (above 1.05 p.u.):

| Bus | Vm (p.u.) | Violation |
|-----|-----------|-----------|
| 25  | 1.0534    | +0.0034   |
| 26  | 1.0528    | +0.0028   |
| 28  | 1.0536    | +0.0036   |
| 29  | 1.0531    | +0.0031   |
| 36  | 1.0636    | +0.0636   |

Overall voltage range: [0.9820, 1.0636] p.u.

## Thermal Violations

No thermal limit violations. All 46 branches have RATE_A limits; none are exceeded.

Top 5 loaded branches by % of RATE_A:

| Branch | From-To | Loading (%) | Flow / Limit (MVA) |
|--------|---------|-------------|-------------------|
| 3      | 2->3    | 89.2%       | 446 / 500         |
| 27     | 16->19  | 79.7%       | 478 / 600         |
| 37     | 22->35  | 77.3%       | 696 / 900         |
| 20     | 10->32  | 77.3%       | 696 / 900         |
| 13     | 6->11   | 76.9%       | 369 / 480         |

## Power Balance

- Total generation: 6300.04 MW
- Total load: 6254.23 MW
- Total AC losses: 45.81 MW (0.73%)
- Slack generator adjusted from 646.00 MW (DC) to 691.81 MW (AC) to absorb losses

## API Observations

The workflow stays entirely within the MATPOWER struct ecosystem. Key steps:
- `rundcopf(mpc)` returns results with `gen(:, PG)` containing optimal dispatch
- Copy `mpc`, fix `gen(:, [PG PMIN PMAX])` for non-slack generators
- `runpf(mpc_modified)` runs AC power flow
- Violations are readable from `bus(:, VM)` and `branch(:, [PF QF PT QT])` vs `RATE_A`

No workarounds needed. The column-index approach (`define_constants`) works cleanly
for both OPF results and PF results.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a4_ac_feasibility_tiny.m`
