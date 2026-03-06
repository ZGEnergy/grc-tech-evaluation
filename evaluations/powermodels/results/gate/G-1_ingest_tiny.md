---
test_id: G-1
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T17:00:00Z
---

# G-1: Ingest TINY network (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** `/workspace/data/networks/case39.m`
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.428 s
- **Data quality notes:**
  - No NaN or infinite values in bus voltages, line ratings, or generator limits
  - 10/10 generators have cost data (all generators have cost curves)
  - 1 reference/slack bus identified (bus_type == 3)
  - No missing branch flow limits
- **Errors/warnings:** PowerModels tightened angmin/angmax on several branches from +/-360 to +/-60 degrees (standard PowerModels behavior for unconstrained angle bounds)

## Test Script

See `evaluations/powermodels/test/gate_eval.jl`
