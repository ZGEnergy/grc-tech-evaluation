---
test_id: G-1
tool: powermodels
dimension: gate
network: TINY
protocol_version: v11
skill_version: v2
test_hash: 7f8c3606
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.32
timestamp: "2026-03-24T18:49:08Z"
---

# G-1: Ingest IEEE 39-bus reference network (TINY)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.32s
- **Data quality notes:** No issues. All bus voltage bounds finite, slack bus present, all branch rate_a finite, no zero-reactance branches, generator cost data present for all generators, all generator limits (pmin/pmax/qmin/qmax) finite.
- **Errors/warnings:** None

## Test Script

```julia
# See tests/test_gate.jl — G-1 invocation:
r1 = run_gate_test(
    "G-1", "TINY (IEEE 39-bus)",
    "/workspace/data/networks/case39.m", 39, 46, 10)
```
