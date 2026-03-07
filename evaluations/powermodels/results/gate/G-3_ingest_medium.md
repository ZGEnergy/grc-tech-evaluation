---
test_id: G-3
tool: powermodels
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
protocol_version: v4
---

# G-3: Ingest MEDIUM network (ACTIVSg10k)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000/12706/2485
- **Actual counts:** 10000/12706/2485
- **Load time:** 2.257s
- **Data quality notes:** No NaN/Inf in bus voltages or generator limits. Generator cost data present. Slack bus identified (bus 40845). 2462 of 12706 branches have zero or missing rate_a (flow limit) -- this is inherent to the source MATPOWER case file, not a parsing issue.
- **Errors/warnings:** PowerModels tightened angmin/angmax values on some branches from +/-360 to +/-60 degrees (standard behavior).

## Test Script

See `evaluations/powermodels/test/test_gate.jl`
