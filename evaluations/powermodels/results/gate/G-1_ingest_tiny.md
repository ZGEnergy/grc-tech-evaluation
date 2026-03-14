---
test_id: G-1
tool: powermodels
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: "2026-03-13T22:57:06Z"
protocol_version: "v10"
skill_version: v1
test_hash: "667325b8"
---

# G-1: Ingest IEEE 39-bus reference network

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.32s

## Post-Import Audit

- Bus voltage bounds: all finite
- Slack/reference bus (bus_type=3): present
- Branch rate_a: all finite
- Branch reactance (br_x): no zero values
- Generator cost data: present for all generators
- Generator limits (pmin/pmax/qmin/qmax): all finite
- Data quality issues: none

## Test Script

```julia
# See tests/test_gate.jl — G-1 invocation:
r1 = run_gate_test(
    "G-1", "TINY (IEEE 39-bus)",
    "/workspace/data/networks/case39.m", 39, 46, 10)
```
