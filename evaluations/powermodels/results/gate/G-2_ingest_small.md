---
test_id: G-2
tool: powermodels
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
protocol_version: v4
---

# G-2: Ingest SMALL network (ACTIVSg2000)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000/3206/544
- **Actual counts:** 2000/3206/544
- **Load time:** 0.466s
- **Data quality notes:** All checks passed. No NaN/Inf in bus voltages, line ratings, or generator limits. Generator cost data present. Branch flow limits (rate_a) present on all branches. Slack bus identified (bus 7098).
- **Errors/warnings:** None.

## Test Script

See `evaluations/powermodels/test/test_gate.jl`
