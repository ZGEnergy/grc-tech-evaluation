---
test_id: G-3
tool: powermodels
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: "2026-03-13T22:57:06Z"
protocol_version: "v10"
skill_version: v1
test_hash: "6e23d994"
---

# G-3: Ingest ACTIVSg 10k reference network

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 1.19s

## Post-Import Audit

- Bus voltage bounds: all finite
- Slack/reference bus (bus_type=3): present
- Branch rate_a: 2462 of 12706 branches have non-finite (Inf) rate_a values, indicating unconstrained thermal limits in the raw .m file (not introduced by PowerModels)
- Branch reactance (br_x): no zero values
- Generator cost data: present for all generators
- Generator limits (pmin/pmax/qmin/qmax): all finite

## Data Quality Warnings

- **2462 branches with Inf rate_a (19.4%):** These unconstrained thermal limits are present in the source case_ACTIVSg10k.m file. Downstream OPF tests that require branch flow limits will need preprocessing to replace Inf values with finite thermal ratings.

## Test Script

```julia
# See tests/test_gate.jl — G-3 invocation:
r3 = run_gate_test(
    "G-3", "MEDIUM (ACTIVSg 10k)",
    "/workspace/data/networks/case_ACTIVSg10k.m", 10000, 12706, 2485)
```
