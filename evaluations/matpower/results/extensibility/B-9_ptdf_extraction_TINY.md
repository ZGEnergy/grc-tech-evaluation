---
test_id: B-9
tool: matpower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.1442
peak_memory_mb: null
loc: 70
timestamp: "2026-03-06T00:00:00Z"
---

# B-9: PTDF Matrix Extraction on TINY

## Result: PASS

## Details

- **Network file:** data/networks/case39.m (39 buses, 46 branches, 10 generators)
- **API call:** `H = makePTDF(mpc)` -- single function, no preprocessing required
- **PTDF dimensions:** 46 x 39 (branches x buses) -- correct
- **Max absolute error vs DCPF:** 1.48e-12 MW (tolerance: 1e-6)
- **Wall clock:** 0.14 seconds (includes DCPF solve for validation)

## Verification

### PTDF-predicted flows match DCPF-solved flows

| Branch | From | To | DCPF (MW) | PTDF (MW) | Error (MW) |
|--------|------|----|-----------|-----------|------------|
| 1 | 1 | 2 | -178.3537 | -178.3537 | 1.14e-13 |
| 5 | 2 | 30 | -250.0000 | -250.0000 | 0.00e+00 |
| 10 | 5 | 6 | -514.7537 | -514.7537 | 1.48e-12 |
| 20 | 10 | 32 | -650.0000 | -650.0000 | 3.41e-13 |
| 30 | 17 | 18 | 200.6853 | 200.6853 | 8.53e-13 |
| 40 | 25 | 26 | 54.2162 | 54.2162 | 0.00e+00 |
| 46 | 29 | 38 | -830.0000 | -830.0000 | 3.41e-13 |

All 46 branch flows predicted within 1e-6 MW tolerance. Maximum error is 1.48e-12 MW,
six orders of magnitude better than the required tolerance.

### PTDF Matrix Properties

- Slack column (bus 31): all zeros (correct for single-slack formulation)
- Value range: [-1.0, 1.0]
- Non-zero entries: 1090 / 1794 (60.8%)

### Distributed Slack Support

`makePTDF(mpc, slack_weights)` accepts an nb x 1 vector of slack weights, enabling
distributed (generation-proportional, load-proportional, or custom) reference
formulations. The distributed-slack PTDF differs substantially from single-slack
(max difference: 0.97), confirming the weight vector is effective.

## API Assessment

**Zero friction.** `makePTDF(mpc)` is a single function call that accepts the
standard `mpc` struct. No `ext2int` conversion needed (case39 already uses
consecutive 1..39 numbering; `makePTDF` handles the conversion internally for
non-consecutive cases). The function also supports:
- Custom single slack: `makePTDF(mpc, slack_bus)`
- Distributed slack: `makePTDF(mpc, weight_vector)`
- Transfer-specific PTDF: `makePTDF(mpc, slack, txfr)`
- Column-subset PTDF: `makePTDF(mpc, slack, bus_idx)`

## Test Script

`evaluations/matpower/tests/extensibility/test_b9_ptdf_extraction_tiny.m`
