---
test_id: G-1
tool: pandapower
dimension: gate
network: TINY
status: pass
workaround_class: null
timestamp: "2026-03-14T02:50:33Z"
protocol_version: "v10"
skill_version: "v1"
test_hash: "7f8c3606"
---

# G-1: Ingest reference network (TINY)

## Result: PASS

## Details

- **Network file:** data/networks/case39.m
- **Expected counts:** 39 buses / 46 branches / 10 generators
- **Actual counts:** 39 buses / 46 branches / 10 generators
- **Load time:** 0.085s
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
