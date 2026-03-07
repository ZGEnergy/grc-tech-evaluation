---
test_id: G-3
tool: matpower
dimension: gate
network: MEDIUM
status: pass
workaround_class: null
timestamp: "2026-03-07T00:16:18Z"
protocol_version: "v4"
---

# G-3: Ingest MEDIUM (ACTIVSg 10000)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 1.0214 seconds
- **Data quality notes:**
  - No NaN/Inf in bus voltages, generator limits, or gencost data
  - Generator cost data present (2485 gencost rows, matching 2485 generators)
  - 2462 of 12706 branches have zero RATE_A (unlimited flow / no thermal limit defined). This is a property of the ACTIVSg 10k dataset, not a MATPOWER ingestion defect. OPF runs treating these as unconstrained branches will still converge, but security-constrained analyses may need synthetic limits.
  - Reference/slack bus identified: bus 40845
- **Errors/warnings:** 1 data-quality warning (zero RATE_A on 19.4% of branches)

## Test Script

`evaluations/matpower/tests/test_gate.m` -- same script as G-1, tier MEDIUM.
