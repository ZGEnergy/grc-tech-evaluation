---
test_id: A-2
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.1968
peak_memory_mb: null
loc: 70
timestamp: "2026-03-06T00:00:00Z"
---

# A-2: AC Power Flow (Newton-Raphson) on TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Solver:** Newton-Raphson (MATPOWER built-in, `pf.alg = NR`)
- **Converged:** Yes
- **Start method:** Flat start (V=1.0 pu, theta=0 deg) -- converged on first attempt
- **Wall clock:** 0.1968 seconds

## Convergence Protocol

1. Flat start attempted first -- **converged successfully**
2. DC warm-start fallback was not needed

## Structured Outputs Verified

### Bus Voltage Magnitudes and Angles

| Bus | VM (pu) | VA (deg) |
|-----|---------|----------|
| 1   | 1.0394  | -13.5366 |
| 10  | 1.0178  | -8.1709  |
| 20  | 0.9910  | -6.8212  |
| 31  | 0.9820  | 0.0000   |
| 39  | 1.0300  | -14.5353 |

- VM range: [0.9820, 1.0636] pu
- VA range: [-14.5353, 4.4684] deg

### Line P/Q Flows (sample)

| Branch | From | To  | PF (MW) | QF (MVAr) | PT (MW) | QT (MVAr) |
|--------|------|-----|---------|-----------|---------|-----------|
| 1      | 1    | 2   | -173.70 | -40.31    | 174.68  | -24.36    |
| 2      | 1    | 39  | 76.10   | -3.89     | -76.03  | -74.75    |
| 3      | 2    | 3   | 319.91  | 88.59     | -318.58 | -100.88   |

### Losses
- Total P loss: 43.6411 MW (0.70% of load)
- Total Q loss: -112.1610 MVAr

### Generator Output
- Total P generation: 6297.87 MW (load 6254.23 + losses 43.64)
- Total Q generation: 1274.94 MVAr
- Slack bus (31) absorbs mismatch: PG = 677.87 MW, QG = 221.57 MVAr

## API Observations

Single-call API: `results = runpf(mpc, mpopt)`. Solver selection via `mpoption('pf.alg', 'NR')`.
Flat start is set by modifying `mpc.bus(:, VM)` and `mpc.bus(:, VA)` before calling `runpf`.
All P/Q flows accessible from `results.branch` columns 14-17 (PF, QF, PT, QT). Losses
computed as `PF + PT` per branch. No workarounds needed.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a2_acpf_tiny.m`
