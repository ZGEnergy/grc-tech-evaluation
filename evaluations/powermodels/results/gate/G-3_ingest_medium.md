---
test_id: G-3
tool: powermodels
dimension: gate
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: d5cc0c0a
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 1.25
timestamp: "2026-03-24T18:49:08Z"
---

# G-3: Ingest ACTIVSg 10k-bus reference network (MEDIUM)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 1.25s
- **Data quality notes:** 2462 of 12706 branches (19.4%) have non-finite (Inf) rate_a values, representing unconstrained thermal limits in the source .m file. All bus voltage bounds finite, slack bus present, no zero-reactance branches, generator cost data present for all generators, all generator limits (pmin/pmax/qmin/qmax) finite.
- **Errors/warnings:** None

## Data Quality Warnings

- **2462 branches with Inf rate_a (19.4%):** These unconstrained thermal limits are present in the source case_ACTIVSg10k.m file (not introduced by PowerModels). Downstream OPF tests that require branch flow limits will need preprocessing to replace Inf values with finite thermal ratings.

## Test Script

```julia
# See tests/test_gate.jl — G-3 invocation:
r3 = run_gate_test(
    "G-3", "MEDIUM (ACTIVSg 10k)",
    "/workspace/data/networks/case_ACTIVSg10k.m", 10000, 12706, 2485)
```
