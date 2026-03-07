---
test_id: G-1
tool: powermodels
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
protocol_version: v4
---

# G-1: Ingest TINY network (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39/46/10
- **Actual counts:** 39/46/10
- **Load time:** 0.738s
- **Data quality notes:** All checks passed. No NaN/Inf in bus voltages, line ratings, or generator limits. Generator cost data present. Slack bus identified (bus 31).
- **Errors/warnings:** PowerModels tightened angmin/angmax values on several branches from +/-360 to +/-60 degrees (standard PowerModels behavior for out-of-range angle difference limits).

## Test Script

See `evaluations/powermodels/test/test_gate.jl`
