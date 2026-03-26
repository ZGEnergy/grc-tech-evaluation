---
test_id: G-3
tool: pandapower
dimension: gate
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: "d5cc0c0a"
status: pass
workaround_class: null
test_category: gate_minimum_bar
wall_clock_seconds: 0.379
timestamp: "2026-03-24T12:00:00Z"
---

# G-3: Ingest reference network (MEDIUM)

## Result: PASS

## Details

- **Network file:** data/networks/case_ACTIVSg10k.m
- **Expected counts:** 10000 buses / 12706 branches / 2485 generators
- **Actual counts:** 10000 buses / 12706 branches / 2485 generators
- **Load time:** 0.379s
- **Element breakdown:**
  - Branches: line=9726, trafo=975, trafo3w=0, impedance=2005
  - Generators: gen=1727, ext_grid=1 (slack), sgen=757
- **Data quality notes:**
  - No NaN or infinite values in line ratings, transformer ratings, or generator limits
  - Generator cost data present: 2485 polynomial cost rows (all generators have cost curves)
  - Slack/reference bus identified via ext_grid (1 ext_grid element)
  - Bus voltage columns (vm_pu, va_degree) not populated pre-solve (expected)
  - No line rating zeros or infinities
  - 2005 branches converted to impedance elements (MATPOWER branches with tap ratio != 0/1 connecting same voltage levels)
  - 975 branches converted to transformer elements
  - 757 generators converted to sgen (static generator) elements
- **Errors/warnings:**
  - FutureWarning from pandas about incompatible dtype when setting trafo lookup (cosmetic, does not affect results)

## Test Script

`evaluations/pandapower/tests/test_gate.py::TestGate::test_gate_ingest[G-3_MEDIUM]`
