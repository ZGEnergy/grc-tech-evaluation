---
test_id: A-1
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.1660
peak_memory_mb: null
loc: 55
timestamp: "2026-03-06T00:00:00Z"
---

# A-1: DC Power Flow on TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Solver:** Direct linear solve (B*theta = P_inj)
- **Converged:** Yes
- **Wall clock:** 0.1660 seconds (includes MATPOWER output formatting overhead)

## Structured Outputs Verified

### Voltage Angles
- Bus 1: -12.3044 deg
- Bus 10: -7.1507 deg
- Bus 31 (slack): 0.0000 deg
- Range: [-13.4611, 7.4046] deg

### Nodal Injections
- Total generation: 6254.23 MW
- Total load: 6254.23 MW (balanced, as expected for DCPF)
- Slack bus (31) picks up 625.03 MW net injection

### Line Flows
- 46 branches with non-trivial flows
- Max |flow|: 830.00 MW (branch 46, bus 29 -> 38)
- Sample: Branch 1 (1->2) PF = -178.35 MW

## API Observations

MATPOWER provides a clean one-call API: `results = rundcpf(mpc)`. All outputs are
in the returned `results` struct using the same column layout as the input (`results.bus`,
`results.branch`, `results.gen`). Column indices are documented via `define_constants`
which loads named constants (e.g., `VA`, `PF`, `PT`). No workarounds needed.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a1_dcpf_tiny.m`
