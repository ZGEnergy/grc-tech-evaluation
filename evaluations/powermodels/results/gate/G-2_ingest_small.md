---
test_id: G-2
tool: powermodels
network: SMALL
status: pass
timestamp: 2026-03-05T17:00:00Z
---

# G-2: Ingest SMALL network (ACTIVSg2000)

## Result: PASS

## Details

- **Network file:** `/workspace/data/networks/case_ACTIVSg2000.m`
- **Expected counts:** ~2000 buses (actual verified below)
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 0.306 s
- **Data quality notes:**
  - No NaN or infinite values in bus voltages, line ratings, or generator limits
  - 410/544 generators have cost data; 134/544 generators missing cost data
  - 1 reference/slack bus identified (bus_type == 3)
  - Branch flow limits present (no missing/zero rate_a reported)
- **Errors/warnings:** PowerModels widened angmin/angmax from 0 to +/-60 degrees on multiple branches where original values were zero (standard correction for degenerate angle bounds)

## Test Script

See `evaluations/powermodels/test/gate_eval.jl`
