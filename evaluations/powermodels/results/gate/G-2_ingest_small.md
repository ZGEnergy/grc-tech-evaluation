---
test_id: G-2
tool: powermodels
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: "2026-03-13T22:57:06Z"
protocol_version: "v10"
skill_version: v1
test_hash: "86c5996e"
---

# G-2: Ingest ACTIVSg 2000 reference network

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 0.27s

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
# See tests/test_gate.jl — G-2 invocation:
r2 = run_gate_test(
    "G-2", "SMALL (ACTIVSg 2000)",
    "/workspace/data/networks/case_ACTIVSg2000.m", 2000, 3206, 544)
```
