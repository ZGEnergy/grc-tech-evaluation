---
test_id: G-1
tool: pandapower
dimension: gate
network: TINY
protocol_version: v11
skill_version: v2
test_hash: "7f8c3606"
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.090
timestamp: "2026-03-24T12:00:00Z"
---

# G-1: Ingest reference network (TINY)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.090s
- **Element breakdown:**
  - Branches: line=35, trafo=11, trafo3w=0, impedance=0
  - Generators: gen=9, ext_grid=1 (slack), sgen=0
- **Data quality notes:**
  - No NaN or infinite values in line ratings, transformer ratings, or generator limits
  - Generator cost data present: 10 polynomial cost rows (all generators have cost curves)
  - Slack/reference bus identified via ext_grid (1 ext_grid element)
  - Bus voltage columns (vm_pu, va_degree) not populated pre-solve (expected for pre-power-flow state)
  - No line rating zeros or infinities
- **Errors/warnings:** None

## Test Script

`evaluations/pandapower/tests/test_gate.py::TestGate::test_gate_ingest[G-1_TINY]`
