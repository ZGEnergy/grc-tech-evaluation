---
test_id: G-2
tool: powermodels
dimension: gate
network: SMALL
protocol_version: v11
skill_version: v2
test_hash: 326e8597
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.28
timestamp: "2026-03-24T18:49:08Z"
---

# G-2: Ingest ACTIVSg 2000-bus reference network (SMALL)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg2000.m
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 0.28s
- **Data quality notes:** No issues. All bus voltage bounds finite, slack bus present, all branch rate_a finite, no zero-reactance branches, generator cost data present for all generators, all generator limits (pmin/pmax/qmin/qmax) finite.
- **Errors/warnings:** None

## Test Script

```julia
# See tests/test_gate.jl — G-2 invocation:
r2 = run_gate_test(
    "G-2", "SMALL (ACTIVSg 2000)",
    "/workspace/data/networks/case_ACTIVSg2000.m", 2000, 3206, 544)
```
