---
test_id: G-2
tool: powersimulations
dimension: gate
network: SMALL
status: pass
workaround_class: null
timestamp: "2026-03-07T00:19:46"
protocol_version: "v4"
---

# G-2: Ingest SMALL network (ACTIVSg 2000-bus)

## Result: PASS

## Details

- **Network file:** `data/networks/case_ACTIVSg2000.m`
- **Expected counts:** 2000 buses / 3206 branches / 544 generators
- **Actual counts:** 2000 buses / 3206 branches / 544 generators
- **Load time:** 2.33 seconds
- **Data quality notes:**
  - Slack bus: WADSWORTH 3
  - No NaN values in bus voltages
  - No Inf values in bus voltages
  - Generators with cost data: 544 / 544
  - Branches with flow limits: 3206 / 3206
- **Errors/warnings:** PowerSystems.jl tightened angle limits on branches with angmin/angmax outside [-90, 90] range and corrected negative rate_a values to positive (standard normalization). No data loss.

## Test Script

See `evaluations/powersimulations/tests/test_gate.jl`
