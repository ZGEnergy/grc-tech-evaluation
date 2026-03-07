---
test_id: G-3
tool: powersimulations
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: "2026-03-07T00:19:46"
protocol_version: "v4"
---

# G-3: Ingest MEDIUM network (ACTIVSg 10000-bus)

## Result: PASS

## Details

- **Network file:** `data/networks/case_ACTIVSg10k.m`
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 3.39 seconds
- **Data quality notes:**
  - Slack bus: PHOENIX 74 6
  - No NaN values in bus voltages
  - No Inf values in bus voltages
  - Generators with cost data: 2485 / 2485
  - Branches with flow limits: 12706 / 12706
- **Errors/warnings:** PowerSystems.jl tightened angle limits on branches with angmin/angmax outside [-90, 90] range and corrected negative rate_a values to positive (standard normalization). No data loss.

## Test Script

See `evaluations/powersimulations/tests/test_gate.jl`
