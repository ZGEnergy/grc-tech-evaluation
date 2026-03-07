---
test_id: G-1
tool: powersimulations
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: "2026-03-07T00:19:46"
protocol_version: "v4"
---

# G-1: Ingest TINY network (IEEE 39-bus)

## Result: PASS

## Details

- **Network file:** `data/networks/case39.m`
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 12.90 seconds (includes first-run JIT compilation; subsequent loads are faster)
- **Data quality notes:**
  - Slack bus: bus-31
  - No NaN values in bus voltages
  - No Inf values in bus voltages
  - Generators with cost data: 10 / 10
  - Branches with flow limits: 46 / 46
- **Errors/warnings:** PowerSystems.jl tightened angle limits on multiple branches from +/-360 deg to +/-60 deg (standard PowerSystems.jl behavior for angmin/angmax outside [-90, 90] range). This is cosmetic and does not affect component counts or data integrity.

## Test Script

See `evaluations/powersimulations/tests/test_gate.jl`
