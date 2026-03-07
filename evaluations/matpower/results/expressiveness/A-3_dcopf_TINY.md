---
test_id: A-3
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.1915
peak_memory_mb: null
loc: 75
timestamp: "2026-03-06T00:00:00Z"
---

# A-3: DC OPF on TINY (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **Solver:** MIPS (MATPOWER Interior Point Solver, built-in)
- **Cost model:** Polynomial (type 2), 3 coefficients (quadratic)
- **Converged:** Yes
- **Objective value:** 41263.94 $/hr
- **Wall clock:** 0.1915 seconds

## Structured Outputs Verified

### Optimal Generator Dispatch

| Gen# | Bus | PG (MW) | PMIN (MW) | PMAX (MW) |
|------|-----|---------|-----------|-----------|
| 1    | 30  | 660.85  | 0.00      | 1040.00   |
| 2    | 31  | 646.00  | 0.00      | 646.00    |
| 3    | 32  | 660.85  | 0.00      | 725.00    |
| 4    | 33  | 652.00  | 0.00      | 652.00    |
| 5    | 34  | 508.00  | 0.00      | 508.00    |
| 6    | 35  | 660.85  | 0.00      | 687.00    |
| 7    | 36  | 580.00  | 0.00      | 580.00    |
| 8    | 37  | 564.00  | 0.00      | 564.00    |
| 9    | 38  | 660.85  | 0.00      | 865.00    |
| 10   | 39  | 660.85  | 0.00      | 1100.00   |

- Total dispatch: 6254.23 MW = Total load: 6254.23 MW

### LMPs (Locational Marginal Prices)
- All buses: 13.5169 $/MWh (uniform)
- LMPs are uniform because case39 has zero RATE_A on all branches (no flow limits),
  so there is no congestion and no locational price differentiation.

### Branch Shadow Prices
- Binding flow constraints: 0
- MU_SF and MU_ST (cols 18-19) are all zero, consistent with no RATE_A limits.

### Line Flows
- Max |flow|: 660.85 MW
- Flows are non-trivial and consistent with dispatch

## API Observations

Single-call API: `results = rundcopf(mpc, mpopt)`. The `results` struct contains:
- `results.f` -- objective value
- `results.bus(:, LAM_P)` -- nodal LMPs (col 14)
- `results.branch(:, MU_SF)` and `MU_ST` -- branch flow shadow prices (cols 18-19)
- `results.gen(:, PG)` -- optimal dispatch (col 2)

Using `define_constants` to get named column indices (LAM_P, MU_SF, PF, etc.) is
strongly recommended over hardcoded numeric indices. Without it, the column mapping
is error-prone, especially for branch results where PF (col 14) and MU_SF (col 18)
are easy to confuse.

## Test Script

`evaluations/matpower/tests/expressiveness/test_a3_dcopf_tiny.m`
