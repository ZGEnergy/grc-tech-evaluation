---
test_id: G-3
tool: powermodels
network: MEDIUM
status: pass
timestamp: 2026-03-05T17:00:00Z
---

# G-3: Ingest MEDIUM network (ACTIVSg10k)

## Result: PASS

## Details

- **Network file:** `/workspace/data/networks/case_ACTIVSg10k.m`
- **Expected counts:** ~10000 buses (actual verified below)
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 1.507 s
- **Data quality notes:**
  - No NaN or infinite values in bus voltages, line ratings, or generator limits
  - 1136/2485 generators have cost data; 1349/2485 generators missing cost data
  - 2462/12706 branches have missing or zero rate_a (flow limits) -- these branches lack thermal ratings in the source MATPOWER case
  - 1 reference/slack bus identified (bus_type == 3)
- **Errors/warnings:**
  - PowerModels widened angmin/angmax from 0 to +/-60 degrees on multiple branches (standard correction)
  - PowerModels removed empty cost terms from numerous generators with `Float64[]` cost arrays
  - Missing branch flow limits (2462 branches) and missing generator cost data (1349 generators) are properties of the source data, not a tool deficiency

## Test Script

See `evaluations/powermodels/test/gate_eval.jl`
